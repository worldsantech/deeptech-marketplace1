import logging
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from backend.core.dependencies import get_current_user
from backend.database.session import get_db
from backend.models.attachment import Attachment
from backend.models.message import Message
from backend.models.project import Project
from backend.models.user import User
from backend.schemas.attachment import AttachmentResponse
from backend.schemas.message import (
    ChatLastMessageInfo,
    ChatListItemResponse,
    ChatProjectInfo,
    ChatUserInfo,
    MessageCreate,
    MessageResponse,
    UnreadCountResponse,
)
from backend.services.project_event_logger import log_project_event

logger = logging.getLogger("app")

router = APIRouter(
    prefix="/messages",
    tags=["Messages"],
)

CHAT_ALLOWED_PROJECT_STATUSES = {"in_progress", "completed"}


def get_project_or_404(project_id: int, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return project


def get_user_or_404(user_id: int, db: Session) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


def ensure_project_has_chat_enabled(project: Project) -> None:
    if not project.selected_applicant_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project does not have selected provider yet",
        )

    if project.status not in CHAT_ALLOWED_PROJECT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Messaging is available only for in_progress or completed projects",
        )


def ensure_project_participant(project: Project, current_user: User) -> None:
    ensure_project_has_chat_enabled(project)

    is_customer = current_user.id == project.owner_id
    is_selected_provider = current_user.id == project.selected_applicant_user_id

    if not (is_customer or is_selected_provider):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this project chat",
        )


def get_other_chat_participant_user_id(project: Project, current_user: User) -> int:
    ensure_project_participant(project, current_user)

    if current_user.id == project.owner_id:
        return project.selected_applicant_user_id

    return project.owner_id


def get_message_attachments(message_id: int, db: Session) -> List[Attachment]:
    return (
        db.query(Attachment)
        .filter(Attachment.message_id == message_id)
        .order_by(Attachment.created_at.asc(), Attachment.id.asc())
        .all()
    )


def build_message_response(message: Message, db: Session) -> MessageResponse:
    attachments = get_message_attachments(message.id, db)

    return MessageResponse(
        id=message.id,
        project_id=message.project_id,
        sender_user_id=message.sender_user_id,
        recipient_user_id=message.recipient_user_id,
        body=message.body,
        is_read=message.is_read,
        read_at=message.read_at,
        created_at=message.created_at,
        attachments=[AttachmentResponse.model_validate(item) for item in attachments],
    )


@router.post(
    "/send",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def send_message(
    payload: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        project = get_project_or_404(payload.project_id, db)
        expected_recipient_user_id = get_other_chat_participant_user_id(project, current_user)

        if (
            payload.recipient_user_id is not None
            and payload.recipient_user_id != expected_recipient_user_id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="recipient_user_id does not match project chat participant",
            )

        body = (payload.body or "").strip()

        attachment_ids = payload.attachment_ids or []
        unique_attachment_ids = list(dict.fromkeys(attachment_ids))

        if not body and not unique_attachment_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message must contain text or at least one attachment",
            )

        attachments: list[Attachment] = []
        if unique_attachment_ids:
            attachments = (
                db.query(Attachment)
                .filter(Attachment.id.in_(unique_attachment_ids))
                .all()
            )

            if len(attachments) != len(unique_attachment_ids):
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
                        detail="Attachment is already linked to another message",
                    )

        message = Message(
            project_id=project.id,
            sender_user_id=current_user.id,
            recipient_user_id=expected_recipient_user_id,
            body=body or None,
            is_read=False,
        )

        db.add(message)
        db.flush()

        for attachment in attachments:
            attachment.message_id = message.id

        body_preview = body[:200] if body else None

        log_project_event(
            db=db,
            project_id=project.id,
            event_type="message_sent",
            title="Message sent",
            description=body_preview or f"Message with {len(attachments)} attachment(s)",
            actor_user_id=current_user.id,
            entity_type="message",
            entity_id=message.id,
            metadata={
                "recipient_user_id": expected_recipient_user_id,
                "attachments_count": len(attachments),
            },
        )

        db.commit()
        db.refresh(message)

        return build_message_response(message, db)

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception(
            "Unhandled error while sending message. project_id=%s user_id=%s",
            payload.project_id,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send message",
        )


@router.get(
    "/project/{project_id}",
    response_model=List[MessageResponse],
)
def get_project_messages(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_project_or_404(project_id, db)
    ensure_project_participant(project, current_user)

    messages = (
        db.query(Message)
        .filter(Message.project_id == project_id)
        .order_by(Message.created_at.asc(), Message.id.asc())
        .all()
    )

    return [build_message_response(message, db) for message in messages]


@router.post(
    "/project/{project_id}/mark-as-read",
    response_model=UnreadCountResponse,
)
def mark_project_messages_as_read(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        project = get_project_or_404(project_id, db)
        ensure_project_participant(project, current_user)

        unread_messages = (
            db.query(Message)
            .filter(
                Message.project_id == project_id,
                Message.recipient_user_id == current_user.id,
                Message.is_read.is_(False),
            )
            .all()
        )

        now = datetime.now(timezone.utc)

        for message in unread_messages:
            message.is_read = True
            message.read_at = now

        if unread_messages:
            db.commit()

        remaining_unread_count = (
            db.query(Message)
            .filter(
                Message.project_id == project_id,
                Message.recipient_user_id == current_user.id,
                Message.is_read.is_(False),
            )
            .count()
        )

        return UnreadCountResponse(unread_count=remaining_unread_count)

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception(
            "Unhandled error while marking messages as read. project_id=%s user_id=%s",
            project_id,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark messages as read",
        )


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
)
def get_total_unread_messages_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    unread_count = (
        db.query(Message)
        .filter(
            Message.recipient_user_id == current_user.id,
            Message.is_read.is_(False),
        )
        .count()
    )

    return UnreadCountResponse(unread_count=unread_count)


@router.get(
    "/project/{project_id}/unread-count",
    response_model=UnreadCountResponse,
)
def get_project_unread_messages_count(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_project_or_404(project_id, db)
    ensure_project_participant(project, current_user)

    unread_count = (
        db.query(Message)
        .filter(
            Message.project_id == project_id,
            Message.recipient_user_id == current_user.id,
            Message.is_read.is_(False),
        )
        .count()
    )

    return UnreadCountResponse(unread_count=unread_count)


@router.get(
    "/chats",
    response_model=List[ChatListItemResponse],
)
def get_chats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    projects = (
        db.query(Project)
        .filter(
            and_(
                Project.selected_applicant_user_id.isnot(None),
                Project.status.in_(list(CHAT_ALLOWED_PROJECT_STATUSES)),
                or_(
                    Project.owner_id == current_user.id,
                    Project.selected_applicant_user_id == current_user.id,
                ),
            )
        )
        .order_by(Project.id.desc())
        .all()
    )

    result = []

    for project in projects:
        other_user_id = (
            project.selected_applicant_user_id
            if current_user.id == project.owner_id
            else project.owner_id
        )

        other_user = get_user_or_404(other_user_id, db)

        last_message = (
            db.query(Message)
            .filter(Message.project_id == project.id)
            .order_by(Message.created_at.desc(), Message.id.desc())
            .first()
        )

        unread_count = (
            db.query(Message)
            .filter(
                Message.project_id == project.id,
                Message.recipient_user_id == current_user.id,
                Message.is_read.is_(False),
            )
            .count()
        )

        last_message_payload = None
        if last_message:
            attachments_count = (
                db.query(Attachment)
                .filter(Attachment.message_id == last_message.id)
                .count()
            )

            last_message_payload = ChatLastMessageInfo(
                id=last_message.id,
                body=last_message.body,
                sender_user_id=last_message.sender_user_id,
                created_at=last_message.created_at,
                attachments_count=attachments_count,
            )

        result.append(
            ChatListItemResponse(
                project=ChatProjectInfo(
                    id=project.id,
                    title=project.title,
                    status=project.status,
                ),
                other_user=ChatUserInfo(
                    id=other_user.id,
                    email=other_user.email,
                    role=other_user.role,
                ),
                last_message=last_message_payload,
                unread_count=unread_count,
            )
        )

    return result