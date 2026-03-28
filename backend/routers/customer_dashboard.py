from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.core.dependencies import get_current_customer
from backend.database.session import get_db
from backend.models.application import Application
from backend.models.project import Project
from backend.models.user import User

router = APIRouter(prefix="/dashboard/customer", tags=["Customer Dashboard"])


@router.get("/summary")
def get_customer_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer),
):
    projects_base = (
        db.query(Project)
        .filter(Project.owner_id == current_user.id)
    )

    projects_total = projects_base.count()
    projects_open = projects_base.filter(Project.status == "open").count()
    projects_in_progress = projects_base.filter(Project.status == "in_progress").count()
    projects_completed = projects_base.filter(Project.status == "completed").count()
    projects_cancelled = projects_base.filter(Project.status == "cancelled").count()

    applications_received_base = (
        db.query(Application)
        .join(Project, Project.id == Application.project_id)
        .filter(Project.owner_id == current_user.id)
    )

    applications_received_total = applications_received_base.count()
    applications_submitted = applications_received_base.filter(Application.status == "submitted").count()
    applications_shortlisted = applications_received_base.filter(Application.status == "shortlisted").count()
    applications_accepted = applications_received_base.filter(Application.status == "accepted").count()
    applications_rejected = applications_received_base.filter(Application.status == "rejected").count()

    recent_projects_rows = (
        db.query(Project)
        .filter(Project.owner_id == current_user.id)
        .order_by(Project.id.desc())
        .limit(5)
        .all()
    )

    recent_projects = []
    for project in recent_projects_rows:
        applications_count = (
            db.query(Application)
            .filter(Application.project_id == project.id)
            .count()
        )

        recent_projects.append(
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
                "status": project.status,
                "applications_count": applications_count,
                "selected_application_id": project.selected_application_id,
                "selected_applicant_user_id": project.selected_applicant_user_id,
            }
        )

    recent_applications_rows = (
        db.query(Application, Project, User)
        .join(Project, Project.id == Application.project_id)
        .join(User, User.id == Application.applicant_user_id)
        .filter(Project.owner_id == current_user.id)
        .order_by(Application.id.desc())
        .limit(5)
        .all()
    )

    recent_applications = []
    for application, project, provider in recent_applications_rows:
        recent_applications.append(
            {
                "application_id": application.id,
                "application_status": application.status,
                "created_at": application.created_at,
                "project": {
                    "id": project.id,
                    "title": project.title,
                    "status": project.status,
                },
                "provider": {
                    "id": provider.id,
                    "full_name": provider.full_name,
                    "email": provider.email,
                    "role": provider.role,
                },
            }
        )

    return {
        "customer_id": current_user.id,
        "summary": {
            "projects_total": projects_total,
            "projects_open": projects_open,
            "projects_in_progress": projects_in_progress,
            "projects_completed": projects_completed,
            "projects_cancelled": projects_cancelled,
            "applications_received_total": applications_received_total,
            "applications_submitted": applications_submitted,
            "applications_shortlisted": applications_shortlisted,
            "applications_accepted": applications_accepted,
            "applications_rejected": applications_rejected,
        },
        "recent_projects": recent_projects,
        "recent_applications": recent_applications,
    }