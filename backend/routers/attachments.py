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


def validate_file(file: UploadFile):
    if file.content_type not in ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{file.content_type}' is not allowed",
        )


def save_file(file: UploadFile) -> tuple[str, str]:
    file_ext = file.filename.split(".")[-1].lower() if "." in file.filename else "bin"
    safe_name = f"{uuid.uuid4()}.{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)

    content = file.file.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large (max 10MB)",
        )

    with open(file_path, "wb") as f:
        f.write(content)

    return safe_name, file_path


def get_attachment_or_404(attachment_id: int, db: Session) -> Attachment:
    attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    return attachment


def get_project_or_404(project_id: int, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def check_project_access(project: Project, current_user: User):
    if current_user.id not in [project.owner_id, project.selected_applicant_user_id]:
        raise HTTPException(status_code=403, detail="No access to this project")


def check_attachment_access(
    attachment: Attachment,
    current_user: User,
    db: Session,
):
    if not attachment.project_id:
        raise HTTPException(status_code=400, detail="Attachment not linked to project")

    project = get_project_or_404(attachment.project_id, db)
    check_project_access(project, current_user)


@router.post("/upload", response_model=AttachmentResponse)
def upload_attachment(
    project_id: int,
    milestone_id: int | None = None,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_project_or_404(project_id, db)
    check_project_access(project, current_user)

    milestone = None
    if milestone_id is not None:
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
                status_code=404,
                detail="Milestone not found for this project",
            )

    validate_file(file)
    _, file_path = save_file(file)

    attachment = Attachment(
        file_name=file.filename,
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
        description=file.filename,
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
    check_attachment_access(attachment, current_user, db)

    if not os.path.exists(attachment.file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(
        path=attachment.file_path,
        filename=attachment.file_name,
        media_type=attachment.file_type or "application/octet-stream",
    )