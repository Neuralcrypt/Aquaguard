from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.auth import Hostel, User
from app.core.security import decode_access_token


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise unauthorized

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = payload.get("sub")
        token_version = payload.get("ver")

        if user_id is None or token_version is None:
            raise unauthorized

        user = db.query(User).filter(User.id == int(user_id)).first()

        if (
            user is None
            or not user.is_active
            or user.token_version != token_version
        ):
            raise unauthorized

        if user.role == "warden":
            hostel = db.get(Hostel, user.hostel_id)
            if hostel is None or not hostel.is_active:
                raise unauthorized

        return user

    except HTTPException:
        raise
    except Exception:
        raise unauthorized


def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


def require_warden(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != "warden":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Warden access required",
        )
    return current_user