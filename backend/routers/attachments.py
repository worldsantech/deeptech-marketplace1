import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.core.dependencies import get_current_user
from backend.database.session import get_db
from backend.models.attachment import Attachment
from backend.models.milestone import Milestone
from backend.models.project import Project
from backend.models.user import User
from backend.schemas.attachment import AttachmentResponse
from backend.services.project_event_logger import log_project_event

UPLOAD_DIR = "uploads"
MAX_FILE_SIZE = 10 * 1024 * 1024

ALLOWED_FILE_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "text/plain",
    "application/zip",
}

router = APIRouter(
    prefix="/attachments",
    tags=["Attachments"],
)

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)


def validate_file(file: UploadFile) -> None:
    if file.content_type not in ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{file.content_type}' is not allowed",
        )


def sanitize_original_filename(filename: str | None) -> str:
    original = (filename or "").strip()
    if not original:
        return "file"

    base = os.path.basename(original)
    return base or "file"


def save_file(file: UploadFile) -> tuple[str, str]:
    safe_original_name = sanitize_original_filename(file.filename)
    file_ext = safe_original_name.split(".")[-1].lower() if "." in safe_original_name else "bin"
    safe_storage_name = f"{uuid.uuid4()}.{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, safe_storage_name)

    content = file.file.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large (max 10MB)",
        )

    with open(file_path, "wb") as f:
        f.write(content)

    return safe_original_name, file_path


def get_attachment_or_404(attachment_id: int, db: Session) -> Attachment:
    attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()
    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found",
        )
    return attachment


def get_project_or_404(project_id: int, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return project


def get_project_milestone_or_404(project_id: int, milestone_id: int, db: Session) -> Milestone:
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
            detail="Milestone not found for this project",
        )
    return milestone


def ensure_project_has_selected_provider(project: Project) -> None:
    if not project.selected_applicant_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project does not have selected provider",
        )


def ensure_project_participant(project: Project, current_user: User) -> None:
    ensure_project_has_selected_provider(project)

    allowed_user_ids = {project.owner_id, project.selected_applicant_user_id}
    if current_user.id not in allowed_user_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No access to this project",
        )


def ensure_milestone_matches_project(milestone: Milestone, project: Project) -> None:
    if milestone.project_id != project.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Milestone does not belong to this project",
        )

    if milestone.customer_id != project.owner_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Milestone customer does not match project owner",
        )

    if project.selected_applicant_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project does not have selected provider",
        )

    if milestone.provider_id != project.selected_applicant_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Milestone provider does not match selected provider",
        )


def ensure_attachment_access(
    attachment: Attachment,
    current_user: User,
    db: Session,
) -> Project:
    if not attachment.project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Attachment not linked to project",
        )

    project = get_project_or_404(attachment.project_id, db)
    ensure_project_participant(project, current_user)

    if attachment.milestone_id is not None:
        milestone = get_project_milestone_or_404(project.id, attachment.milestone_id, db)
        ensure_milestone_matches_project(milestone, project)

    return project


@router.post("/upload", response_model=AttachmentResponse, status_code=status.HTTP_201_CREATED)
def upload_attachment(
    project_id: int,
    milestone_id: int | None = None,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_project_or_404(project_id, db)
    ensure_project_participant(project, current_user)

    if project.status not in {"in_progress", "completed"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Attachments can be uploaded only for in_progress or completed projects",
        )

    milestone = None
    if milestone_id is not None:
        milestone = get_project_milestone_or_404(project_id, milestone_id, db)
        ensure_milestone_matches_project(milestone, project)

    validate_file(file)
    original_filename, file_path = save_file(file)

    attachment = Attachment(
        file_name=original_filename,
        file_path=file_path,
        file_type=file.content_type,
        uploaded_by=current_user.id,
        project_id=project_id,
        milestone_id=milestone.id if milestone else None,
    )

    db.add(attachment)
    db.flush()

    log_project_event(
        db=db,
        project_id=project.id,
        event_type="attachment_uploaded",
        title="File uploaded",
        description=original_filename,
        actor_user_id=current_user.id,
        entity_type="attachment",
        entity_id=attachment.id,
        metadata={
            "file_type": file.content_type,
            "milestone_id": milestone.id if milestone else None,
        },
    )

    db.commit()
    db.refresh(attachment)

    return attachment


@router.get("/{attachment_id}/download")
def download_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    attachment = get_attachment_or_404(attachment_id, db)
    ensure_attachment_access(attachment, current_user, db)

    if not os.path.exists(attachment.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on disk",
        )

    return FileResponse(
        path=attachment.file_path,
        filename=attachment.file_name,
        media_type=attachment.file_type or "application/octet-stream",
    )