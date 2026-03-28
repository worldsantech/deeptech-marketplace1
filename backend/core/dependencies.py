from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from backend.core.roles import ensure_active_user, ensure_allowed_role, ensure_customer, ensure_provider
from backend.core.security import decode_access_token
from backend.database.session import get_db

bearer_scheme = HTTPBearer(auto_error=False)


def _credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )


def _decode_user_id_from_credentials(
    credentials: Optional[HTTPAuthorizationCredentials],
) -> Optional[int]:
    if credentials is None:
        return None

    try:
        token = credentials.credentials
        payload = decode_access_token(token)
        user_id = payload.get("sub")

        if user_id is None:
            raise _credentials_exception()

        return int(user_id)
    except (JWTError, TypeError, ValueError):
        raise _credentials_exception()


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    from backend.models.user import User

    user_id = _decode_user_id_from_credentials(credentials)

    if user_id is None:
        raise _credentials_exception()

    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise _credentials_exception()

    user = ensure_allowed_role(user)
    user = ensure_active_user(user)

    return user


def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    from backend.models.user import User

    if credentials is None:
        return None

    user_id = _decode_user_id_from_credentials(credentials)
    if user_id is None:
        return None

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        return None

    try:
        user = ensure_allowed_role(user)
        user = ensure_active_user(user)
    except HTTPException:
        return None

    return user


def get_current_customer(
    current_user=Depends(get_current_user),
):
    return ensure_customer(current_user)


def get_current_provider(
    current_user=Depends(get_current_user),
):
    return ensure_provider(current_user)