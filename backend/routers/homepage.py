from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.core.dependencies import get_current_user
from backend.database.session import get_db
from backend.models.application import Application
from backend.models.project import Project
from backend.models.provider_profile import ProviderProfile
from backend.models.review import Review
from backend.models.saved_project import SavedProject
from backend.models.user import User

router = APIRouter(prefix="/homepage", tags=["Homepage"])


@router.get("/feed")
def get_homepage_feed(
    featured_providers_limit: int = Query(6, ge=1, le=20),
    featured_projects_limit: int = Query(8, ge=1, le=20),
    latest_projects_limit: int = Query(8, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    provider_rows = (
        db.query(
            User,
            ProviderProfile,
            func.avg(Review.rating),
            func.count(Review.id),
        )
        .join(ProviderProfile, ProviderProfile.user_id == User.id)
        .outerjoin(Review, Review.reviewed_user_id == User.id)
        .filter(User.role == "Provider")
        .group_by(User.id, ProviderProfile.id)
        .order_by(func.avg(Review.rating).desc().nullslast(), User.id.desc())
        .limit(featured_providers_limit)
        .all()
    )

    featured_providers = []
    for user, profile, avg_rating, reviews_count in provider_rows:
        featured_providers.append(
            {
                "user": {
                    "id": user.id,
                    "full_name": user.full_name,
                    "role": user.role,
                },
                "profile": {
                    "skills": profile.skills,
                    "country": profile.country,
                    "availability": profile.availability,
                },
                "stats": {
                    "average_rating": round(float(avg_rating), 2) if avg_rating else None,
                    "reviews_count": int(reviews_count or 0),
                },
            }
        )

    featured_projects = (
        db.query(Project)
        .filter(Project.status == "open")
        .order_by(Project.id.desc())
        .limit(featured_projects_limit)
        .all()
    )

    featured_projects_items = []
    for project in featured_projects:
        featured_projects_items.append(
            {
                "id": project.id,
                "title": project.title,
                "country": project.country,
                "city": project.city,
                "project_type": project.project_type,
                "budget_min": project.budget_min,
                "budget_max": project.budget_max,
                "currency": project.currency,
                "deadline_days": project.deadline_days,
            }
        )

    latest_projects = (
        db.query(Project)
        .filter(Project.status == "open")
        .order_by(Project.id.desc())
        .limit(latest_projects_limit)
        .all()
    )

    latest_projects_items = []
    for project in latest_projects:
        latest_projects_items.append(
            {
                "id": project.id,
                "title": project.title,
                "country": project.country,
                "city": project.city,
                "project_type": project.project_type,
                "budget_min": project.budget_min,
                "budget_max": project.budget_max,
                "currency": project.currency,
                "deadline_days": project.deadline_days,
            }
        )

    personalization = {}

    if current_user.role == "Provider":
        saved_ids = (
            db.query(SavedProject.project_id)
            .join(Project, Project.id == SavedProject.project_id)
            .filter(
                SavedProject.provider_id == current_user.id,
                Project.status == "open",
            )
            .all()
        )

        applied_ids = (
            db.query(Application.project_id)
            .filter(Application.applicant_user_id == current_user.id)
            .all()
        )

        recommended_projects = (
            db.query(Project)
            .filter(Project.status == "open")
            .order_by(Project.id.desc())
            .limit(5)
            .all()
        )

        personalization = {
            "recommended_projects": [
                {
                    "id": p.id,
                    "title": p.title,
                    "country": p.country,
                    "city": p.city,
                    "project_type": p.project_type,
                    "budget_min": p.budget_min,
                    "budget_max": p.budget_max,
                    "currency": p.currency,
                }
                for p in recommended_projects
            ],
            "saved_project_ids": [p[0] for p in saved_ids],
            "applied_project_ids": [p[0] for p in applied_ids],
        }

    if current_user.role == "Customer":
        my_projects = (
            db.query(Project)
            .filter(Project.owner_id == current_user.id)
            .order_by(Project.id.desc())
            .limit(5)
            .all()
        )

        recommended_providers = (
            db.query(User, ProviderProfile)
            .join(ProviderProfile, ProviderProfile.user_id == User.id)
            .filter(User.role == "Provider")
            .limit(5)
            .all()
        )

        personalization = {
            "my_recent_projects": [
                {
                    "id": p.id,
                    "title": p.title,
                    "status": p.status,
                }
                for p in my_projects
            ],
            "recommended_providers": [
                {
                    "id": u.id,
                    "full_name": u.full_name,
                    "skills": prof.skills,
                    "country": prof.country,
                    "availability": prof.availability,
                }
                for u, prof in recommended_providers
            ],
        }

    return {
        "featured_providers": featured_providers,
        "featured_projects": featured_projects_items,
        "latest_projects": latest_projects_items,
        "personalization": personalization,
    }