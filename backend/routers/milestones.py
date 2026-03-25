from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.core.dependencies import get_current_user
from backend.database.session import get_db
from backend.models.attachment import Attachment
from backend.models.milestone import Milestone
from backend.models.project import Project
from backend.models.user import User
from backend.schemas.attachment import AttachmentResponse
from backend.schemas.milestone import (
    MilestoneCreate,
    MilestoneDecision,
    MilestoneResponse,
    MilestoneSubmit,
    MilestoneUpdate,
)
from backend.services.project_event_logger import log_project_event

router = APIRouter(
    prefix="/projects",
    tags=["Milestones"],
)


def get_project_or_404(project_id: int, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return project


def get_milestone_or_404(project_id: int, milestone_id: int, db: Session) -> Milestone:
    milestone = (
        db.query(Milestone)
        .filter(
            Milestone.id == milestone_id,
            Milestone.project_id == project_id,
        )
        .first()
    )
    if not milestone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Milestone not found",
        )
    return milestone


def ensure_project_has_selected_provider(project: Project):
    if not project.selected_applicant_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project does not have selected provider",
        )


def ensure_customer_access(project: Project, current_user: User):
    if current_user.id != project.owner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only project owner can perform this action",
        )


def ensure_provider_access(project: Project, current_user: User):
    if current_user.id != project.selected_applicant_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only selected provider can perform this action",
        )


def ensure_project_participant(project: Project, current_user: User):
    allowed_user_ids = [project.owner_id, project.selected_applicant_user_id]
    if current_user.id not in allowed_user_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to project milestones",
        )


def get_milestone_attachments(milestone_id: int, db: Session) -> List[Attachment]:
    return (
        db.query(Attachment)
        .filter(Attachment.milestone_id == milestone_id)
        .order_by(Attachment.created_at.asc(), Attachment.id.asc())
        .all()
    )


def build_milestone_response(milestone: Milestone, db: Session) -> MilestoneResponse:
    attachments = get_milestone_attachments(milestone.id, db)

    return MilestoneResponse(
        id=milestone.id,
        project_id=milestone.project_id,
        customer_id=milestone.customer_id,
        provider_id=milestone.provider_id,
        title=milestone.title,
        description=milestone.description,
        amount=float(milestone.amount) if milestone.amount is not None else None,
        due_date=milestone.due_date,
        status=milestone.status,
        provider_note=milestone.provider_note,
        customer_note=milestone.customer_note,
        submitted_at=milestone.submitted_at,
        approved_at=milestone.approved_at,
        created_at=milestone.created_at,
        updated_at=milestone.updated_at,
        attachments=[AttachmentResponse.model_validate(item) for item in attachments],
    )


@router.post(
    "/{project_id}/milestones",
    response_model=MilestoneResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_milestone(
    project_id: int,
    payload: MilestoneCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_project_or_404(project_id, db)
    ensure_customer_access(project, current_user)
    ensure_project_has_selected_provider(project)

    if project.status not in ["in_progress", "open"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Milestones can be created only for open or in_progress projects",
        )

    milestone = Milestone(
        project_id=project.id,
        customer_id=project.owner_id,
        provider_id=project.selected_applicant_user_id,
        title=payload.title.strip(),
        description=payload.description,
        amount=payload.amount,
        due_date=payload.due_date,
        status="pending",
    )

    db.add(milestone)
    db.flush()

    log_project_event(
        db=db,
        project_id=project.id,
        event_type="milestone_created",
        title="Milestone created",
        description=milestone.title,
        actor_user_id=current_user.id,
        entity_type="milestone",
        entity_id=milestone.id,
        metadata={
            "status": milestone.status,
            "amount": float(milestone.amount) if milestone.amount is not None else None,
            "due_date": milestone.due_date.isoformat() if milestone.due_date else None,
        },
    )

    db.commit()
    db.refresh(milestone)

    return build_milestone_response(milestone, db)


@router.get(
    "/{project_id}/milestones",
    response_model=List[MilestoneResponse],
)
def list_project_milestones(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_project_or_404(project_id, db)
    ensure_project_has_selected_provider(project)
    ensure_project_participant(project, current_user)

    milestones = (
        db.query(Milestone)
        .filter(Milestone.project_id == project_id)
        .order_by(Milestone.created_at.asc(), Milestone.id.asc())
        .all()
    )

    return [build_milestone_response(milestone, db) for milestone in milestones]


@router.get(
    "/{project_id}/milestones/{milestone_id}",
    response_model=MilestoneResponse,
)
def get_milestone(
    project_id: int,
    milestone_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_project_or_404(project_id, db)
    ensure_project_has_selected_provider(project)
    ensure_project_participant(project, current_user)

    milestone = get_milestone_or_404(project_id, milestone_id, db)
    return build_milestone_response(milestone, db)


@router.put(
    "/{project_id}/milestones/{milestone_id}",
    response_model=MilestoneResponse,
)
def update_milestone(
    project_id: int,
    milestone_id: int,
    payload: MilestoneUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_project_or_404(project_id, db)
    ensure_customer_access(project, current_user)
    ensure_project_has_selected_provider(project)

    milestone = get_milestone_or_404(project_id, milestone_id, db)

    if milestone.status == "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Approved milestone cannot be edited",
        )

    if payload.title is not None:
        milestone.title = payload.title.strip()

    if payload.description is not None:
        milestone.description = payload.description

    if payload.amount is not None:
        milestone.amount = payload.amount

    if payload.due_date is not None:
        milestone.due_date = payload.due_date

    db.commit()
    db.refresh(milestone)

    return build_milestone_response(milestone, db)


@router.post(
    "/{project_id}/milestones/{milestone_id}/submit",
    response_model=MilestoneResponse,
)
def submit_milestone(
    project_id: int,
    milestone_id: int,
    payload: MilestoneSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_project_or_404(project_id, db)
    ensure_project_has_selected_provider(project)
    ensure_provider_access(project, current_user)

    if project.status != "in_progress":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Milestones can be submitted only when project is in_progress",
        )

    milestone = get_milestone_or_404(project_id, milestone_id, db)

    if milestone.status not in ["pending", "changes_requested"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending or changes_requested milestones can be submitted",
        )

    attachments = []
    if payload.attachment_ids:
        attachments = (
            db.query(Attachment)
            .filter(Attachment.id.in_(payload.attachment_ids))
            .all()
        )

        if len(attachments) != len(set(payload.attachment_ids)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more attachments not found",
            )

        for attachment in attachments:
            if attachment.uploaded_by != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can attach only your own uploaded files",
                )

            if attachment.project_id != project.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Attachment does not belong to this project",
                )

            if attachment.message_id is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Message attachment cannot be reused for milestone",
                )

            if attachment.milestone_id is not None and attachment.milestone_id != milestone.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Attachment is already linked to another milestone",
                )

    milestone.status = "submitted"
    milestone.provider_note = payload.provider_note
    milestone.customer_note = None
    milestone.submitted_at = datetime.utcnow()

    for attachment in attachments:
        attachment.milestone_id = milestone.id

    log_project_event(
        db=db,
        project_id=project.id,
        event_type="milestone_submitted",
        title="Milestone submitted",
        description=milestone.title,
        actor_user_id=current_user.id,
        entity_type="milestone",
        entity_id=milestone.id,
        metadata={
            "attachments_count": len(attachments),
            "provider_note_present": bool(payload.provider_note),
        },
    )

    db.commit()
    db.refresh(milestone)

    return build_milestone_response(milestone, db)


@router.post(
    "/{project_id}/milestones/{milestone_id}/approve",
    response_model=MilestoneResponse,
)
def approve_milestone(
    project_id: int,
    milestone_id: int,
    payload: MilestoneDecision,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_project_or_404(project_id, db)
    ensure_customer_access(project, current_user)
    ensure_project_has_selected_provider(project)

    milestone = get_milestone_or_404(project_id, milestone_id, db)

    if milestone.status != "submitted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only submitted milestones can be approved",
        )

    milestone.status = "approved"
    milestone.customer_note = payload.customer_note
    milestone.approved_at = datetime.utcnow()

    log_project_event(
        db=db,
        project_id=project.id,
        event_type="milestone_approved",
        title="Milestone approved",
        description=milestone.title,
        actor_user_id=current_user.id,
        entity_type="milestone",
        entity_id=milestone.id,
        metadata={
            "amount": float(milestone.amount) if milestone.amount is not None else None,
            "customer_note_present": bool(payload.customer_note),
        },
    )

    db.commit()
    db.refresh(milestone)

    return build_milestone_response(milestone, db)


@router.post(
    "/{project_id}/milestones/{milestone_id}/request-changes",
    response_model=MilestoneResponse,
)
def request_changes_for_milestone(
    project_id: int,
    milestone_id: int,
    payload: MilestoneDecision,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_project_or_404(project_id, db)
    ensure_customer_access(project, current_user)
    ensure_project_has_selected_provider(project)

    milestone = get_milestone_or_404(project_id, milestone_id, db)

    if milestone.status != "submitted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only submitted milestones can be sent back for changes",
        )

    milestone.status = "changes_requested"
    milestone.customer_note = payload.customer_note
    milestone.approved_at = None

    log_project_event(
        db=db,
        project_id=project.id,
        event_type="milestone_changes_requested",
        title="Changes requested",
        description=milestone.title,
        actor_user_id=current_user.id,
        entity_type="milestone",
        entity_id=milestone.id,
        metadata={
            "customer_note_present": bool(payload.customer_note),
        },
    )

    db.commit()
    db.refresh(milestone)

    return build_milestone_response(milestone, db)


@router.delete(
    "/{project_id}/milestones/{milestone_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_milestone(
    project_id: int,
    milestone_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_project_or_404(project_id, db)
    ensure_customer_access(project, current_user)
    ensure_project_has_selected_provider(project)

    milestone = get_milestone_or_404(project_id, milestone_id, db)

    if milestone.status in ["submitted", "approved"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Submitted or approved milestone cannot be deleted",
        )

    attachments = (
        db.query(Attachment)
        .filter(Attachment.milestone_id == milestone.id)
        .all()
    )

    for attachment in attachments:
        attachment.milestone_id = None

    log_project_event(
        db=db,
        project_id=project.id,
        event_type="milestone_deleted",
        title="Milestone deleted",
        description=milestone.title,
        actor_user_id=current_user.id,
        entity_type="milestone",
        entity_id=milestone.id,
        metadata={},
    )

    db.delete(milestone)
    db.commit()

    return None