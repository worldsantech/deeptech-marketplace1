from fastapi import APIRouter, Depends, HTTPException, status
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

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("/{project_id}/detail")
def get_project_detail(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    is_owner = current_user.role == "Customer" and project.owner_id == current_user.id

    is_saved = False
    has_applied = False
    my_application_status = None
    can_apply = False

    if current_user.role == "Provider":
        saved = (
            db.query(SavedProject)
            .filter(
                SavedProject.provider_id == current_user.id,
                SavedProject.project_id == project.id,
            )
            .first()
        )
        is_saved = saved is not None

        application = (
            db.query(Application)
            .filter(
                Application.project_id == project.id,
                Application.applicant_user_id == current_user.id,
            )
            .first()
        )
        has_applied = application is not None
        my_application_status = application.status if application else None

        can_apply = project.status == "open" and not has_applied

    applications_count = (
        db.query(Application)
        .filter(Application.project_id == project.id)
        .count()
    )

    selected_provider = None
    if project.selected_applicant_user_id:
        selected_user = (
            db.query(User)
            .filter(User.id == project.selected_applicant_user_id)
            .first()
        )

        selected_profile = (
            db.query(ProviderProfile)
            .filter(ProviderProfile.user_id == project.selected_applicant_user_id)
            .first()
        )

        average_rating = (
            db.query(func.avg(Review.rating))
            .filter(Review.reviewed_user_id == project.selected_applicant_user_id)
            .scalar()
        )

        reviews_count = (
            db.query(Review)
            .filter(Review.reviewed_user_id == project.selected_applicant_user_id)
            .count()
        )

        completed_projects_count = (
            db.query(Project)
            .filter(
                Project.selected_applicant_user_id == project.selected_applicant_user_id,
                Project.status == "completed",
            )
            .count()
        )

        active_projects_count = (
            db.query(Project)
            .filter(
                Project.selected_applicant_user_id == project.selected_applicant_user_id,
                Project.status == "in_progress",
            )
            .count()
        )

        if selected_user:
            selected_provider = {
                "user": {
                    "id": selected_user.id,
                    "email": selected_user.email,
                    "full_name": selected_user.full_name,
                    "role": selected_user.role,
                },
                "profile": {
                    "bio": selected_profile.bio if selected_profile else None,
                    "skills": selected_profile.skills if selected_profile else None,
                    "country": selected_profile.country if selected_profile else None,
                    "availability": selected_profile.availability if selected_profile else None,
                },
                "stats": {
                    "average_rating": round(float(average_rating), 2) if average_rating is not None else None,
                    "reviews_count": reviews_count,
                    "completed_projects_count": completed_projects_count,
                    "active_projects_count": active_projects_count,
                },
            }

    return {
        "project": {
            "id": project.id,
            "title": project.title,
            "description": project.description,
            "country": project.country,
            "project_type": project.project_type,
            "budget_min": project.budget_min,
            "budget_max": project.budget_max,
            "status": project.status,
            "owner_id": project.owner_id,
            "selected_application_id": project.selected_application_id,
            "selected_applicant_user_id": project.selected_applicant_user_id,
        },
        "viewer": {
            "id": current_user.id,
            "role": current_user.role,
            "is_owner": is_owner,
            "is_saved": is_saved,
            "has_applied": has_applied,
            "my_application_status": my_application_status,
            "can_apply": can_apply,
        },
        "stats": {
            "applications_count": applications_count,
        },
        "selected_provider": selected_provider,
    }