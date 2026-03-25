from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.models.user import User
from backend.models.engineer_profile import EngineerProfile
from backend.schemas.engineer_profile import EngineerProfileCreate, EngineerProfileResponse

router = APIRouter(prefix="/engineers", tags=["engineers"])


@router.post("/profile", response_model=EngineerProfileResponse, status_code=status.HTTP_201_CREATED)
def create_engineer_profile(payload: EngineerProfileCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.role != "engineer":
        raise HTTPException(status_code=400, detail="User is not an engineer")

    existing_profile = db.query(EngineerProfile).filter(EngineerProfile.user_id == payload.user_id).first()
    if existing_profile:
        raise HTTPException(status_code=400, detail="Engineer profile already exists")

    profile = EngineerProfile(
        user_id=payload.user_id,
        title=payload.title,
        bio=payload.bio,
        skills=payload.skills,
        hourly_rate=payload.hourly_rate,
        country=payload.country,
        city=payload.city,
        linkedin_url=payload.linkedin_url,
        portfolio_url=payload.portfolio_url,
    )

    db.add(profile)
    db.commit()
    db.refresh(profile)

    return profile