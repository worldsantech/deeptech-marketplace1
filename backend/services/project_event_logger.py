from typing import Any, Optional

from sqlalchemy.orm import Session

from backend.models.notification import Notification
from backend.models.project import Project
from backend.models.project_event import ProjectEvent


def create_notification(
    db: Session,
    user_id: int,
    notification_type: str,
    title: str,
    message: Optional[str] = None,
    related_project_id: Optional[int] = None,
    related_application_id: Optional[int] = None,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        type=notification_type,
        title=title,
        message=message,
        related_project_id=related_project_id,
        related_application_id=related_application_id,
        is_read=False,
    )
    db.add(notification)
    db.flush()
    return notification


def _create_notifications_from_event(
    db: Session,
    project: Project,
    event: ProjectEvent,
):
    owner_id = project.owner_id
    provider_id = project.selected_applicant_user_id

    if event.event_type == "message_sent":
        recipient_user_id = (event.metadata_json or {}).get("recipient_user_id")
        if recipient_user_id:
            create_notification(
                db=db,
                user_id=recipient_user_id,
                notification_type="new_message",
                title="New message",
                message=event.description or "You received a new message",
                related_project_id=project.id,
            )
        return

    if event.event_type == "application_submitted":
        if owner_id and event.actor_user_id != owner_id:
            create_notification(
                db=db,
                user_id=owner_id,
                notification_type="new_application",
                title="New application received",
                message=event.description or "A provider applied to your project",
                related_project_id=project.id,
                related_application_id=event.entity_id if event.entity_type == "application" else None,
            )
        return

    if event.event_type in {"application_shortlisted", "application_accepted", "application_rejected"}:
        applicant_user_id = (event.metadata_json or {}).get("applicant_user_id")
        if applicant_user_id and event.actor_user_id != applicant_user_id:
            create_notification(
                db=db,
                user_id=applicant_user_id,
                notification_type="application_status_updated",
                title="Application status updated",
                message=event.description or f"Your application was updated: {event.event_type}",
                related_project_id=project.id,
                related_application_id=event.entity_id if event.entity_type == "application" else None,
            )
        return

    if event.event_type == "provider_selected":
        selected_provider_id = (event.metadata_json or {}).get("selected_provider_id")
        if selected_provider_id and event.actor_user_id != selected_provider_id:
            create_notification(
                db=db,
                user_id=selected_provider_id,
                notification_type="provider_selected",
                title="You were selected",
                message="Customer selected you for the project",
                related_project_id=project.id,
                related_application_id=(event.metadata_json or {}).get("selected_application_id"),
            )
        return

    if event.event_type == "milestone_created":
        if provider_id and event.actor_user_id != provider_id:
            create_notification(
                db=db,
                user_id=provider_id,
                notification_type="milestone_created",
                title="New milestone created",
                message=event.description or "A new milestone was added",
                related_project_id=project.id,
            )
        return

    if event.event_type == "milestone_submitted":
        if owner_id and event.actor_user_id != owner_id:
            create_notification(
                db=db,
                user_id=owner_id,
                notification_type="milestone_submitted",
                title="Milestone submitted",
                message=event.description or "A milestone was submitted for review",
                related_project_id=project.id,
            )
        return

    if event.event_type in {"milestone_approved", "milestone_changes_requested"}:
        if provider_id and event.actor_user_id != provider_id:
            create_notification(
                db=db,
                user_id=provider_id,
                notification_type=event.event_type,
                title="Milestone updated",
                message=event.description or "Milestone status changed",
                related_project_id=project.id,
            )
        return

    if event.event_type == "completion_requested":
        if owner_id and event.actor_user_id != owner_id:
            create_notification(
                db=db,
                user_id=owner_id,
                notification_type="completion_requested",
                title="Project completion requested",
                message=event.description or "Provider requested project completion",
                related_project_id=project.id,
            )
        return

    if event.event_type in {"completion_approved", "completion_reopened"}:
        if provider_id and event.actor_user_id != provider_id:
            create_notification(
                db=db,
                user_id=provider_id,
                notification_type=event.event_type,
                title="Project status updated",
                message=event.description or "Project completion status changed",
                related_project_id=project.id,
            )
        return

    if event.event_type == "attachment_uploaded":
        other_user_id = None
        if event.actor_user_id == owner_id:
            other_user_id = provider_id
        elif event.actor_user_id == provider_id:
            other_user_id = owner_id

        if other_user_id:
            create_notification(
                db=db,
                user_id=other_user_id,
                notification_type="attachment_uploaded",
                title="New file uploaded",
                message=event.description or "A file was uploaded to the project",
                related_project_id=project.id,
            )
        return

    if event.event_type == "review_created":
        reviewed_user_id = (event.metadata_json or {}).get("reviewed_user_id")
        if reviewed_user_id and event.actor_user_id != reviewed_user_id:
            create_notification(
                db=db,
                user_id=reviewed_user_id,
                notification_type="review_created",
                title="New review received",
                message=event.description or "A review was added to the project",
                related_project_id=project.id,
            )
        return


def log_project_event(
    db: Session,
    project_id: int,
    event_type: str,
    title: str,
    description: Optional[str] = None,
    actor_user_id: Optional[int] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> ProjectEvent:
    event = ProjectEvent(
        project_id=project_id,
        actor_user_id=actor_user_id,
        event_type=event_type,
        title=title,
        description=description,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_json=metadata or {},
    )

    db.add(event)
    db.flush()

    project = db.query(Project).filter(Project.id == project_id).first()
    if project:
        _create_notifications_from_event(db=db, project=project, event=event)

    return event