
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.models.auth import Hostel


def migrate_hostel_data(db: Session) -> int:
    """Safely add hostel ownership and assign legacy rooms."""

    inspector = inspect(db.get_bind())

    # Add the hostel_id column and foreign key if missing.
    columns = {
        column["name"]
        for column in inspector.get_columns("rooms")
    }

    if "hostel_id" not in columns:
        db.execute(
            text(
                """
                ALTER TABLE rooms
                ADD COLUMN hostel_id INTEGER
                REFERENCES hostels(id)
                """
            )
        )

    # Find or create the initial Bamashah Hostel.
    hostel = (
        db.query(Hostel)
        .filter(Hostel.is_initial.is_(True))
        .first()
    )

    if hostel is None:
        hostel = Hostel(
            hostel_name="Bamashah Hostel",
            is_initial=True,
            is_active=True,
        )
        db.add(hostel)
        db.flush()

    # Preserve existing assignments; assign only unassigned rooms.
    db.execute(
        text(
            """
            UPDATE rooms
            SET hostel_id = :hostel_id
            WHERE hostel_id IS NULL
            """
        ),
        {"hostel_id": hostel.id},
    )

    # Create an index if it does not already exist.
    db.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS ix_rooms_hostel_id
            ON rooms(hostel_id)
            """
        )
    )

    db.commit()

    return hostel.id
