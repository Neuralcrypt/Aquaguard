
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.models import (
    Alert,
    SeasonalSetting,
    WaterReading,
    Sensor,
)

SEASONS = ("Summer", "Monsoon", "Winter")


def current_season(month: int) -> str:
    # Prototype policy; replace with the university's agreed calendar if needed.
    if month in (3, 4, 5, 6):
        return "Summer"
    if month in (7, 8, 9, 10):
        return "Monsoon"
    return "Winter"


def ensure_defaults(db: Session, room_id="ROOM-101", hostel_id=None):
    from app.models.models import Room

    room = db.get(Room, room_id)

    if not room:
        if hostel_id is None:
            raise ValueError("hostel_id is required when creating a room")

        room = Room(
            id=room_id,
            name="Room 101" if room_id == "ROOM-101" else room_id,
            hostel_id=hostel_id,
        )
        db.add(room)
        db.flush()

    if not db.get(Sensor, "SENSOR-101"):
        db.add(
            Sensor(
                id="SENSOR-101",
                room_id=room_id,
                calibration_pulses_per_litre=450.0,
            )
        )

    for season in SEASONS:
        exists = (
            db.query(SeasonalSetting)
            .filter_by(room_id=room_id, season=season)
            .first()
        )

        if not exists:
            db.add(
                SeasonalSetting(
                    room_id=room_id,
                    season=season,
                    daily_limit_litres=350.0,
                    continuous_flow_minutes=15,
                )
            )

    db.commit()


def day_total(db: Session, room_id: str, at: datetime):
    start = at.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)

    return float(
        db.query(
            func.coalesce(
                func.sum(WaterReading.interval_volume_litres),
                0.0,
            )
        )
        .filter(
            WaterReading.room_id == room_id,
            WaterReading.timestamp >= start,
            WaterReading.timestamp < end,
        )
        .scalar()
        or 0.0
    )


def check_daily_limit(db: Session, room_id: str, at: datetime):
    setting = (
        db.query(SeasonalSetting)
        .filter_by(
            room_id=room_id,
            season=current_season(at.month),
        )
        .first()
    )

    if not setting:
        return

    total = day_total(db, room_id, at)

    if total > setting.daily_limit_litres:
        start = at.replace(hour=0, minute=0, second=0, microsecond=0)

        exists = (
            db.query(Alert)
            .filter(
                Alert.room_id == room_id,
                Alert.alert_type == "daily_limit",
                Alert.created_at >= start,
                Alert.status != "Resolved",
            )
            .first()
        )

        if not exists:
            db.add(
                Alert(
                    room_id=room_id,
                    alert_type="daily_limit",
                    severity="high",
                    message=(
                        f"Daily usage {total:.1f} L exceeded the "
                        f"{setting.daily_limit_litres:.1f} L limit."
                    ),
                )
            )
            db.commit()


def check_continuous_flow(db: Session, room_id: str, at: datetime):
    setting = (
        db.query(SeasonalSetting)
        .filter_by(
            room_id=room_id,
            season=current_season(at.month),
        )
        .first()
    )

    if not setting:
        return

    since = at - timedelta(minutes=setting.continuous_flow_minutes)

    readings = (
        db.query(WaterReading)
        .filter(
            WaterReading.room_id == room_id,
            WaterReading.timestamp >= since,
            WaterReading.timestamp <= at,
        )
        .order_by(WaterReading.timestamp.asc())
        .all()
    )

    if len(readings) < 2:
        return

    if any(reading.flow_rate_lpm <= 0 for reading in readings):
        return

    elapsed_seconds = (
        readings[-1].timestamp - readings[0].timestamp
    ).total_seconds()

    if elapsed_seconds < setting.continuous_flow_minutes * 60:
        return

    exists = (
        db.query(Alert)
        .filter(
            Alert.room_id == room_id,
            Alert.alert_type == "continuous_flow",
            Alert.status != "Resolved",
            Alert.created_at >= since,
        )
        .first()
    )

    if not exists:
        db.add(
            Alert(
                room_id=room_id,
                alert_type="continuous_flow",
                severity="medium",
                message=(
                    f"Flow remained active for at least "
                    f"{setting.continuous_flow_minutes} minutes. "
                    "Please investigate."
                ),
            )
        )
        db.commit()
