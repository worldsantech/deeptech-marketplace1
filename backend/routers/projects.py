from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.core.dependencies import get_current_user
from backend.core.roles import ROLE_CUSTOMER
from backend.database.session import get_db
from backend.models.project import Project
from backend.models.user import User
from backend.services.project_event_logger import log_project_event

router = APIRouter(prefix="/projects", tags=["Projects"])

ALLOWED_PROJECT_TYPES = {
    "automation",
    "mechanical",
    "electrical",
    "plc",
    "maintenance",
}

ALLOWED_PROJECT_STATUSES = {
    "open",
    "in_progress",
    "completed",
    "cancelled",
}


@router.post("")
def create_project(
    title: str,
    description: str,
    country: str,
    project_type: str,
    budget_min: int,
    budget_max: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != ROLE_CUSTOMER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only customers can create projects",
        )

    clean_title = title.strip()
    clean_description = description.strip()
    clean_country = country.strip()
    clean_project_type = project_type.strip().lower()

    if not clean_title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Title cannot be empty",
        )

    if not clean_description:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Description cannot be empty",
        )

    if clean_project_type not in ALLOWED_PROJECT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid project type. Allowed: {sorted(ALLOWED_PROJECT_TYPES)}",
        )

    if budget_min > budget_max:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="budget_min cannot be greater than budget_max",
        )

    project = Project(
        title=clean_title,
        description=clean_description,
        country=clean_country,
        project_type=clean_project_type,
        budget_min=budget_min,
        budget_max=budget_max,
        owner_id=current_user.id,
        status="open",
    )

    db.add(project)
    db.flush()

    log_project_event(
        db=db,
        project_id=project.id,
        event_type="project_created",
        title="Project created",
        description=project.title,
        actor_user_id=current_user.id,
        entity_type="project",
        entity_id=project.id,
        metadata={
            "country": project.country,
            "project_type": project.project_type,
            "budget_min": project.budget_min,
            "budget_max": project.budget_max,
            "status": project.status,
        },
    )

    db.commit()
    db.refresh(project)

    return project


@router.get("/my")
def get_my_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Project)
        .filter(Project.owner_id == current_user.id)
        .order_by(Project.id.desc())
        .all()
    )


@router.get("/{project_id}")
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    return project


@router.put("/{project_id}")
def update_project(
    project_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    country: Optional[str] = None,
    project_type: Optional[str] = None,
    budget_min: Optional[int] = None,
    budget_max: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to edit this project",
        )

    clean_project_type = None
    if project_type is not None:
        clean_project_type = project_type.strip().lower()
        if clean_project_type not in ALLOWED_PROJECT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid project type. Allowed: {sorted(ALLOWED_PROJECT_TYPES)}",
            )

    clean_status = None
    if status is not None:
        clean_status = status.strip().lower()
        if clean_status not in ALLOWED_PROJECT_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Allowed: {sorted(ALLOWED_PROJECT_STATUSES)}",
            )

    new_budget_min = budget_min if budget_min is not None else project.budget_min
    new_budget_max = budget_max if budget_max is not None else project.budget_max

    if new_budget_min is not None and new_budget_max is not None:
        if new_budget_min > new_budget_max:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="budget_min cannot be greater than budget_max",
            )

    original_title = project.title
    original_description = project.description
    original_country = project.country
    original_project_type = project.project_type
    original_budget_min = project.budget_min
    original_budget_max = project.budget_max
    original_status = project.status

    changed_fields = []

    if title is not None:
        clean_title = title.strip()
        if clean_title != project.title:
            project.title = clean_title
            changed_fields.append("title")

    if description is not None:
        clean_description = description.strip()
        if clean_description != project.description:
            project.description = clean_description
            changed_fields.append("description")

    if country is not None:
        clean_country = country.strip()
        if clean_country != project.country:
            project.country = clean_country
            changed_fields.append("country")

    if clean_project_type is not None and clean_project_type != project.project_type:
        project.project_type = clean_project_type
        changed_fields.append("project_type")

    if budget_min is not None and budget_min != project.budget_min:
        project.budget_min = budget_min
        changed_fields.append("budget_min")

    if budget_max is not None and budget_max != project.budget_max:
        project.budget_max = budget_max
        changed_fields.append("budget_max")

    status_changed = False
    if clean_status is not None and clean_status != project.status:
        project.status = clean_status
        changed_fields.append("status")
        status_changed = True

    if changed_fields:
        log_project_event(
            db=db,
            project_id=project.id,
            event_type="project_updated",
            title="Project updated",
            description=project.title,
            actor_user_id=current_user.id,
            entity_type="project",
            entity_id=project.id,
            metadata={
                "changed_fields": changed_fields,
                "before": {
                    "title": original_title,
                    "description": original_description,
                    "country": original_country,
                    "project_type": original_project_type,
                    "budget_min": original_budget_min,
                    "budget_max": original_budget_max,
                    "status": original_status,
                },
                "after": {
                    "title": project.title,
                    "description": project.description,
                    "country": project.country,
                    "project_type": project.project_type,
                    "budget_min": project.budget_min,
                    "budget_max": project.budget_max,
                    "status": project.status,
                },
            },
        )

    if status_changed:
        log_project_event(
            db=db,
            project_id=project.id,
            event_type="project_status_changed",
            title="Project status changed",
            description=f"{original_status} → {project.status}",
            actor_user_id=current_user.id,
            entity_type="project",
            entity_id=project.id,
            metadata={
                "old_status": original_status,
                "new_status": project.status,
            },
        )

    db.commit()
    db.refresh(project)

    return project