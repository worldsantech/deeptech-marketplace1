from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.core.dependencies import get_current_user
from backend.core.roles import ROLE_CUSTOMER, ROLE_PROVIDER
from backend.database.session import get_db
from backend.models.customer_profile import CustomerProfile
from backend.models.provider_profile import ProviderProfile
from backend.models.user import User
from backend.schemas.profile import (
    CustomerProfileResponse,
    CustomerProfileUpdate,
    MyProfileResponse,
    ProviderProfileResponse,
    ProviderProfileUpdate,
)

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("/me", response_model=MyProfileResponse)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    customer_profile = None
    provider_profile = None

    if current_user.role == ROLE_CUSTOMER:
        customer_profile = (
            db.query(CustomerProfile)
            .filter(CustomerProfile.user_id == current_user.id)
            .first()
        )
    elif current_user.role == ROLE_PROVIDER:
        provider_profile = (
            db.query(ProviderProfile)
            .filter(ProviderProfile.user_id == current_user.id)
            .first()
        )

    return MyProfileResponse(
        role=current_user.role,
        user_id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        customer_profile=customer_profile,
        provider_profile=provider_profile,
    )


@router.put("/me/customer", response_model=CustomerProfileResponse)
def upsert_customer_profile(
    payload: CustomerProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != ROLE_CUSTOMER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Customer can update customer profile",
        )

    profile = (
        db.query(CustomerProfile)
        .filter(CustomerProfile.user_id == current_user.id)
        .first()
    )

    if not profile:
        profile = CustomerProfile(user_id=current_user.id)
        db.add(profile)
        db.flush()

    update_data = payload.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)

    return profile


@router.put("/me/provider", response_model=ProviderProfileResponse)
def upsert_provider_profile(
    payload: ProviderProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != ROLE_PROVIDER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Provider can update provider profile",
        )

    profile = (
        db.query(ProviderProfile)
        .filter(ProviderProfile.user_id == current_user.id)
        .first()
    )

    if not profile:
        profile = ProviderProfile(user_id=current_user.id)
        db.add(profile)
        db.flush()

    update_data = payload.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)

    return profile


@router.get("/providers/{user_id}", response_model=ProviderProfileResponse)
def get_provider_profile(user_id: int, db: Session = Depends(get_db)):
    profile = db.query(ProviderProfile).filter(ProviderProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider profile not found",
        )
    return profile


@router.get("/customers/{user_id}", response_model=CustomerProfileResponse)
def get_customer_profile(user_id: int, db: Session = Depends(get_db)):
    profile = db.query(CustomerProfile).filter(CustomerProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer profile not found",
        )
    return profile