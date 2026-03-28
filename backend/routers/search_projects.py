from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
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


def validate_budget_range(budget_min: int | None, budget_max: int | None) -> None:
    if budget_min is not None and budget_max is not None and budget_min > budget_max:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="budget_min cannot be greater than budget_max",
        )


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
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort_by. Allowed values: {', '.join(sorted(ALLOWED_PROJECT_SORTS))}",
        )

    clean_status = status.strip().lower()
    if clean_status not in ALLOWED_PROJECT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Allowed values: {', '.join(sorted(ALLOWED_PROJECT_STATUSES))}",
        )

    validate_budget_range(budget_min, budget_max)

    query = db.query(Project).filter(Project.status == clean_status)

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

    if country:
        country_clean = country.strip()
        if country_clean:
            query = query.filter(Project.country.ilike(country_clean))

    if city:
        city_clean = city.strip()
        if city_clean:
            query = query.filter(Project.city.ilike(city_clean))

    if project_type:
        clean_project_type = project_type.strip().lower()
        if clean_project_type not in ALLOWED_PROJECT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid project_type. Allowed values: {', '.join(sorted(ALLOWED_PROJECT_TYPES))}",
            )
        query = query.filter(Project.project_type == clean_project_type)

    if currency:
        clean_currency = currency.strip().upper()
        if clean_currency not in ALLOWED_CURRENCIES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
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
        query = query.order_by(Project.created_at.desc(), Project.id.desc())
    elif sort_by == "budget_min":
        query = query.order_by(Project.budget_min.asc(), Project.id.desc())
    elif sort_by == "budget_max":
        query = query.order_by(Project.budget_max.desc(), Project.id.desc())
    elif sort_by == "deadline_days":
        query = query.order_by(Project.deadline_days.asc(), Project.id.desc())
    elif sort_by == "title":
        query = query.order_by(Project.title.asc(), Project.id.desc())

    items = query.offset(offset).limit(limit).all()

    page = (offset // limit) + 1
    pages = (total + limit - 1) // limit

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