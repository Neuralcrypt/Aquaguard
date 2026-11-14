from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.session import get_db
from app.models.auth import User
from app.core.auth import require_warden
from app.core.tenant import require_device_key, get_warden_room, get_warden_sensor, get_warden_alert
from app.models.models import (
    Alert,
    AnomalyResult,
    Room,
    Sensor,
    SeasonalSetting,
    WaterReading,
    DeviceState,
    MonitoringSession
)
from app.schemas.schemas import (
    ReadingCreate, ReadingOut,
    SettingUpdate, SettingOut,
    CalibrationUpdate,
    AlertStatusUpdate, AlertOut,
    RoomCreate, RoomUpdate,
    DeviceControlRequest, DeviceCommandOut,
    DeviceHeartbeat, DeviceStateOut,
    LowFlowConfigUpdate, MonitoringSessionOut,
    WaterLimitUpdate, ContinuousFlowConfigUpdate
)
from app.services.water import ensure_defaults, current_season, day_total, check_daily_limit, check_continuous_flow, SEASONS

router = APIRouter(prefix="/api")

def now_utc_naive(): return datetime.now(timezone.utc).replace(tzinfo=None)

@router.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(__import__('sqlalchemy').text("SELECT 1"))
        return {"status":"healthy", "database":"connected", "room_id":"ROOM-101", "sensor":"not_verified"}
    except Exception:
        raise HTTPException(status_code=503, detail="Database unavailable")

def _room_payload(room: Room, db: Session):
    now = now_utc_naive()
    sensor = db.query(Sensor).filter_by(room_id=room.id).first()
    latest = (
        db.query(WaterReading)
        .filter_by(room_id=room.id)
        .order_by(WaterReading.timestamp.desc())
        .first()
    )
    today = day_total(db, room.id, now)
    setting = db.query(SeasonalSetting).filter_by(
        room_id=room.id, season=current_season(now.month)
    ).first()
    pending = (
        db.query(Alert)
        .filter_by(room_id=room.id)
        .filter(Alert.status != "Resolved")
        .count()
    )

    device_state = (
        db.query(DeviceState).filter_by(sensor_id=sensor.id).first()
        if sensor else None
    )

    if sensor is None:
        status, issue, last_seen = "Inactive", "No sensor assigned", None
    elif not sensor.active:
        status, issue, last_seen = "Inactive", "Sensor is disabled in configuration", sensor.last_seen_at
    elif device_state is not None:
        last_seen = device_state.last_seen_at
        online = (
            last_seen is not None
            and (now - last_seen).total_seconds() <= 15
        )
        if not online:
            status, issue = "Issue", "ESP32 is offline or has stopped sending heartbeats"
        elif device_state.is_running and device_state.acknowledged_command_id == device_state.command_id:
            status, issue = "Active", None
        else:
            status, issue = "Inactive", "Device is connected; monitoring is stopped"
    elif sensor.last_seen_at is None:
        status, issue, last_seen = "Issue", "Assigned sensor has not reported yet", None
    elif (now - sensor.last_seen_at).total_seconds() > 180:
        status, issue, last_seen = "Issue", "No recent sensor readings received", sensor.last_seen_at
    else:
        status, issue, last_seen = "Active", None, sensor.last_seen_at

    return {
        "id": room.id,
        "name": room.name,
        "created_at": room.created_at,
        "sensor_id": sensor.id if sensor else None,
        "sensor_status": status,
        "sensor_issue": issue,
        "last_seen_at": last_seen,
        "daily_limit_litres": setting.daily_limit_litres if setting else 350.0,
        "today_litres": round(today, 3),
        "pending_alerts": pending,
    }

@router.get("/rooms")
def list_rooms(db: Session = Depends(get_db), current_user: User = Depends(require_warden)):
    rooms = db.query(Room).filter(Room.hostel_id == current_user.hostel_id).order_by(Room.id.asc()).all()
    return [_room_payload(room, db) for room in rooms]

@router.post("/rooms", status_code=201)
def create_room(payload: RoomCreate, db: Session = Depends(get_db), current_user: User = Depends(require_warden)):
    room_id = payload.id.strip()
    name = payload.name.strip()
    if not room_id or not name:
        raise HTTPException(status_code=422, detail="Room ID and name are required")
    if db.get(Room, room_id):
        raise HTTPException(status_code=409, detail="A room with this ID already exists")
    room = Room(id=room_id, name=name, hostel_id=current_user.hostel_id)
    db.add(room)
    for season in SEASONS:
        db.add(SeasonalSetting(room_id=room_id, season=season,
            daily_limit_litres=payload.daily_limit_litres,
            continuous_flow_minutes=payload.continuous_flow_minutes))
    db.commit(); db.refresh(room)
    return _room_payload(room, db)

@router.patch("/rooms/{room_id}")
def update_room(room_id: str, payload: RoomUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_warden)):
    room = get_warden_room(db, room_id, current_user)
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Room name cannot be empty")
    room.name = name
    db.commit(); db.refresh(room)
    return _room_payload(room, db)

@router.delete("/rooms/{room_id}")
def delete_room(room_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_warden)):
    room = get_warden_room(db, room_id, current_user)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")
    if room_id == "ROOM-101":
        raise HTTPException(status_code=400, detail="The default room ROOM-101 cannot be deleted")

    # Preserve historical data: do not cascade-delete rooms that have readings,
    # alerts, or anomaly-analysis results attached to them.
    if db.query(WaterReading).filter_by(room_id=room_id).first():
        raise HTTPException(status_code=409, detail="This room has historical readings and cannot be deleted")
    if db.query(Alert).filter_by(room_id=room_id).first():
        raise HTTPException(status_code=409, detail="This room has historical alerts and cannot be deleted")
    if db.query(AnomalyResult).filter_by(room_id=room_id).first():
        raise HTTPException(status_code=409, detail="This room has anomaly-analysis history and cannot be deleted")

    try:
        db.query(SeasonalSetting).filter_by(room_id=room_id).delete(synchronize_session=False)
        db.query(Sensor).filter_by(room_id=room_id).delete(synchronize_session=False)
        db.delete(room)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not delete room due to database dependencies")
    return {"message": f"Room {room_id} deleted successfully"}


@router.get("/rooms/{room_id}")
def room_info(room_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_warden)):
    room = get_warden_room(db, room_id, current_user)
    sensor = db.query(Sensor).filter_by(room_id=room_id).first()
    result = _room_payload(room, db)
    result["calibration_pulses_per_litre"] = sensor.calibration_pulses_per_litre if sensor else None
    return result

@router.get("/overview")
def overview(db: Session = Depends(get_db), current_user: User = Depends(require_warden)):
    now = now_utc_naive()
    rooms = db.query(Room).filter(Room.hostel_id == current_user.hostel_id).all()
    payloads = [_room_payload(room, db) for room in rooms]
    return {"room_count": len(rooms),
            "active_sensors": sum(r["sensor_status"] == "Active" for r in payloads),
            "inactive_sensors": sum(r["sensor_status"] == "Inactive" for r in payloads),
            "sensor_issues": sum(r["sensor_status"] == "Issue" for r in payloads),
            "pending_alerts": sum(r["pending_alerts"] for r in payloads),
            "today_litres": round(float(db.query(func.coalesce(func.sum(WaterReading.interval_volume_litres), 0.0)).join(Room, WaterReading.room_id == Room.id).filter(Room.hostel_id == current_user.hostel_id, WaterReading.timestamp >= now.replace(hour=0, minute=0, second=0, microsecond=0), WaterReading.timestamp < now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)).scalar() or 0), 2)}

@router.post("/readings", response_model=ReadingOut, status_code=201)
def create_reading(payload: ReadingCreate, db: Session = Depends(get_db), device_auth: None = Depends(require_device_key)):
    room = db.get(Room, payload.room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")
    if not db.query(Sensor).filter_by(id=payload.sensor_id, room_id=payload.room_id, active=True).first():
        raise HTTPException(status_code=404, detail="Active sensor not found for this room")
    if payload.device_sequence and db.query(WaterReading).filter_by(device_sequence=payload.device_sequence).first():
        raise HTTPException(status_code=409, detail="Duplicate device_sequence")
    at = payload.timestamp or now_utc_naive()
    if at.tzinfo is not None: at = at.astimezone(timezone.utc).replace(tzinfo=None)
    reading = WaterReading(room_id=payload.room_id, sensor_id=payload.sensor_id, device_sequence=payload.device_sequence, timestamp=at, flow_rate_lpm=payload.flow_rate_lpm, interval_volume_litres=payload.interval_volume_litres, cumulative_volume_litres=payload.cumulative_volume_litres)
    db.add(reading)
    sensor = db.query(Sensor).filter_by(id=payload.sensor_id).first()
    sensor.last_seen_at = at
    db.commit(); db.refresh(reading)
    check_daily_limit(db, payload.room_id, at)
    check_continuous_flow(db, payload.room_id, at)
    return reading

@router.get("/readings", response_model=list[ReadingOut])
def list_readings(room_id: str = "ROOM-101", limit: int = Query(default=100, ge=1, le=1000), db: Session = Depends(get_db), current_user: User = Depends(require_warden)):
    get_warden_room(db, room_id, current_user)
    return db.query(WaterReading).filter_by(room_id=room_id).order_by(WaterReading.timestamp.desc()).limit(limit).all()

@router.get("/summary")
def summary(room_id: str = "ROOM-101", db: Session = Depends(get_db), current_user: User = Depends(require_warden)):
    get_warden_room(db, room_id, current_user)

    now = now_utc_naive()
    today = day_total(db, room_id, now)
    week_start = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    def total_since(start):
        return float(
            db.query(func.coalesce(func.sum(WaterReading.interval_volume_litres), 0.0))
            .filter(
                WaterReading.room_id == room_id,
                WaterReading.timestamp >= start,
            )
            .scalar() or 0.0
        )

    setting = db.query(SeasonalSetting).filter_by(
        room_id=room_id, season=current_season(now.month)
    ).first()
    sensor = db.query(Sensor).filter_by(room_id=room_id).first()
    latest = (
        db.query(WaterReading)
        .filter_by(room_id=room_id)
        .order_by(WaterReading.timestamp.desc())
        .first()
    )
    device_state = (
        db.query(DeviceState).filter_by(sensor_id=sensor.id).first()
        if sensor else None
    )
    device_online = bool(
        device_state
        and device_state.last_seen_at
        and (now - device_state.last_seen_at).total_seconds() <= 15
    )

    daily_limit = setting.daily_limit_litres if setting else 350.0
    telemetry_online = (
        device_online
        if device_state is not None
        else bool(
            sensor and sensor.last_seen_at
            and (now - sensor.last_seen_at).total_seconds() <= 180
        )
    )
    latest_flow = (
        device_state.last_flow_rate_lpm
        if device_online and device_state.is_running
        else (0.0 if device_online else (latest.flow_rate_lpm if latest else 0.0))
    )
    latest_at = (
        device_state.last_seen_at.isoformat()
        if device_online
        else (latest.timestamp.isoformat() if latest else None)
    )

    return {
        "room_id": room_id,
        "season": current_season(now.month),
        "today_litres": round(today, 3),
        "week_litres": round(total_since(week_start), 3),
        "month_litres": round(total_since(month_start), 3),
        "daily_limit_litres": daily_limit,
        "remaining_litres": round(max(0.0, daily_limit - today), 3),
        "latest_flow_rate_lpm": round(latest_flow, 3),
        "last_reading_at": latest_at,
        "device_online": telemetry_online,
        "sensor_last_seen_at": (
            device_state.last_seen_at.isoformat()
            if device_state and device_state.last_seen_at
            else (sensor.last_seen_at.isoformat() if sensor and sensor.last_seen_at else None)
        ),
        "session_litres": (
            db.query(MonitoringSession.total_litres)
            .filter_by(sensor_id=sensor.id, status="RUNNING")
            .order_by(MonitoringSession.started_at.desc())
            .limit(1)
            .scalar()
            if sensor else 0.0
        ) or 0.0,
    }


@router.get("/settings", response_model=list[SettingOut])
def get_settings(room_id: str = "ROOM-101", db: Session = Depends(get_db), current_user: User = Depends(require_warden)):
    get_warden_room(db, room_id, current_user)
    return db.query(SeasonalSetting).filter_by(room_id=room_id).all()

@router.put("/settings/{season}", response_model=SettingOut)
def update_settings(season: str, payload: SettingUpdate, room_id: str = "ROOM-101", db: Session = Depends(get_db), current_user: User = Depends(require_warden)):
    get_warden_room(db, room_id, current_user)
    if season not in SEASONS: raise HTTPException(status_code=422, detail=f"season must be one of {SEASONS}")
    if not db.get(Room, room_id): raise HTTPException(status_code=404, detail="Room not found")
    setting = db.query(SeasonalSetting).filter_by(room_id=room_id, season=season).first()
    if not setting: raise HTTPException(status_code=404, detail="Seasonal setting not found")
    setting.daily_limit_litres = payload.daily_limit_litres; setting.continuous_flow_minutes = payload.continuous_flow_minutes
    db.commit(); db.refresh(setting)
    return setting

@router.put("/sensors/{sensor_id}/calibration")
def update_calibration(sensor_id: str, payload: CalibrationUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_warden)):
    sensor = get_warden_sensor(db, sensor_id, current_user)
    sensor.calibration_pulses_per_litre = payload.pulses_per_litre
    db.commit()
    return {"sensor_id":sensor_id,"pulses_per_litre":sensor.calibration_pulses_per_litre,"note":"Historical readings were not modified."}

@router.get("/alerts", response_model=list[AlertOut])
def list_alerts(room_id: str = "ROOM-101", status: str | None = None, db: Session = Depends(get_db), current_user: User = Depends(require_warden)):
    get_warden_room(db, room_id, current_user)
    q = db.query(Alert).filter_by(room_id=room_id)
    if status: q = q.filter_by(status=status)
    return q.order_by(Alert.created_at.desc()).limit(200).all()

@router.patch("/alerts/{alert_id}", response_model=AlertOut)
def update_alert(alert_id: int, payload: AlertStatusUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_warden)):
    if payload.status not in ("Pending", "Investigating", "Resolved"):
        raise HTTPException(status_code=422, detail="status must be Pending, Investigating, or Resolved")
    alert = get_warden_alert(db, alert_id, current_user)
    alert.status = payload.status
    alert.resolved_at = now_utc_naive() if payload.status == "Resolved" else None
    db.commit(); db.refresh(alert); return alert


@router.delete("/alerts/{alert_id}")
def delete_alert(alert_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_warden)):
    alert = get_warden_alert(db, alert_id, current_user)
    db.delete(alert)
    db.commit()
    return {"message": f"Alert {alert_id} deleted successfully"}


@router.get("/seasonal-analysis")
def seasonal_analysis(room_id: str = "ROOM-101", db: Session = Depends(get_db), current_user: User = Depends(require_warden)):
    get_warden_room(db, room_id, current_user)
    rows = db.query(WaterReading.timestamp, WaterReading.interval_volume_litres).filter_by(room_id=room_id).all()
    totals = {s:0.0 for s in SEASONS}; counts = {s:0 for s in SEASONS}
    for timestamp, litres in rows:
        s = current_season(timestamp.month); totals[s] += litres; counts[s] += 1
    return {"room_id":room_id,"note":"Season labels use a prototype month-based policy; validate it with your university calendar.","seasons":[{"season":s,"total_litres":round(totals[s],2),"reading_count":counts[s],"data_available":counts[s]>0} for s in SEASONS]}

@router.post("/anomaly-analysis")
def anomaly_analysis(room_id: str = "ROOM-101", db: Session = Depends(get_db), current_user: User = Depends(require_warden)):
    get_warden_room(db, room_id, current_user)
    readings = db.query(WaterReading).filter_by(room_id=room_id).order_by(WaterReading.timestamp.asc()).all()
    if len(readings) < 10:
        return {"status":"insufficient_data","minimum_readings":10,"available_readings":len(readings),"results":[]}
    values = [r.interval_volume_litres for r in readings]
    import statistics
    median = statistics.median(values); deviations = [abs(x-median) for x in values]; mad = statistics.median(deviations)
    results=[]
    for r in readings[-100:]:
        score = abs(r.interval_volume_litres-median)/(1.4826*mad) if mad else (0.0 if r.interval_volume_litres==median else 99.0)
        anomaly = score >= 3.5
        result = AnomalyResult(room_id=room_id, reading_id=r.id, timestamp=now_utc_naive(), score=score, is_anomaly=anomaly, method="robust-median-MAD", details=f"interval_volume_litres={r.interval_volume_litres}; median={median}")
        db.add(result)
        results.append({"reading_id":r.id,"timestamp":r.timestamp.isoformat(),"score":round(score,3),"is_anomaly":anomaly})
    db.commit()
    return {"status":"complete","method":"robust-median-MAD baseline","warning":"This is a baseline detector, not proof of a leak. Validate against labelled data.","results":results}
def get_or_create_device_state(db: Session, sensor_id: str):
    sensor = db.get(Sensor, sensor_id)

    if not sensor:
        raise HTTPException(
            status_code=404,
            detail="Sensor not found"
        )

    state = db.query(DeviceState).filter_by(
        sensor_id=sensor_id
    ).first()

    if not state:
        state = DeviceState(
            sensor_id=sensor_id,
            device_id=f"ESP32-{sensor_id.split('-')[-1]}",
            desired_command="STOP",
            command_id=0,
            acknowledged_command_id=0,
            is_running=False
        )

        db.add(state)
        db.commit()
        db.refresh(state)

    return state

def ensure_device_stopped(state: DeviceState):
    if state.is_running:
        raise HTTPException(
            status_code=409,
            detail="Stop monitoring before changing device configuration"
        )


@router.put("/device/water-limit")
def update_water_limit(
    payload: WaterLimitUpdate,
    sensor_id: str = "SENSOR-101",
    db: Session = Depends(get_db), current_user: User = Depends(require_warden)
):
    get_warden_sensor(db, sensor_id, current_user)
    state = get_or_create_device_state(db, sensor_id)
    ensure_device_stopped(state)

    state.water_limit_litres = payload.water_limit_litres

    db.commit()
    db.refresh(state)

    return {
        "message": "Water limit updated successfully",
        "sensor_id": sensor_id,
        "water_limit_litres": state.water_limit_litres
    }


@router.put("/device/continuous-flow")
def update_continuous_flow(
    payload: ContinuousFlowConfigUpdate,
    sensor_id: str = "SENSOR-101",
    db: Session = Depends(get_db), current_user: User = Depends(require_warden)
):
    get_warden_sensor(db, sensor_id, current_user)
    state = get_or_create_device_state(db, sensor_id)
    ensure_device_stopped(state)

    state.continuous_flow_seconds = payload.duration_seconds

    db.commit()
    db.refresh(state)

    return {
        "message": "Continuous-flow duration updated successfully",
        "sensor_id": sensor_id,
        "duration_seconds": state.continuous_flow_seconds
    }


@router.put("/device/low-flow")
def update_low_flow(
    payload: LowFlowConfigUpdate,
    sensor_id: str = "SENSOR-101",
    db: Session = Depends(get_db), current_user: User = Depends(require_warden)
):
    get_warden_sensor(db, sensor_id, current_user)
    state = get_or_create_device_state(db, sensor_id)
    ensure_device_stopped(state)

    state.low_flow_threshold_lpm = payload.threshold_lpm
    state.low_flow_confirmation_seconds = payload.confirmation_seconds

    state.low_flow_since = None
    state.low_flow_detected = False

    db.commit()
    db.refresh(state)

    return {
        "message": "Low-flow configuration updated successfully",
        "sensor_id": sensor_id,
        "threshold_lpm": state.low_flow_threshold_lpm,
        "confirmation_seconds": state.low_flow_confirmation_seconds
    }

@router.post("/device/control")
def control_device(
    payload: DeviceControlRequest,
    sensor_id: str = "SENSOR-101",
    db: Session = Depends(get_db), current_user: User = Depends(require_warden)
):
    get_warden_sensor(db, sensor_id, current_user)
    state = get_or_create_device_state(db, sensor_id)

    command = payload.command

    # Validate command against current device state
    if command == "START" and state.is_running:
        raise HTTPException(
            status_code=409,
            detail="Device is already running"
        )

    if command == "STOP" and not state.is_running:
        raise HTTPException(
            status_code=409,
            detail="Device is already stopped"
        )

    if command == "RESET" and not state.is_running:
        raise HTTPException(
            status_code=409,
            detail="Cannot reset: device is stopped"
        )

    # Queue the command for ESP32
    state.command_id += 1
    state.desired_command = command

    db.commit()
    db.refresh(state)

    return {
        "message": f"{command} command queued successfully",
        "device_id": state.device_id,
        "command_id": state.command_id,
        "command": state.desired_command
    }
@router.get("/device/command", response_model=DeviceCommandOut)
def get_device_command(
    device_id: str = "ESP32-101",
    sensor_id: str = "SENSOR-101",
    db: Session = Depends(get_db), device_auth: None = Depends(require_device_key)
):
    state = get_or_create_device_state(db, sensor_id)

    if state.device_id != device_id:
        raise HTTPException(
            status_code=404,
            detail="Device not found"
        )

    return {
       "device_id": state.device_id,
       "command_id": state.command_id,
       "command": state.desired_command,

       "water_limit_litres": state.water_limit_litres,
       "continuous_flow_seconds": state.continuous_flow_seconds,

       "low_flow_threshold_lpm": state.low_flow_threshold_lpm,
       "low_flow_confirmation_seconds": state.low_flow_confirmation_seconds
    }


def _add_device_water_reading(
    db: Session,
    sensor: Sensor,
    at: datetime,
    flow_rate_lpm: float,
    previous_total_litres: float,
    current_total_litres: float,
):
    """Persist only positive cumulative-volume deltas from ESP32 heartbeats."""
    delta = max(0.0, current_total_litres - previous_total_litres)
    if delta <= 0.000001:
        return False

    db.add(
        WaterReading(
            room_id=sensor.room_id,
            sensor_id=sensor.id,
            timestamp=at,
            flow_rate_lpm=flow_rate_lpm,
            interval_volume_litres=delta,
            cumulative_volume_litres=current_total_litres,
        )
    )
    return True


@router.post("/device/heartbeat")
def device_heartbeat(
    payload: DeviceHeartbeat,
    db: Session = Depends(get_db), device_auth: None = Depends(require_device_key)
):
    state = get_or_create_device_state(db, payload.sensor_id)
    sensor = db.get(Sensor, payload.sensor_id)
    if sensor is None:
        raise HTTPException(status_code=404, detail="Sensor not found")

    if state.device_id != payload.device_id:
        raise HTTPException(status_code=404, detail="Device ID mismatch")

    if payload.acknowledged_command_id > state.command_id:
        raise HTTPException(status_code=400, detail="Invalid command acknowledgment")

    now = now_utc_naive()
    previous_running = state.is_running
    previous_low_flow = state.low_flow_detected
    previous_acknowledged_id = state.acknowledged_command_id

    state.last_seen_at = now
    sensor.last_seen_at = now

    new_command_acknowledged = (
        payload.acknowledged_command_id == state.command_id
        and payload.acknowledged_command_id > previous_acknowledged_id
    )

    if payload.acknowledged_command_id == state.command_id:
        state.acknowledged_command_id = payload.acknowledged_command_id
        state.is_running = payload.is_running

    session = (
        db.query(MonitoringSession)
        .filter_by(sensor_id=payload.sensor_id, status="RUNNING")
        .order_by(MonitoringSession.started_at.desc())
        .first()
    )

    reading_added = False

    # RESET acknowledgement: persist the final delta, close the old session,
    # then open a new session with a zero cumulative counter.
    reset_acknowledged = (
        new_command_acknowledged
        and state.desired_command == "RESET"
        and previous_running
        and state.is_running
    )
    if reset_acknowledged:
        if session:
            previous_total = session.total_litres
            final_total = (
                payload.reset_previous_total_litres
                if payload.reset_previous_total_litres is not None
                else max(previous_total, payload.cumulative_volume_litres)
            )
            reading_added |= _add_device_water_reading(
                db, sensor, now, payload.flow_rate_lpm,
                previous_total, final_total
            )
            session.total_litres = max(previous_total, final_total)
            session.ended_at = now
            session.status = "COMPLETED"
            session.ended_by = "RESET"

        state.low_flow_since = None
        state.low_flow_detected = False

        session = MonitoringSession(
            room_id=sensor.room_id,
            sensor_id=payload.sensor_id,
            device_id=state.device_id,
            started_at=now,
            total_litres=0.0,
            water_limit_litres=state.water_limit_litres,
            continuous_flow_seconds=state.continuous_flow_seconds,
            low_flow_threshold_lpm=state.low_flow_threshold_lpm,
            low_flow_confirmation_seconds=state.low_flow_confirmation_seconds,
            status="RUNNING",
        )
        db.add(session)
        db.flush()

    # START acknowledgement: create a session only after ESP32 confirms it.
    elif (
        new_command_acknowledged
        and state.desired_command == "START"
        and not previous_running
        and state.is_running
        and session is None
    ):
        session = MonitoringSession(
            room_id=sensor.room_id,
            sensor_id=payload.sensor_id,
            device_id=state.device_id,
            started_at=now,
            total_litres=0.0,
            water_limit_litres=state.water_limit_litres,
            continuous_flow_seconds=state.continuous_flow_seconds,
            low_flow_threshold_lpm=state.low_flow_threshold_lpm,
            low_flow_confirmation_seconds=state.low_flow_confirmation_seconds,
            status="RUNNING",
        )
        db.add(session)
        db.flush()

    # Persist incremental consumption while the session is running.
    if state.is_running:
        state.last_flow_rate_lpm = payload.flow_rate_lpm

        if session:
            previous_total = session.total_litres
            current_total = payload.cumulative_volume_litres

            if current_total >= previous_total:
                reading_added |= _add_device_water_reading(
                    db, sensor, now, payload.flow_rate_lpm,
                    previous_total, current_total
                )
                session.total_litres = current_total
            # If the device counter unexpectedly moves backwards, preserve
            # the server-side session total. RESET is the supported reset path.

            if payload.water_limit_warning_triggered:
                if not session.limit_warning:
                    session.limit_warning_at = now
                session.limit_warning = True

            if payload.device_continuous_warning_triggered:
                if not session.continuous_warning:
                    session.continuous_warning_at = now
                session.continuous_warning = True

        # Zero flow is idle, not low flow. A threshold of zero disables
        # low-flow detection entirely.
        if (
            state.low_flow_threshold_lpm > 0
            and payload.flow_rate_lpm > 0
            and payload.flow_rate_lpm < state.low_flow_threshold_lpm
        ):
            if state.low_flow_since is None:
                state.low_flow_since = now

            elapsed = (now - state.low_flow_since).total_seconds()
            if elapsed >= state.low_flow_confirmation_seconds:
                state.low_flow_detected = True
        else:
            state.low_flow_since = None
            state.low_flow_detected = False

        if session and state.low_flow_detected:
            if not session.low_flow_warning:
                session.low_flow_warning_at = now
            session.low_flow_warning = True

    else:
        state.last_flow_rate_lpm = 0.0
        state.low_flow_since = None
        state.low_flow_detected = False

    if state.low_flow_detected and not previous_low_flow:
        db.add(
            Alert(
                room_id=sensor.room_id,
                alert_type="low_flow",
                severity="medium",
                message=(
                    f"Low flow detected: {payload.flow_rate_lpm:.2f} L/min. "
                    "Possible blockage or restricted water supply."
                ),
            )
        )

    # STOP acknowledgement: save any final unrecorded volume and close session.
    stop_acknowledged = (
        new_command_acknowledged
        and state.desired_command == "STOP"
        and previous_running
        and not state.is_running
    )
    if stop_acknowledged and session:
        previous_total = session.total_litres
        final_total = max(previous_total, payload.cumulative_volume_litres)
        reading_added |= _add_device_water_reading(
            db, sensor, now, payload.flow_rate_lpm,
            previous_total, final_total
        )
        session.total_litres = final_total
        session.ended_at = now
        session.status = "COMPLETED"
        session.ended_by = "STOP"

    db.commit()

    # Run aggregate alert checks only after the reading transaction is saved.
    if reading_added:
        check_daily_limit(db, sensor.room_id, now)
        check_continuous_flow(db, sensor.room_id, now)

    return {
        "message": "Heartbeat received",
        "device_id": state.device_id,
        "is_running": state.is_running,
        "acknowledged_command_id": state.acknowledged_command_id,
        "flow_rate_lpm": state.last_flow_rate_lpm,
        "low_flow_detected": state.low_flow_detected,
        "session_id": session.id if session else None,
        "session_total_litres": session.total_litres if session else 0.0,
    }


@router.get("/device/status")
def device_status(
    sensor_id: str = "SENSOR-101",
    db: Session = Depends(get_db), current_user: User = Depends(require_warden)
):
    get_warden_sensor(db, sensor_id, current_user)
    state = get_or_create_device_state(db, sensor_id)
    now = now_utc_naive()

    online = (
        state.last_seen_at is not None
        and (now - state.last_seen_at).total_seconds() <= 15
    )
    acknowledged = state.acknowledged_command_id == state.command_id

    session = (
        db.query(MonitoringSession)
        .filter_by(sensor_id=sensor_id, status="RUNNING")
        .order_by(MonitoringSession.started_at.desc())
        .first()
    )
    sensor = db.get(Sensor, sensor_id)
    today = day_total(db, sensor.room_id, now) if sensor else 0.0

    return {
        "device_id": state.device_id,
        "online": online,
        "desired_command": state.desired_command,
        "command_id": state.command_id,
        "acknowledged_command_id": state.acknowledged_command_id,
        "command_acknowledged": acknowledged,
        "is_running": state.is_running if online and acknowledged else False,
        "flow_rate_lpm": state.last_flow_rate_lpm if online and state.is_running else 0.0,
        "low_flow_threshold_lpm": state.low_flow_threshold_lpm,
        "low_flow_confirmation_seconds": state.low_flow_confirmation_seconds,
        "water_limit_litres": state.water_limit_litres,
        "continuous_flow_seconds": state.continuous_flow_seconds,
        "low_flow_detected": (
            state.low_flow_detected
            if online and state.is_running and state.low_flow_threshold_lpm > 0
            else False
        ),
        "last_seen_at": state.last_seen_at,
        "session_id": session.id if session else None,
        "session_total_litres": session.total_litres if session else 0.0,
        "today_litres": round(today, 3),
    }
