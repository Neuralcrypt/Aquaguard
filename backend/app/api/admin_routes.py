
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import require_admin
from app.core.security import hash_password
from app.db.session import get_db
from app.models.auth import Hostel, User
from app.models.models import Room
from app.schemas.auth import (
    HostelCreate,
    HostelOut,
    HostelUpdate,
    PasswordReset,
    UsernameUpdate,
)

router = APIRouter(
    prefix="/api/admin",
    tags=["Hostel administration"],
)


def get_warden(db: Session, hostel_id: int):
    return (
        db.query(User)
        .filter(
            User.hostel_id == hostel_id,
            User.role == "warden",
        )
        .order_by(User.id.asc())
        .first()
    )


@router.get("/hostels", response_model=list[HostelOut])
def list_hostels(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    hostels = db.query(Hostel).order_by(Hostel.id.asc()).all()
    return [
        HostelOut(
            id=hostel.id,
            hostel_name=hostel.hostel_name,
            username=(warden.username if (warden := get_warden(db, hostel.id)) else ""),
            is_active=hostel.is_active,
        )
        for hostel in hostels
    ]


@router.post(
    "/hostels",
    response_model=HostelOut,
    status_code=status.HTTP_201_CREATED,
)
def create_hostel(
    payload: HostelCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(409, "This username is already in use")

    hostel = Hostel(
        hostel_name=payload.hostel_name.strip(),
        is_initial=False,
        is_active=True,
    )
    db.add(hostel)
    db.flush()

    warden = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role="warden",
        hostel_id=hostel.id,
        is_active=True,
        token_version=0,
    )
    db.add(warden)
    db.commit()
    db.refresh(hostel)

    return HostelOut(
        id=hostel.id,
        hostel_name=hostel.hostel_name,
        username=warden.username,
        is_active=hostel.is_active,
    )


@router.patch("/hostels/{hostel_id}", response_model=HostelOut)
def update_hostel(
    hostel_id: int,
    payload: HostelUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    hostel = db.get(Hostel, hostel_id)
    if hostel is None:
        raise HTTPException(404, "Hostel not found")

    hostel.hostel_name = payload.hostel_name.strip()
    hostel.is_active = payload.is_active

    db.commit()
    db.refresh(hostel)

    warden = get_warden(db, hostel.id)
    return HostelOut(
        id=hostel.id,
        hostel_name=hostel.hostel_name,
        username=warden.username if warden else "",
        is_active=hostel.is_active,
    )


@router.put("/hostels/{hostel_id}/username")
def update_hostel_username(
    hostel_id: int,
    payload: UsernameUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    hostel = db.get(Hostel, hostel_id)
    if hostel is None:
        raise HTTPException(404, "Hostel not found")

    warden = get_warden(db, hostel_id)
    if warden is None:
        raise HTTPException(404, "Warden account not found")

    new_username = payload.username.strip()

    existing = db.query(User).filter(
        User.username == new_username,
        User.id != warden.id,
    ).first()

    if existing:
        raise HTTPException(409, "This username is already in use")

    warden.username = new_username
    warden.token_version += 1
    db.commit()

    return {"message": "Hostel username updated successfully"}


@router.put("/hostels/{hostel_id}/password")
def reset_hostel_password(
    hostel_id: int,
    payload: PasswordReset,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    hostel = db.get(Hostel, hostel_id)
    if hostel is None:
        raise HTTPException(404, "Hostel not found")

    warden = get_warden(db, hostel_id)
    if warden is None:
        raise HTTPException(404, "Warden account not found")

    warden.password_hash = hash_password(payload.new_password)
    warden.token_version += 1
    db.commit()

    return {"message": "Hostel password reset successfully"}


@router.delete("/hostels/{hostel_id}")
def delete_hostel(
    hostel_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    hostel = db.get(Hostel, hostel_id)
    if hostel is None:
        raise HTTPException(404, "Hostel not found")

    # Never delete the original hostel containing legacy data.
    if hostel.is_initial:
        raise HTTPException(
            403,
            "The initial hostel cannot be deleted because it contains legacy monitoring data",
        )

    # Refuse deletion if rooms or their associated monitoring data exist.
    room_count = db.query(Room).filter(
        Room.hostel_id == hostel_id
    ).count()

    if room_count > 0:
        raise HTTPException(
            409,
            "Cannot delete this hostel because it contains rooms or monitoring data. Deactivate it instead.",
        )

    # Delete linked user accounts, then the empty hostel.
    db.query(User).filter(
        User.hostel_id == hostel_id
    ).delete(synchronize_session=False)

    db.delete(hostel)
    db.commit()

    return {"message": "Hostel account deleted successfully"}
