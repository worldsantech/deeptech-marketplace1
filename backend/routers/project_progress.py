from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.core.dependencies import get_current_user
from backend.database.session import get_db
from backend.models.attachment import Attachment
from backend.models.milestone import Milestone
from backend.models.project import Project
from backend.models.project_completion_request import ProjectCompletionRequest
from backend.models.user import User
from backend.schemas.project_progress import (
    ProjectProgressMilestoneItem,
    ProjectProgressSummaryResponse,
)

router = APIRouter(
    prefix="/projects",
    tags=["Project Progress"],
)


def get_project_or_404(project_id: int, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return project


def ensure_project_access(project: Project, current_user: User):
    allowed_user_ids = [project.owner_id, project.selected_applicant_user_id]
    if current_user.id not in allowed_user_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this project progress",
        )


def get_latest_completion_request(
    project_id: int,
    db: Session,
) -> ProjectCompletionRequest | None:
    return (
        db.query(ProjectCompletionRequest)
        .filter(ProjectCompletionRequest.project_id == project_id)
        .order_by(ProjectCompletionRequest.created_at.desc())
        .first()
    )


def get_attachment_count_for_milestone(milestone_id: int, db: Session) -> int:
    return (
        db.query(Attachment)
        .filter(Attachment.milestone_id == milestone_id)
        .count()
    )


@router.get(
    "/{project_id}/progress-summary",
    response_model=ProjectProgressSummaryResponse,
)
def get_project_progress_summary(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_project_or_404(project_id, db)
    ensure_project_access(project, current_user)

    milestones: List[Milestone] = (
        db.query(Milestone)
        .filter(Milestone.project_id == project_id)
        .order_by(Milestone.created_at.asc(), Milestone.id.asc())
        .all()
    )

    total_milestones = len(milestones)
    pending_milestones = sum(1 for m in milestones if m.status == "pending")
    submitted_milestones = sum(1 for m in milestones if m.status == "submitted")
    approved_milestones = sum(1 for m in milestones if m.status == "approved")
    changes_requested_milestones = sum(
        1 for m in milestones if m.status == "changes_requested"
    )

    total_amount = float(
        sum(float(m.amount) for m in milestones if m.amount is not None)
    )
    approved_amount = float(
        sum(float(m.amount) for m in milestones if m.amount is not None and m.status == "approved")
    )
    remaining_amount = float(max(total_amount - approved_amount, 0.0))

    completion_percentage = 0.0
    if total_milestones > 0:
        completion_percentage = round((approved_milestones / total_milestones) * 100, 2)

    completed_milestones_count = approved_milestones
    open_milestones_count = total_milestones - approved_milestones

    latest_completion_request = get_latest_completion_request(project_id, db)
    has_pending_completion_request = (
        latest_completion_request is not None
        and latest_completion_request.status == "pending"
    )
    completion_request_status = (
        latest_completion_request.status if latest_completion_request else None
    )

    milestone_items: List[ProjectProgressMilestoneItem] = []
    last_milestone_activity_at = None

    for milestone in milestones:
        attachments_count = get_attachment_count_for_milestone(milestone.id, db)

        candidate_dates = [
            milestone.updated_at,
            milestone.submitted_at,
            milestone.approved_at,
            milestone.created_at,
        ]
        candidate_dates = [dt for dt in candidate_dates if dt is not None]

        if candidate_dates:
            milestone_last_activity = max(candidate_dates)
            if (
                last_milestone_activity_at is None
                or milestone_last_activity > last_milestone_activity_at
            ):
                last_milestone_activity_at = milestone_last_activity

        milestone_items.append(
            ProjectProgressMilestoneItem(
                id=milestone.id,
                title=milestone.title,
                status=milestone.status,
                amount=float(milestone.amount) if milestone.amount is not None else None,
                due_date=milestone.due_date,
                submitted_at=milestone.submitted_at,
                approved_at=milestone.approved_at,
                attachments_count=attachments_count,
            )
        )

    return ProjectProgressSummaryResponse(
        project_id=project.id,
        project_status=project.status,
        total_milestones=total_milestones,
        pending_milestones=pending_milestones,
        submitted_milestones=submitted_milestones,
        approved_milestones=approved_milestones,
        changes_requested_milestones=changes_requested_milestones,
        total_amount=round(total_amount, 2),
        approved_amount=round(approved_amount, 2),
        remaining_amount=round(remaining_amount, 2),
        completion_percentage=completion_percentage,
        has_pending_completion_request=has_pending_completion_request,
        completion_request_status=completion_request_status,
        completed_milestones_count=completed_milestones_count,
        open_milestones_count=open_milestones_count,
        last_milestone_activity_at=last_milestone_activity_at,
        milestones=milestone_items,
    )