from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.models.application import Application
from backend.models.project import Project
from backend.models.provider_profile import ProviderProfile
from backend.models.review import Review
from backend.models.user import User

router = APIRouter(prefix="/featured", tags=["Featured"])


@router.get("/providers")
def get_featured_providers(
    limit: int = Query(6, ge=1, le=50),
    db: Session = Depends(get_db),
):
    rows = (
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
        .order_by(
            func.avg(Review.rating).desc().nullslast(),
            func.count(Review.id).desc(),
            User.id.desc(),
        )
        .limit(limit)
        .all()
    )

    items = []
    for user, profile, average_rating, reviews_count in rows:
        completed_projects_count = (
            db.query(Project)
            .filter(
                Project.selected_applicant_user_id == user.id,
                Project.status == "completed",
            )
            .count()
        )

        active_projects_count = (
            db.query(Project)
            .filter(
                Project.selected_applicant_user_id == user.id,
                Project.status == "in_progress",
            )
            .count()
        )

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
                    "completed_projects_count": completed_projects_count,
                    "active_projects_count": active_projects_count,
                },
            }
        )

    return {
        "total": len(items),
        "items": items,
    }


@router.get("/projects")
def get_featured_projects(
    limit: int = Query(8, ge=1, le=50),
    country: Optional[str] = Query(None),
    project_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Project).filter(Project.status == "open")

    if country:
        query = query.filter(Project.country == country)

    if project_type:
        query = query.filter(Project.project_type == project_type)

    projects = (
        query.order_by(Project.id.desc())
        .limit(limit)
        .all()
    )

    items = []
    for project in projects:
        applications_count = (
            db.query(Application)
            .filter(Application.project_id == project.id)
            .count()
        )

        items.append(
            {
                "id": project.id,
                "title": project.title,
                "description": project.description,
                "country": project.country,
                "project_type": project.project_type,
                "budget_min": project.budget_min,
                "budget_max": project.budget_max,
                "status": project.status,
                "owner_id": project.owner_id,
                "applications_count": applications_count,
            }
        )

    return {
        "total": len(items),
        "items": items,
    }