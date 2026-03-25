from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.models.project import Project

router = APIRouter(prefix="/search/projects", tags=["Search"])


ALLOWED_PROJECT_SORTS = ["newest", "budget_min", "budget_max"]


@router.get("/")
def search_projects(
    country: Optional[str] = Query(None),
    project_type: Optional[str] = Query(None),
    budget_min: Optional[int] = Query(None),
    budget_max: Optional[int] = Query(None),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("newest"),
    db: Session = Depends(get_db),
):
    if sort_by not in ALLOWED_PROJECT_SORTS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sort_by. Allowed values: {', '.join(ALLOWED_PROJECT_SORTS)}"
        )

    query = db.query(Project)

    # marketplace показує тільки відкриті проєкти
    query = query.filter(Project.status == "open")

    if country:
        query = query.filter(Project.country == country)

    if project_type:
        query = query.filter(Project.project_type == project_type)

    if budget_min is not None:
        query = query.filter(Project.budget_min >= budget_min)

    if budget_max is not None:
        query = query.filter(Project.budget_max <= budget_max)

    total = query.count()

    if sort_by == "newest":
        query = query.order_by(Project.id.desc())
    elif sort_by == "budget_min":
        query = query.order_by(Project.budget_min.asc(), Project.id.desc())
    elif sort_by == "budget_max":
        query = query.order_by(Project.budget_max.asc(), Project.id.desc())

    items = query.offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "sort_by": sort_by,
        "items": items,
    }