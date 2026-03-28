from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from backend.core.roles import ROLE_PROVIDER
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
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort_by. Allowed values: {', '.join(sorted(ALLOWED_PROVIDER_SORTS))}",
        )

    average_rating_expr = func.avg(Review.rating)
    reviews_count_expr = func.count(Review.id)

    query = (
        db.query(
            User,
            ProviderProfile,
            average_rating_expr.label("average_rating"),
            reviews_count_expr.label("reviews_count"),
        )
        .join(ProviderProfile, ProviderProfile.user_id == User.id)
        .outerjoin(Review, Review.reviewed_user_id == User.id)
        .filter(User.role == ROLE_PROVIDER)
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
        country_clean = country.strip()
        if country_clean:
            query = query.filter(ProviderProfile.country.ilike(country_clean))

    if availability:
        availability_clean = availability.strip()
        if availability_clean:
            query = query.filter(ProviderProfile.availability.ilike(availability_clean))

    if skills:
        skills_clean = skills.strip()
        if skills_clean:
            query = query.filter(ProviderProfile.skills.ilike(f"%{skills_clean}%"))

    total = query.count()

    if sort_by == "newest":
        query = query.order_by(User.created_at.desc(), User.id.desc())
    elif sort_by == "rating":
        query = query.order_by(
            average_rating_expr.desc().nullslast(),
            reviews_count_expr.desc(),
            User.id.desc(),
        )
    elif sort_by == "reviews_count":
        query = query.order_by(
            reviews_count_expr.desc(),
            average_rating_expr.desc().nullslast(),
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

    page = (offset // limit) + 1
    pages = (total + limit - 1) // limit

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