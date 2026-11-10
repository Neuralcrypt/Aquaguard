
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.auth import Hostel, User
from app.schemas.auth import LoginRequest, LoginResponse
from app.core.security import verify_password, create_access_token


router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    # Find the account by username.
    user = (
        db.query(User)
        .filter(User.username == payload.username)
        .first()
    )

    # Use a generic error for invalid credentials.
    if user is None or not verify_password(
        payload.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is inactive",
        )

    hostel_name = None

    # Verify that a warden belongs to an active hostel.
    if user.role == "warden":
        hostel = db.get(Hostel, user.hostel_id)

        if hostel is None or not hostel.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This hostel account is inactive",
            )

        hostel_name = hostel.hostel_name

    elif user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid account role",
        )

    # Create a signed access token.
    access_token = create_access_token(
        {
            "sub": str(user.id),
            "ver": user.token_version,
        }
    )

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        role=user.role,
        username=user.username,
        hostel_id=user.hostel_id,
        hostel_name=hostel_name,
    )
