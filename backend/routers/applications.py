from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.core.dependencies import get_current_user
from backend.core.roles import ROLE_CUSTOMER, ROLE_PROVIDER
from backend.database.session import get_db
from backend.models.application import Application
from backend.models.notification import Notification
from backend.models.project import Project
from backend.models.provider_profile import ProviderProfile
from backend.models.review import Review
from backend.models.user import User
from backend.schemas.application import (
    ApplicationCreate,
    ApplicationResponse,
    ApplicationStatusUpdate,
)
from backend.services.project_event_logger import log_project_event

router = APIRouter(prefix="/applications", tags=["applications"])

ALLOWED_APPLICATION_STATUSES = {"shortlisted", "accepted", "rejected"}


@router.post("", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
def create_application(
    payload: ApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = db.query(Project).filter(Project.id == payload.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.status != "open":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You can apply only to open projects",
        )

    if current_user.role != ROLE_PROVIDER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Provider can apply",
        )

    existing_application = (
        db.query(Application)
        .filter(
            Application.project_id == payload.project_id,
            Application.applicant_user_id == current_user.id,
        )
        .first()
    )

    if existing_application:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already applied to this project",
        )

    application = Application(
        project_id=payload.project_id,
        applicant_user_id=current_user.id,
        application_type=current_user.role,
        cover_letter=payload.cover_letter,
        proposed_budget=payload.proposed_budget,
        estimated_timeline_days=payload.estimated_timeline_days,
        status="submitted",
    )

    db.add(application)
    db.flush()

    log_project_event(
        db=db,
        project_id=project.id,
        event_type="application_submitted",
        title="Application submitted",
        description=f"{current_user.full_name} applied to the project",
        actor_user_id=current_user.id,
        entity_type="application",
        entity_id=application.id,
        metadata={
            "application_status": application.status,
            "proposed_budget": application.proposed_budget,
            "estimated_timeline_days": application.estimated_timeline_days,
            "application_type": application.application_type,
        },
    )

    customer_notification = Notification(
        user_id=project.owner_id,
        type="new_application",
        title="New application received",
        message=f"{current_user.full_name} applied to your project '{project.title}'",
        related_project_id=project.id,
        related_application_id=application.id,
    )

    db.add(customer_notification)
    db.commit()
    db.refresh(application)

    return application


@router.put("/{application_id}/status", response_model=ApplicationResponse)
def update_application_status(
    application_id: int,
    payload: ApplicationStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )

    project = db.query(Project).filter(Project.id == application.project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if current_user.role != ROLE_CUSTOMER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Customer can update application status",
        )

    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can update applications only for your own projects",
        )

    if payload.status not in ALLOWED_APPLICATION_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid application status",
        )

    if payload.status == "accepted":
        if (
            project.selected_application_id is not None
            and project.selected_application_id != application.id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project already has an accepted application",
            )

    previous_status = application.status
    project_status_before = project.status

    application.status = payload.status

    if payload.status == "accepted":
        project.selected_applicant_user_id = application.applicant_user_id
        project.selected_application_id = application.id
        project.status = "in_progress"

    if payload.status != previous_status:
        log_project_event(
            db=db,
            project_id=project.id,
            event_type=f"application_{payload.status}",
            title=f"Application {payload.status}",
            description=f"Application status changed from '{previous_status}' to '{payload.status}'",
            actor_user_id=current_user.id,
            entity_type="application",
            entity_id=application.id,
            metadata={
                "old_status": previous_status,
                "new_status": payload.status,
                "applicant_user_id": application.applicant_user_id,
            },
        )

    if payload.status == "accepted":
        log_project_event(
            db=db,
            project_id=project.id,
            event_type="provider_selected",
            title="Provider selected",
            description="Customer selected a provider and started the project",
            actor_user_id=current_user.id,
            entity_type="project",
            entity_id=project.id,
            metadata={
                "selected_provider_id": application.applicant_user_id,
                "selected_application_id": application.id,
                "old_project_status": project_status_before,
                "new_project_status": project.status,
            },
        )

    provider_notification = Notification(
        user_id=application.applicant_user_id,
        type="application_status_updated",
        title="Application status updated",
        message=f"Your application for project '{project.title}' was marked as '{payload.status}'",
        related_project_id=project.id,
        related_application_id=application.id,
    )

    db.add(provider_notification)
    db.commit()
    db.refresh(application)

    return application


@router.get("/my")
def get_my_applications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != ROLE_PROVIDER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Provider can view own applications",
        )

    rows = (
        db.query(Application, Project)
        .join(Project, Project.id == Application.project_id)
        .filter(Application.applicant_user_id == current_user.id)
        .order_by(Application.id.desc())
        .all()
    )

    items = []
    for application, project in rows:
        items.append(
            {
                "application": {
                    "id": application.id,
                    "project_id": application.project_id,
                    "applicant_user_id": application.applicant_user_id,
                    "application_type": application.application_type,
                    "cover_letter": application.cover_letter,
                    "proposed_budget": application.proposed_budget,
                    "estimated_timeline_days": application.estimated_timeline_days,
                    "status": application.status,
                    "created_at": getattr(application, "created_at", None),
                },
                "project": {
                    "id": project.id,
                    "title": project.title,
                    "country": project.country,
                    "project_type": project.project_type,
                    "budget_min": project.budget_min,
                    "budget_max": project.budget_max,
                    "status": project.status,
                    "owner_id": project.owner_id,
                },
            }
        )

    return {
        "total": len(items),
        "items": items,
    }


@router.get("/projects/{project_id}")
def get_project_applications(
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

    if current_user.role != ROLE_CUSTOMER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Customer can view project applications",
        )

    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can view applications only for your own projects",
        )

    applications = (
        db.query(Application)
        .filter(Application.project_id == project.id)
        .order_by(Application.id.desc())
        .all()
    )

    return {
        "project_id": project.id,
        "total": len(applications),
        "items": applications,
    }


@router.get("/projects/{project_id}/detailed")
def get_project_applications_detailed(
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

    if current_user.role != ROLE_CUSTOMER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Customer can view detailed project applications",
        )

    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can view applications only for your own projects",
        )

    rows = (
        db.query(Application, User, ProviderProfile)
        .join(User, User.id == Application.applicant_user_id)
        .outerjoin(ProviderProfile, ProviderProfile.user_id == User.id)
        .filter(Application.project_id == project.id)
        .order_by(Application.id.desc())
        .all()
    )

    items = []
    for application, provider_user, provider_profile in rows:
        average_rating = (
            db.query(func.avg(Review.rating))
            .filter(Review.reviewed_user_id == provider_user.id)
            .scalar()
        )

        reviews_count = (
            db.query(Review)
            .filter(Review.reviewed_user_id == provider_user.id)
            .count()
        )

        completed_projects_count = (
            db.query(Project)
            .filter(
                Project.selected_applicant_user_id == provider_user.id,
                Project.status == "completed",
            )
            .count()
        )

        active_projects_count = (
            db.query(Project)
            .filter(
                Project.selected_applicant_user_id == provider_user.id,
                Project.status == "in_progress",
            )
            .count()
        )

        items.append(
            {
                "application": {
                    "id": application.id,
                    "project_id": application.project_id,
                    "applicant_user_id": application.applicant_user_id,
                    "application_type": application.application_type,
                    "cover_letter": application.cover_letter,
                    "proposed_budget": application.proposed_budget,
                    "estimated_timeline_days": application.estimated_timeline_days,
                    "status": application.status,
                    "created_at": getattr(application, "created_at", None),
                },
                "provider": {
                    "id": provider_user.id,
                    "full_name": provider_user.full_name,
                    "email": provider_user.email,
                    "role": provider_user.role,
                },
                "provider_profile": {
                    "bio": provider_profile.bio if provider_profile else None,
                    "skills": provider_profile.skills if provider_profile else None,
                    "country": provider_profile.country if provider_profile else None,
                    "availability": provider_profile.availability if provider_profile else None,
                },
                "provider_stats": {
                    "average_rating": round(float(average_rating), 2) if average_rating is not None else None,
                    "reviews_count": reviews_count,
                    "completed_projects_count": completed_projects_count,
                    "active_projects_count": active_projects_count,
                },
            }
        )

    return {
        "project_id": project.id,
        "total": len(items),
        "items": items,
    }