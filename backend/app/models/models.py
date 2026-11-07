from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from app.db.session import Base

def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

class Room(Base):
    __tablename__ = "rooms"
    id = Column(String, primary_key=True, default="ROOM-101")
    name = Column(String, nullable=False, default="Room 101")
    created_at = Column(DateTime, default=utcnow, nullable=False)

class Sensor(Base):
    __tablename__ = "sensors"
    id = Column(String, primary_key=True, default="SENSOR-101")
    room_id = Column(String, ForeignKey("rooms.id"), nullable=False, default="ROOM-101")
    calibration_pulses_per_litre = Column(Float, nullable=False, default=450.0)
    active = Column(Boolean, nullable=False, default=True)
    last_seen_at = Column(DateTime, nullable=True)

class SeasonalSetting(Base):
    __tablename__ = "seasonal_settings"
    __table_args__ = (UniqueConstraint("room_id", "season", name="uq_room_season"),)
    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(String, ForeignKey("rooms.id"), nullable=False, default="ROOM-101")
    season = Column(String, nullable=False)
    daily_limit_litres = Column(Float, nullable=False, default=350.0)
    continuous_flow_minutes = Column(Integer, nullable=False, default=15)

class WaterReading(Base):
    __tablename__ = "water_readings"
    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(String, ForeignKey("rooms.id"), nullable=False, index=True)
    sensor_id = Column(String, ForeignKey("sensors.id"), nullable=False, index=True)
    device_sequence = Column(String, nullable=True, unique=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    flow_rate_lpm = Column(Float, nullable=False)
    interval_volume_litres = Column(Float, nullable=False)
    cumulative_volume_litres = Column(Float, nullable=True)

class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(String, ForeignKey("rooms.id"), nullable=False, index=True)
    alert_type = Column(String, nullable=False)
    severity = Column(String, nullable=False, default="medium")
    message = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="Pending")
    created_at = Column(DateTime, default=utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)

class AnomalyResult(Base):
    __tablename__ = "anomaly_results"
    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(String, ForeignKey("rooms.id"), nullable=False)
    reading_id = Column(Integer, ForeignKey("water_readings.id"), nullable=True)
    timestamp = Column(DateTime, default=utcnow, nullable=False)
    score = Column(Float, nullable=True)
    is_anomaly = Column(Boolean, nullable=False)
    method = Column(String, nullable=False, default="statistical-baseline")
    details = Column(Text, nullable=True)

class DeviceState(Base):
    __tablename__ = "device_states"

    sensor_id = Column(
        String,
        ForeignKey("sensors.id"),
        primary_key=True
    )

    device_id = Column(String, nullable=False, unique=True, default="ESP32-101")
    desired_command = Column(String, nullable=False, default="STOP")
    command_id = Column(Integer, nullable=False, default=0)
    acknowledged_command_id = Column(Integer, nullable=False, default=0)
    is_running = Column(Boolean, nullable=False, default=False)
    last_seen_at = Column(DateTime, nullable=True)

    last_flow_rate_lpm = Column(Float, nullable=False, default=0.0)
    low_flow_threshold_lpm = Column(Float, nullable=False, default=8.5)
    low_flow_confirmation_seconds = Column(Integer, nullable=False, default=5)
    low_flow_since = Column(DateTime, nullable=True)
    low_flow_detected = Column(Boolean, nullable=False, default=False)
    water_limit_litres = Column(Float, nullable=False, default=1.0)
    continuous_flow_seconds = Column(Integer, nullable=False, default=30)

class MonitoringSession(Base):
    __tablename__ = "monitoring_sessions"

    id = Column(Integer, primary_key=True, index=True)

    room_id = Column(String, ForeignKey("rooms.id"), nullable=False, index=True)
    sensor_id = Column(String, ForeignKey("sensors.id"), nullable=False, index=True)
    device_id = Column(String, nullable=False)

    started_at = Column(DateTime, nullable=False, default=utcnow)
    ended_at = Column(DateTime, nullable=True)

    total_litres = Column(Float, nullable=False, default=0.0)

    limit_warning = Column(Boolean, nullable=False, default=False)
    continuous_warning = Column(Boolean, nullable=False, default=False)
    low_flow_warning = Column(Boolean, nullable=False, default=False)

    limit_warning_at = Column(DateTime, nullable=True)
    continuous_warning_at = Column(DateTime, nullable=True)
    low_flow_warning_at = Column(DateTime, nullable=True)

    status = Column(String, nullable=False, default="RUNNING")
    ended_by = Column(String, nullable=True)
    water_limit_litres = Column(Float, nullable=False, default=1.0)
    continuous_flow_seconds = Column(Integer, nullable=False, default=30)

    low_flow_threshold_lpm = Column(Float, nullable=False, default=8.5)

    low_flow_confirmation_seconds = Column(Integer, nullable=False, default=5)