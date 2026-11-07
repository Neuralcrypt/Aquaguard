from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict


# ==========================================
# DEVICE CONTROL SCHEMAS
# ==========================================

class DeviceControlRequest(BaseModel):
    command: Literal["START", "STOP", "RESET"]


class DeviceCommandOut(BaseModel):
    device_id: str
    command_id: int
    command: Literal["START", "STOP", "RESET"]

    water_limit_litres: float
    continuous_flow_seconds: int

    low_flow_threshold_lpm: float
    low_flow_confirmation_seconds: int

class DeviceHeartbeat(BaseModel):
    device_id: str = "ESP32-101"
    sensor_id: str = "SENSOR-101"

    acknowledged_command_id: int = Field(ge=0)

    is_running: bool
    flow_rate_lpm: float = Field(ge=0, le=200)

    cumulative_volume_litres: float = Field(
        ge=0, le=100000, default=0.0
    )

    # Used to preserve the previous session total during RESET
    reset_previous_total_litres: float | None = Field(
        default=None,
        ge=0,
        le=100000
    )

    water_limit_warning_triggered: bool = False

    device_continuous_warning_triggered: bool = False


class DeviceStateOut(BaseModel):
    sensor_id: str
    device_id: str
    desired_command: str
    command_id: int
    acknowledged_command_id: int
    is_running: bool
    last_seen_at: datetime | None

    last_flow_rate_lpm: float
    low_flow_threshold_lpm: float
    low_flow_confirmation_seconds: int
    low_flow_since: datetime | None
    low_flow_detected: bool

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# LOW FLOW CONFIGURATION
# ==========================================

class LowFlowConfigUpdate(BaseModel):
    threshold_lpm: float = Field(ge=0, le=200)
    confirmation_seconds: int = Field(ge=1, le=300)

class WaterLimitUpdate(BaseModel):
    water_limit_litres: float = Field(ge=1, le=1000)


class ContinuousFlowConfigUpdate(BaseModel):
    duration_seconds: int = Field(ge=10, le=1800)
# ==========================================
# MONITORING SESSION HISTORY
# ==========================================

class MonitoringSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    room_id: str
    sensor_id: str
    device_id: str

    started_at: datetime
    ended_at: datetime | None

    total_litres: float

    limit_warning: bool
    continuous_warning: bool
    low_flow_warning: bool

    limit_warning_at: datetime | None
    continuous_warning_at: datetime | None
    low_flow_warning_at: datetime | None

    status: str
    ended_by: str | None

class ReadingCreate(BaseModel):
    room_id: str = "ROOM-101"
    sensor_id: str = "SENSOR-101"
    device_sequence: str | None = None
    timestamp: datetime | None = None
    flow_rate_lpm: float = Field(ge=0, le=200)
    interval_volume_litres: float = Field(ge=0, le=10000)
    cumulative_volume_litres: float | None = Field(default=None, ge=0)

class ReadingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    room_id: str
    sensor_id: str
    device_sequence: str | None
    timestamp: datetime
    flow_rate_lpm: float
    interval_volume_litres: float
    cumulative_volume_litres: float | None

class SettingUpdate(BaseModel):
    daily_limit_litres: float = Field(gt=0, le=100000)
    continuous_flow_minutes: int = Field(ge=1, le=1440)

class SettingOut(SettingUpdate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    room_id: str
    season: str

class CalibrationUpdate(BaseModel):
    pulses_per_litre: float = Field(gt=0, le=100000)

class AlertStatusUpdate(BaseModel):
    status: str

class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    room_id: str
    alert_type: str
    severity: str
    message: str
    status: str
    created_at: datetime
    resolved_at: datetime | None


class RoomCreate(BaseModel):
    id: str = Field(min_length=1, max_length=50, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=100)
    daily_limit_litres: float = Field(default=350, gt=0, le=100000)
    continuous_flow_minutes: int = Field(default=15, ge=1, le=1440)


class RoomUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class RoomOut(BaseModel):
    id: str
    name: str
    created_at: datetime
    sensor_id: str | None = None
    sensor_status: str
    sensor_issue: str | None = None
    last_seen_at: datetime | None = None
    daily_limit_litres: float
    today_litres: float
    pending_alerts: int
