from fastapi import HTTPException, status

from backend.models.user import User

ROLE_CUSTOMER = "Customer"
ROLE_PROVIDER = "Provider"

ALLOWED_ROLES = {ROLE_CUSTOMER, ROLE_PROVIDER}


def is_customer(user: User) -> bool:
    return user.role == ROLE_CUSTOMER


def is_provider(user: User) -> bool:
    return user.role == ROLE_PROVIDER


def ensure_active_user(user: User) -> User:
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )
    return user


def ensure_customer(user: User) -> User:
    if not is_customer(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customer access required",
        )
    return user


def ensure_provider(user: User) -> User:
    if not is_provider(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Provider access required",
        )
    return user


def ensure_allowed_role(user: User) -> User:
    if user.role not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User role is not allowed",
        )
    return user