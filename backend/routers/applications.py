import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.core.dependencies import get_current_customer, get_current_provider
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
    ApplicationStatusUpdateResponse,
)
from backend.services.project_event_logger import log_project_event

logger = logging.getLogger("app")

router = APIRouter(prefix="/applications", tags=["Applications"])

ALLOWED_APPLICATION_STATUSES = {"shortlisted", "accepted", "rejected"}
ACTIVE_APPLICATION_STATUSES = {"submitted", "shortlisted"}

VALID_STATUS_TRANSITIONS = {
    "submitted": {"shortlisted", "accepted", "rejected"},
    "shortlisted": {"accepted", "rejected"},
    "accepted": set(),
    "rejected": set(),
}


def get_project_or_404(db: Session, project_id: int) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return project


def get_application_or_404(db: Session, application_id: int) -> Application:
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )
    return application


def ensure_project_owner(project: Project, current_user: User) -> None:
    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can access applications only for your own projects",
        )


def normalize_application_status(value: str) -> str:
    clean_status = value.strip().lower()
    if clean_status not in ALLOWED_APPLICATION_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid application status. Allowed: {sorted(ALLOWED_APPLICATION_STATUSES)}",
        )
    return clean_status


@router.post("", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
def create_application(
    payload: ApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_provider),
):
    try:
        project = get_project_or_404(db, payload.project_id)

        if project.owner_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot apply to your own project",
            )

        if project.status != "open":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You can apply only to open projects",
            )

        if project.selected_application_id is not None or project.selected_applicant_user_id is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This project already has a selected provider",
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

        clean_cover_letter = payload.cover_letter.strip()
        if not clean_cover_letter:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="cover_letter cannot be empty",
            )

        application = Application(
            project_id=payload.project_id,
            applicant_user_id=current_user.id,
            application_type=current_user.role,
            cover_letter=clean_cover_letter,
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

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception(
            "Unhandled error while creating application. project_id=%s user_id=%s",
            payload.project_id,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create application",
        )


@router.put(
    "/{application_id}/status",
    response_model=ApplicationStatusUpdateResponse,
)
def update_application_status(
    application_id: int,
    payload: ApplicationStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer),
):
    try:
        application = get_application_or_404(db, application_id)
        project = get_project_or_404(db, application.project_id)

        ensure_project_owner(project, current_user)

        new_status = normalize_application_status(payload.status)

        if project.status in {"completed", "cancelled"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot update applications for completed or cancelled projects",
            )

        previous_status = application.status

        if previous_status == new_status:
            return {
                "application": application,
                "project": project,
                "auto_rejected_applications": [],
            }

        allowed_next_statuses = VALID_STATUS_TRANSITIONS.get(previous_status, set())
        if new_status not in allowed_next_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot change application status from '{previous_status}' to '{new_status}'",
            )

        if new_status == "accepted":
            if (
                project.selected_application_id is not None
                and project.selected_application_id != application.id
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Project already has an accepted application",
                )

            if project.status != "open":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Only open projects can accept applications",
                )

        project_status_before = project.status
        application.status = new_status

        if new_status == "accepted":
            project.selected_applicant_user_id = application.applicant_user_id
            project.selected_application_id = application.id
            project.status = "in_progress"

        log_project_event(
            db=db,
            project_id=project.id,
            event_type=f"application_{new_status}",
            title=f"Application {new_status}",
            description=f"Application status changed from '{previous_status}' to '{new_status}'",
            actor_user_id=current_user.id,
            entity_type="application",
            entity_id=application.id,
            metadata={
                "old_status": previous_status,
                "new_status": new_status,
                "applicant_user_id": application.applicant_user_id,
            },
        )

        provider_notification = Notification(
            user_id=application.applicant_user_id,
            type="application_status_updated",
            title="Application status updated",
            message=f"Your application for project '{project.title}' was marked as '{new_status}'",
            related_project_id=project.id,
            related_application_id=application.id,
        )
        db.add(provider_notification)

        auto_rejected_applications = []

        if new_status == "accepted":
            other_applications = (
                db.query(Application)
                .filter(
                    Application.project_id == project.id,
                    Application.id != application.id,
                    Application.status.in_(ACTIVE_APPLICATION_STATUSES),
                )
                .all()
            )

            for other_application in other_applications:
                old_other_status = other_application.status
                other_application.status = "rejected"
                auto_rejected_applications.append(other_application)

                log_project_event(
                    db=db,
                    project_id=project.id,
                    event_type="application_rejected",
                    title="Application rejected",
                    description="Application was automatically rejected because another provider was selected",
                    actor_user_id=current_user.id,
                    entity_type="application",
                    entity_id=other_application.id,
                    metadata={
                        "old_status": old_other_status,
                        "new_status": "rejected",
                        "applicant_user_id": other_application.applicant_user_id,
                        "reason": "another_provider_selected",
                    },
                )

                other_provider_notification = Notification(
                    user_id=other_application.applicant_user_id,
                    type="application_status_updated",
                    title="Application status updated",
                    message=f"Your application for project '{project.title}' was marked as 'rejected'",
                    related_project_id=project.id,
                    related_application_id=other_application.id,
                )
                db.add(other_provider_notification)

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

        db.commit()
        db.refresh(application)
        db.refresh(project)

        refreshed_auto_rejected = []
        for rejected_application in auto_rejected_applications:
            db.refresh(rejected_application)
            refreshed_auto_rejected.append(rejected_application)

        return {
            "application": application,
            "project": project,
            "auto_rejected_applications": refreshed_auto_rejected,
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception(
            "Unhandled error while updating application status. application_id=%s user_id=%s",
            application_id,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update application status",
        )


@router.get("/my")
def get_my_applications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_provider),
):
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
                    "city": getattr(project, "city", None),
                    "project_type": project.project_type,
                    "budget_min": project.budget_min,
                    "budget_max": project.budget_max,
                    "currency": getattr(project, "currency", None),
                    "deadline_days": getattr(project, "deadline_days", None),
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
    current_user: User = Depends(get_current_customer),
):
    project = get_project_or_404(db, project_id)
    ensure_project_owner(project, current_user)

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
    current_user: User = Depends(get_current_customer),
):
    project = get_project_or_404(db, project_id)
    ensure_project_owner(project, current_user)

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