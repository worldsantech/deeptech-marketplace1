from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.core.dependencies import get_current_user
from backend.database.session import get_db
from backend.models.project import Project
from backend.models.project_event import ProjectEvent
from backend.models.user import User
from backend.schemas.project_activity import (
    ProjectActivityFeedResponse,
    ProjectActivityItem,
)

router = APIRouter(
    prefix="/projects",
    tags=["Project Activity"],
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
            detail="You do not have access to this project activity",
        )


@router.get(
    "/{project_id}/activity-feed",
    response_model=ProjectActivityFeedResponse,
)
def get_project_activity_feed(
    project_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_project_or_404(project_id, db)
    ensure_project_access(project, current_user)

    events: List[ProjectEvent] = (
        db.query(ProjectEvent)
        .filter(ProjectEvent.project_id == project_id)
        .order_by(ProjectEvent.created_at.desc(), ProjectEvent.id.desc())
        .limit(limit)
        .all()
    )

    total_events = (
        db.query(ProjectEvent)
        .filter(ProjectEvent.project_id == project_id)
        .count()
    )

    activities = [
        ProjectActivityItem(
            event_id=f"project-event-{event.id}",
            event_type=event.event_type,
            happened_at=event.created_at,
            actor_user_id=event.actor_user_id,
            title=event.title,
            description=event.description,
            entity_type=event.entity_type,
            entity_id=event.entity_id,
            metadata=event.metadata_json or {},
        )
        for event in events
    ]

    return ProjectActivityFeedResponse(
        project_id=project.id,
        project_status=project.status,
        total_events=total_events,
        activities=activities,
    )