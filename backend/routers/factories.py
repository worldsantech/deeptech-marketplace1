from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.models.user import User
from backend.models.factory_profile import FactoryProfile
from backend.schemas.factory_profile import FactoryProfileCreate, FactoryProfileResponse

router = APIRouter(prefix="/factories", tags=["factories"])


@router.post("/profile", response_model=FactoryProfileResponse, status_code=status.HTTP_201_CREATED)
def create_factory_profile(payload: FactoryProfileCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.role != "factory":
        raise HTTPException(status_code=400, detail="User is not a factory")

    existing_profile = db.query(FactoryProfile).filter(FactoryProfile.user_id == payload.user_id).first()
    if existing_profile:
        raise HTTPException(status_code=400, detail="Factory profile already exists")

    profile = FactoryProfile(
        user_id=payload.user_id,
        company_name=payload.company_name,
        description=payload.description,
        capabilities=payload.capabilities,
        min_order_value=payload.min_order_value,
        country=payload.country,
        city=payload.city,
        website_url=payload.website_url,
    )

    db.add(profile)
    db.commit()
    db.refresh(profile)

    return profile