from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.core.dependencies import get_current_user
from backend.database.session import get_db
from backend.models.application import Application
from backend.models.project import Project
from backend.models.saved_project import SavedProject
from backend.models.user import User

router = APIRouter(prefix="/dashboard/provider", tags=["Provider Dashboard"])


@router.get("/summary")
def get_provider_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "Provider":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only providers can access provider dashboard",
        )

    saved_projects_count = (
        db.query(SavedProject)
        .filter(SavedProject.provider_id == current_user.id)
        .count()
    )

    applications_base = (
        db.query(Application)
        .filter(Application.applicant_user_id == current_user.id)
    )

    applications_total = applications_base.count()
    applications_submitted = applications_base.filter(Application.status == "submitted").count()
    applications_shortlisted = applications_base.filter(Application.status == "shortlisted").count()
    applications_accepted = applications_base.filter(Application.status == "accepted").count()
    applications_rejected = applications_base.filter(Application.status == "rejected").count()

    active_jobs_count = (
        db.query(Application)
        .join(Project, Project.id == Application.project_id)
        .filter(
            Application.applicant_user_id == current_user.id,
            Application.status == "accepted",
            Project.status == "in_progress",
        )
        .count()
    )

    recent_saved_rows = (
        db.query(SavedProject, Project)
        .join(Project, Project.id == SavedProject.project_id)
        .filter(SavedProject.provider_id == current_user.id)
        .order_by(SavedProject.id.desc())
        .limit(5)
        .all()
    )

    recent_saved_projects = []
    for saved, project in recent_saved_rows:
        recent_saved_projects.append(
            {
                "saved_project_id": saved.id,
                "saved_at": saved.created_at,
                "project": {
                    "id": project.id,
                    "title": project.title,
                    "country": project.country,
                    "project_type": project.project_type,
                    "budget_min": project.budget_min,
                    "budget_max": project.budget_max,
                    "status": project.status,
                },
            }
        )

    recent_application_rows = (
        db.query(Application, Project)
        .join(Project, Project.id == Application.project_id)
        .filter(Application.applicant_user_id == current_user.id)
        .order_by(Application.id.desc())
        .limit(5)
        .all()
    )

    recent_applications = []
    for application, project in recent_application_rows:
        recent_applications.append(
            {
                "application_id": application.id,
                "application_status": application.status,
                "project": {
                    "id": project.id,
                    "title": project.title,
                    "country": project.country,
                    "project_type": project.project_type,
                    "budget_min": project.budget_min,
                    "budget_max": project.budget_max,
                    "status": project.status,
                },
            }
        )

    return {
        "provider_id": current_user.id,
        "summary": {
            "saved_projects_count": saved_projects_count,
            "applications_total": applications_total,
            "applications_submitted": applications_submitted,
            "applications_shortlisted": applications_shortlisted,
            "applications_accepted": applications_accepted,
            "applications_rejected": applications_rejected,
            "active_jobs_count": active_jobs_count,
        },
        "recent_saved_projects": recent_saved_projects,
        "recent_applications": recent_applications,
    }