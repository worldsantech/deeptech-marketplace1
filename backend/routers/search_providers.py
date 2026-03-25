from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.models.provider_profile import ProviderProfile
from backend.models.review import Review
from backend.models.user import User

router = APIRouter(prefix="/search/providers", tags=["Search"])

ALLOWED_PROVIDER_SORTS = {
    "newest",
    "rating",
    "reviews_count",
    "full_name",
}


@router.get("/")
def search_providers(
    q: Optional[str] = Query(None),
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
            detail=f"Invalid sort_by. Allowed values: {', '.join(sorted(ALLOWED_PROVIDER_SORTS))}",
        )

    query = (
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

    if q:
        q_clean = q.strip()
        if q_clean:
            pattern = f"%{q_clean}%"
            query = query.filter(
                or_(
                    User.full_name.ilike(pattern),
                    ProviderProfile.bio.ilike(pattern),
                    ProviderProfile.skills.ilike(pattern),
                    ProviderProfile.country.ilike(pattern),
                    ProviderProfile.availability.ilike(pattern),
                )
            )

    if country:
        query = query.filter(ProviderProfile.country.ilike(country.strip()))

    if availability:
        query = query.filter(ProviderProfile.availability.ilike(availability.strip()))

    if skills:
        query = query.filter(ProviderProfile.skills.ilike(f"%{skills.strip()}%"))

    total = query.count()

    if sort_by == "newest":
        query = query.order_by(User.id.desc())
    elif sort_by == "rating":
        query = query.order_by(
            func.avg(Review.rating).desc().nullslast(),
            func.count(Review.id).desc(),
            User.id.desc(),
        )
    elif sort_by == "reviews_count":
        query = query.order_by(
            func.count(Review.id).desc(),
            func.avg(Review.rating).desc().nullslast(),
            User.id.desc(),
        )
    elif sort_by == "full_name":
        query = query.order_by(User.full_name.asc(), User.id.desc())

    rows = query.offset(offset).limit(limit).all()

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

    page = (offset // limit) + 1 if limit else 1
    pages = (total + limit - 1) // limit if limit else 1

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "page": page,
        "pages": pages,
        "filters": {
            "q": q,
            "skills": skills,
            "country": country,
            "availability": availability,
            "sort_by": sort_by,
        },
        "items": items,
    }