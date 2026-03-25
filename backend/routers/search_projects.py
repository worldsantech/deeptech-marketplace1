from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.models.project import Project

router = APIRouter(prefix="/search/projects", tags=["Search"])

ALLOWED_PROJECT_TYPES = {
    "automation",
    "mechanical",
    "electrical",
    "plc",
    "maintenance",
}

ALLOWED_CURRENCIES = {
    "EUR",
    "USD",
    "PLN",
}

ALLOWED_PROJECT_STATUSES = {
    "open",
    "in_progress",
    "completed",
    "cancelled",
}

ALLOWED_PROJECT_SORTS = {
    "newest",
    "budget_min",
    "budget_max",
    "deadline_days",
    "title",
}


@router.get("/")
def search_projects(
    q: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    project_type: Optional[str] = Query(None),
    currency: Optional[str] = Query(None),
    status: str = Query("open"),
    budget_min: Optional[int] = Query(None, ge=0),
    budget_max: Optional[int] = Query(None, ge=0),
    deadline_days_max: Optional[int] = Query(None, ge=1),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("newest"),
    db: Session = Depends(get_db),
):
    if sort_by not in ALLOWED_PROJECT_SORTS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sort_by. Allowed values: {', '.join(sorted(ALLOWED_PROJECT_SORTS))}",
        )

    clean_status = status.strip().lower()
    if clean_status not in ALLOWED_PROJECT_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Allowed values: {', '.join(sorted(ALLOWED_PROJECT_STATUSES))}",
        )

    query = db.query(Project)

    if q:
        q_clean = q.strip()
        if q_clean:
            pattern = f"%{q_clean}%"
            query = query.filter(
                or_(
                    Project.title.ilike(pattern),
                    Project.description.ilike(pattern),
                    Project.country.ilike(pattern),
                    Project.city.ilike(pattern),
                    Project.project_type.ilike(pattern),
                    Project.currency.ilike(pattern),
                )
            )

    query = query.filter(Project.status == clean_status)

    if country:
        query = query.filter(Project.country.ilike(country.strip()))

    if city:
        query = query.filter(Project.city.ilike(city.strip()))

    if project_type:
        clean_project_type = project_type.strip().lower()
        if clean_project_type not in ALLOWED_PROJECT_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid project_type. Allowed values: {', '.join(sorted(ALLOWED_PROJECT_TYPES))}",
            )
        query = query.filter(Project.project_type == clean_project_type)

    if currency:
        clean_currency = currency.strip().upper()
        if clean_currency not in ALLOWED_CURRENCIES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid currency. Allowed values: {', '.join(sorted(ALLOWED_CURRENCIES))}",
            )
        query = query.filter(Project.currency == clean_currency)

    if budget_min is not None:
        query = query.filter(Project.budget_max >= budget_min)

    if budget_max is not None:
        query = query.filter(Project.budget_min <= budget_max)

    if deadline_days_max is not None:
        query = query.filter(Project.deadline_days <= deadline_days_max)

    total = query.count()

    if sort_by == "newest":
        query = query.order_by(Project.id.desc())
    elif sort_by == "budget_min":
        query = query.order_by(Project.budget_min.asc(), Project.id.desc())
    elif sort_by == "budget_max":
        query = query.order_by(Project.budget_max.desc(), Project.id.desc())
    elif sort_by == "deadline_days":
        query = query.order_by(Project.deadline_days.asc(), Project.id.desc())
    elif sort_by == "title":
        query = query.order_by(Project.title.asc(), Project.id.desc())

    items = query.offset(offset).limit(limit).all()

    page = (offset // limit) + 1 if limit else 1
    pages = (total + limit - 1) // limit if limit else 1

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "page": page,
        "pages": pages,
        "filters": {
            "q": q,
            "country": country,
            "city": city,
            "project_type": project_type,
            "currency": currency,
            "status": clean_status,
            "budget_min": budget_min,
            "budget_max": budget_max,
            "deadline_days_max": deadline_days_max,
            "sort_by": sort_by,
        },
        "items": items,
    }