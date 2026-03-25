from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.models.provider_profile import ProviderProfile
from backend.models.review import Review
from backend.models.user import User

router = APIRouter(prefix="/search/providers", tags=["Search"])


ALLOWED_PROVIDER_SORTS = ["newest", "rating"]


@router.get("/")
def search_providers(
    skills: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    availability: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("newest"),
    db: Session = Depends(get_db),
):
    if sort_by not in ALLOWED_PROVIDER_SORTS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sort_by. Allowed values: {', '.join(ALLOWED_PROVIDER_SORTS)}"
        )

    base_query = (
        db.query(
            User,
            ProviderProfile,
            func.avg(Review.rating).label("average_rating"),
            func.count(Review.id).label("reviews_count"),
        )
        .join(ProviderProfile, ProviderProfile.user_id == User.id)
        .outerjoin(Review, Review.reviewed_user_id == User.id)
        .filter(User.role == "Provider")
        .group_by(User.id, ProviderProfile.id)
    )

    if country:
        base_query = base_query.filter(ProviderProfile.country == country)

    if availability:
        base_query = base_query.filter(ProviderProfile.availability == availability)

    if skills:
        base_query = base_query.filter(ProviderProfile.skills.ilike(f"%{skills}%"))

    total = base_query.count()

    if sort_by == "newest":
        base_query = base_query.order_by(User.id.desc())
    elif sort_by == "rating":
        base_query = base_query.order_by(
            func.avg(Review.rating).desc().nullslast(),
            func.count(Review.id).desc(),
            User.id.desc(),
        )

    rows = base_query.offset(offset).limit(limit).all()

    items = []
    for user, profile, average_rating, reviews_count in rows:
        items.append(
            {
                "user": {
                    "id": user.id,
                    "full_name": user.full_name,
                    "role": user.role,
                },
                "profile": {
                    "bio": profile.bio,
                    "skills": profile.skills,
                    "country": profile.country,
                    "availability": profile.availability,
                },
                "stats": {
                    "average_rating": round(float(average_rating), 2) if average_rating is not None else None,
                    "reviews_count": int(reviews_count or 0),
                },
            }
        )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "sort_by": sort_by,
        "items": items,
    }