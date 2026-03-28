import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.core.dependencies import get_current_customer, get_current_provider, get_current_user
from backend.database.session import get_db
from backend.models.project import Project
from backend.models.project_completion_request import ProjectCompletionRequest
from backend.models.user import User
from backend.schemas.project_completion import (
    CompletionRequestCreate,
    CompletionRequestDecision,
    CompletionRequestResponse,
)
from backend.services.project_event_logger import log_project_event

logger = logging.getLogger("app")

router = APIRouter(
    prefix="/projects",
    tags=["Project Completion"],
)


def get_project_or_404(project_id: int, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return project


def get_latest_completion_request_or_404(
    project_id: int,
    db: Session,
) -> ProjectCompletionRequest:
    completion_request = (
        db.query(ProjectCompletionRequest)
        .filter(ProjectCompletionRequest.project_id == project_id)
        .order_by(ProjectCompletionRequest.created_at.desc(), ProjectCompletionRequest.id.desc())
        .first()
    )

    if not completion_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Completion request not found",
        )

    return completion_request


def ensure_project_customer(project: Project, current_user: User) -> None:
    if current_user.id != project.owner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only project owner can perform this action",
        )


def ensure_selected_provider(project: Project, current_user: User) -> None:
    if not project.selected_applicant_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project does not have a selected provider",
        )

    if current_user.id != project.selected_applicant_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only selected provider can perform this action",
        )


def ensure_project_participant(project: Project, current_user: User) -> None:
    is_customer = current_user.id == project.owner_id
    is_selected_provider = current_user.id == project.selected_applicant_user_id

    if not (is_customer or is_selected_provider):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this completion request",
        )


def ensure_completion_request_matches_project(
    project: Project,
    completion_request: ProjectCompletionRequest,
) -> None:
    if completion_request.project_id != project.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Completion request does not belong to this project",
        )

    if completion_request.customer_id != project.owner_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Completion request customer does not match project owner",
        )

    if project.selected_applicant_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project does not have a selected provider",
        )

    if completion_request.provider_id != project.selected_applicant_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Completion request provider does not match selected provider",
        )


def clean_optional_message(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


@router.post(
    "/{project_id}/completion-request",
    response_model=CompletionRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_completion_request(
    project_id: int,
    payload: CompletionRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_provider),
):
    try:
        project = get_project_or_404(project_id, db)

        if project.status != "in_progress":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Completion request can only be created for in_progress projects",
            )

        ensure_selected_provider(project, current_user)

        existing_pending_request = (
            db.query(ProjectCompletionRequest)
            .filter(
                ProjectCompletionRequest.project_id == project_id,
                ProjectCompletionRequest.status == "pending",
            )
            .first()
        )

        if existing_pending_request:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pending completion request already exists for this project",
            )

        provider_message = clean_optional_message(payload.provider_message)

        completion_request = ProjectCompletionRequest(
            project_id=project.id,
            provider_id=current_user.id,
            customer_id=project.owner_id,
            status="pending",
            provider_message=provider_message,
        )

        db.add(completion_request)
        db.flush()

        log_project_event(
            db=db,
            project_id=project.id,
            event_type="completion_requested",
            title="Project completion requested",
            description=provider_message or "Provider requested project completion",
            actor_user_id=current_user.id,
            entity_type="completion_request",
            entity_id=completion_request.id,
            metadata={
                "status": completion_request.status,
            },
        )

        db.commit()
        db.refresh(completion_request)

        return completion_request

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception(
            "Unhandled error while creating completion request. project_id=%s user_id=%s",
            project_id,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create completion request",
        )


@router.get(
    "/{project_id}/completion-request",
    response_model=CompletionRequestResponse,
)
def get_completion_request(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_project_or_404(project_id, db)
    completion_request = get_latest_completion_request_or_404(project_id, db)

    ensure_project_participant(project, current_user)
    ensure_completion_request_matches_project(project, completion_request)

    return completion_request


@router.post(
    "/{project_id}/completion-request/approve",
    response_model=CompletionRequestResponse,
)
def approve_completion_request(
    project_id: int,
    payload: CompletionRequestDecision,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer),
):
    try:
        project = get_project_or_404(project_id, db)
        completion_request = get_latest_completion_request_or_404(project_id, db)

        ensure_project_customer(project, current_user)
        ensure_completion_request_matches_project(project, completion_request)

        if project.status != "in_progress":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project must be in_progress to approve completion request",
            )

        if completion_request.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only pending completion request can be approved",
            )

        customer_message = clean_optional_message(payload.customer_message)

        completion_request.status = "approved"
        completion_request.customer_message = customer_message
        completion_request.resolved_at = datetime.now(timezone.utc)

        project.status = "completed"

        log_project_event(
            db=db,
            project_id=project.id,
            event_type="completion_approved",
            title="Project completion approved",
            description=customer_message or "Customer approved project completion",
            actor_user_id=current_user.id,
            entity_type="completion_request",
            entity_id=completion_request.id,
            metadata={
                "status": completion_request.status,
                "project_status": project.status,
            },
        )

        db.commit()
        db.refresh(completion_request)
        db.refresh(project)

        return completion_request

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception(
            "Unhandled error while approving completion request. project_id=%s user_id=%s",
            project_id,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to approve completion request",
        )


@router.post(
    "/{project_id}/completion-request/reopen",
    response_model=CompletionRequestResponse,
)
def reopen_completion_request(
    project_id: int,
    payload: CompletionRequestDecision,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer),
):
    try:
        project = get_project_or_404(project_id, db)
        completion_request = get_latest_completion_request_or_404(project_id, db)

        ensure_project_customer(project, current_user)
        ensure_completion_request_matches_project(project, completion_request)

        if project.status != "in_progress":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project must be in_progress to reopen completion request",
            )

        if completion_request.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only pending completion request can be reopened",
            )

        customer_message = clean_optional_message(payload.customer_message)

        completion_request.status = "reopened"
        completion_request.customer_message = customer_message
        completion_request.resolved_at = datetime.now(timezone.utc)

        log_project_event(
            db=db,
            project_id=project.id,
            event_type="completion_reopened",
            title="Project reopened",
            description=customer_message or "Customer requested more work before completion",
            actor_user_id=current_user.id,
            entity_type="completion_request",
            entity_id=completion_request.id,
            metadata={
                "status": completion_request.status,
                "project_status": project.status,
            },
        )

        db.commit()
        db.refresh(completion_request)

        return completion_request

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception(
            "Unhandled error while reopening completion request. project_id=%s user_id=%s",
            project_id,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reopen completion request",
        )