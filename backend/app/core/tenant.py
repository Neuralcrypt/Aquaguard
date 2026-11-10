import hmac
import os

from fastapi import Header, HTTPException, status
from sqlalchemy.orm import Session

from app.models.auth import User
from app.models.models import Alert, Room, Sensor


def require_device_key(
    x_device_key: str | None = Header(default=None, alias="X-Device-Key"),
):
    configured_key = os.getenv("DEVICE_API_KEY")

    if not configured_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Device authentication is not configured",
        )

    if not x_device_key or not hmac.compare_digest(
        x_device_key, configured_key
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid device key",
        )


def get_warden_room(
    db: Session,
    room_id: str,
    current_user: User,
) -> Room:
    room = (
        db.query(Room)
        .filter(
            Room.id == room_id,
            Room.hostel_id == current_user.hostel_id,
        )
        .first()
    )

    if room is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found",
        )

    return room


def get_warden_sensor(
    db: Session,
    sensor_id: str,
    current_user: User,
) -> Sensor:
    sensor = (
        db.query(Sensor)
        .join(Room, Sensor.room_id == Room.id)
        .filter(
            Sensor.id == sensor_id,
            Room.hostel_id == current_user.hostel_id,
        )
        .first()
    )

    if sensor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sensor not found",
        )

    return sensor


def get_warden_alert(
    db: Session,
    alert_id: int,
    current_user: User,
) -> Alert:
    alert = (
        db.query(Alert)
        .join(Room, Alert.room_id == Room.id)
        .filter(
            Alert.id == alert_id,
            Room.hostel_id == current_user.hostel_id,
        )
        .first()
    )

    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        )

    return alert
