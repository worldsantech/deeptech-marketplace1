from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.core.dependencies import get_current_provider
from backend.database.session import get_db
from backend.models.project import Project
from backend.models.saved_project import SavedProject
from backend.models.user import User

router = APIRouter(prefix="/favorites", tags=["Favorites"])


def get_project_or_404(project_id: int, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return project


def ensure_project_visible_for_favorites(project: Project) -> None:
    if project.status != "open":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only open projects can be added to favorites",
        )


def get_saved_project_for_provider(
    db: Session,
    provider_id: int,
    project_id: int,
) -> SavedProject | None:
    return (
        db.query(SavedProject)
        .filter(
            SavedProject.provider_id == provider_id,
            SavedProject.project_id == project_id,
        )
        .first()
    )


@router.post("/projects/{project_id}", status_code=status.HTTP_201_CREATED)
def save_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_provider),
):
    project = get_project_or_404(project_id, db)
    ensure_project_visible_for_favorites(project)

    existing_saved = get_saved_project_for_provider(
        db=db,
        provider_id=current_user.id,
        project_id=project_id,
    )
    if existing_saved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project already saved",
        )

    saved_project = SavedProject(
        provider_id=current_user.id,
        project_id=project_id,
    )

    db.add(saved_project)
    db.commit()
    db.refresh(saved_project)

    return {
        "message": "Project saved successfully",
        "is_saved": True,
        "saved_project_id": saved_project.id,
        "project_id": project.id,
    }


@router.post("/projects/{project_id}/toggle")
def toggle_saved_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_provider),
):
    project = get_project_or_404(project_id, db)
    ensure_project_visible_for_favorites(project)

    existing_saved = get_saved_project_for_provider(
        db=db,
        provider_id=current_user.id,
        project_id=project_id,
    )

    if existing_saved:
        db.delete(existing_saved)
        db.commit()

        return {
            "message": "Project removed from favorites",
            "is_saved": False,
            "project_id": project_id,
        }

    saved_project = SavedProject(
        provider_id=current_user.id,
        project_id=project_id,
    )

    db.add(saved_project)
    db.commit()
    db.refresh(saved_project)

    return {
        "message": "Project saved successfully",
        "is_saved": True,
        "saved_project_id": saved_project.id,
        "project_id": project_id,
    }


@router.get("/projects/my")
def get_my_saved_projects(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_provider),
):
    base_query = (
        db.query(SavedProject, Project)
        .join(Project, Project.id == SavedProject.project_id)
        .filter(SavedProject.provider_id == current_user.id)
    )

    total = base_query.count()

    rows = (
        base_query
        .order_by(SavedProject.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = []
    for saved, project in rows:
        items.append(
            {
                "saved_project_id": saved.id,
                "saved_at": saved.created_at,
                "project": {
                    "id": project.id,
                    "title": project.title,
                    "description": project.description,
                    "country": project.country,
                    "project_type": project.project_type,
                    "budget_min": project.budget_min,
                    "budget_max": project.budget_max,
                    "status": project.status,
                    "owner_id": project.owner_id,
                },
            }
        )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": items,
    }


@router.get("/projects/ids")
def get_my_saved_project_ids(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_provider),
):
    rows = (
        db.query(SavedProject.project_id)
        .filter(SavedProject.provider_id == current_user.id)
        .order_by(SavedProject.id.desc())
        .all()
    )

    project_ids = [row[0] for row in rows]

    return {
        "total": len(project_ids),
        "project_ids": project_ids,
    }


@router.delete("/projects/{project_id}")
def remove_saved_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_provider),
):
    saved_project = get_saved_project_for_provider(
        db=db,
        provider_id=current_user.id,
        project_id=project_id,
    )

    if not saved_project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved project not found",
        )

    db.delete(saved_project)
    db.commit()

    return {
        "message": "Saved project removed successfully",
        "is_saved": False,
        "project_id": project_id,
    }