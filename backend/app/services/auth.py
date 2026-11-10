
import os

from sqlalchemy.orm import Session

from app.models.auth import User
from app.core.security import hash_password


def ensure_admin_exists(db: Session):
    admin = (
        db.query(User)
        .filter(User.username == "admin")
        .first()
    )

    if admin is not None:
        return

    admin_password = os.getenv("ADMIN_PASSWORD", "123456")

    if len(admin_password) < 6:
        raise ValueError("ADMIN_PASSWORD must contain at least 6 characters")

    admin = User(
        username="admin",
        password_hash=hash_password(admin_password),
        role="admin",
        hostel_id=None,
        is_active=True,
        token_version=0,
    )

    db.add(admin)
    db.commit()
