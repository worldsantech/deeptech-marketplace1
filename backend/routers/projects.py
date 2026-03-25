from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.core.dependencies import get_current_user
from backend.core.roles import ROLE_CUSTOMER
from backend.database.session import get_db
from backend.models.project import Project
from backend.models.user import User
from backend.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
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

ALLOWED_CURRENCIES = {
    "EUR",
    "USD",
    "PLN",
}

ALLOWED_SORT_FIELDS = {
    "created_at",
    "budget_min",
    "budget_max",
    "deadline_days",
    "title",
    "country",
    "city",
}

ALLOWED_SORT_ORDERS = {
    "asc",
    "desc",
}


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != ROLE_CUSTOMER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only customers can create projects",
        )

    clean_title = payload.title.strip()
    clean_description = payload.description.strip()
    clean_country = payload.country.strip()
    clean_city = payload.city.strip() if payload.city else None
    clean_project_type = payload.project_type.strip().lower()
    clean_currency = payload.currency.strip().upper() if payload.currency else "EUR"

    if clean_project_type not in ALLOWED_PROJECT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid project type. Allowed: {sorted(ALLOWED_PROJECT_TYPES)}",
        )

    if clean_currency not in ALLOWED_CURRENCIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid currency. Allowed: {sorted(ALLOWED_CURRENCIES)}",
        )

    if payload.budget_min > payload.budget_max:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="budget_min cannot be greater than budget_max",
        )

    project = Project(
        title=clean_title,
        description=clean_description,
        country=clean_country,
        city=clean_city,
        project_type=clean_project_type,
        budget_min=payload.budget_min,
        budget_max=payload.budget_max,
        currency=clean_currency,
        deadline_days=payload.deadline_days,
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
            "city": project.city,
            "project_type": project.project_type,
            "budget_min": project.budget_min,
            "budget_max": project.budget_max,
            "currency": project.currency,
            "deadline_days": project.deadline_days,
            "status": project.status,
        },
    )

    db.commit()
    db.refresh(project)

    return project


@router.get("/search")
def search_projects(
    q: str | None = Query(None),
    country: str | None = Query(None),
    city: str | None = Query(None),
    project_type: str | None = Query(None),
    currency: str | None = Query(None),
    status: str | None = Query("open"),
    budget_min: int | None = Query(None, ge=0),
    budget_max: int | None = Query(None, ge=0),
    deadline_days_max: int | None = Query(None, ge=1),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
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
                )
            )

    if country:
        query = query.filter(Project.country.ilike(country.strip()))

    if city:
        query = query.filter(Project.city.ilike(city.strip()))

    if project_type:
        clean_project_type = project_type.strip().lower()
        if clean_project_type not in ALLOWED_PROJECT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid project type. Allowed: {sorted(ALLOWED_PROJECT_TYPES)}",
            )
        query = query.filter(Project.project_type == clean_project_type)

    if currency:
        clean_currency = currency.strip().upper()
        if clean_currency not in ALLOWED_CURRENCIES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid currency. Allowed: {sorted(ALLOWED_CURRENCIES)}",
            )
        query = query.filter(Project.currency == clean_currency)

    if status:
        clean_status = status.strip().lower()
        if clean_status not in ALLOWED_PROJECT_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Allowed: {sorted(ALLOWED_PROJECT_STATUSES)}",
            )
        query = query.filter(Project.status == clean_status)

    if budget_min is not None:
        query = query.filter(Project.budget_max >= budget_min)

    if budget_max is not None:
        query = query.filter(Project.budget_min <= budget_max)

    if deadline_days_max is not None:
        query = query.filter(Project.deadline_days <= deadline_days_max)

    if sort_by not in ALLOWED_SORT_FIELDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort_by. Allowed: {sorted(ALLOWED_SORT_FIELDS)}",
        )

    if sort_order not in ALLOWED_SORT_ORDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort_order. Allowed: {sorted(ALLOWED_SORT_ORDERS)}",
        )

    sort_column = getattr(Project, sort_by)
    if sort_order == "asc":
        query = query.order_by(sort_column.asc(), Project.id.desc())
    else:
        query = query.order_by(sort_column.desc(), Project.id.desc())

    total = query.count()

    offset = (page - 1) * page_size
    items = query.offset(offset).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
        "filters": {
            "q": q,
            "country": country,
            "city": city,
            "project_type": project_type,
            "currency": currency,
            "status": status,
            "budget_min": budget_min,
            "budget_max": budget_max,
            "deadline_days_max": deadline_days_max,
            "sort_by": sort_by,
            "sort_order": sort_order,
        },
        "items": items,
    }


@router.get("/my", response_model=list[ProjectResponse])
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


@router.get("/{project_id}", response_model=ProjectResponse)
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


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
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
    if payload.project_type is not None:
        clean_project_type = payload.project_type.strip().lower()
        if clean_project_type not in ALLOWED_PROJECT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid project type. Allowed: {sorted(ALLOWED_PROJECT_TYPES)}",
            )

    clean_status = None
    if payload.status is not None:
        clean_status = payload.status.strip().lower()
        if clean_status not in ALLOWED_PROJECT_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Allowed: {sorted(ALLOWED_PROJECT_STATUSES)}",
            )

    clean_currency = None
    if payload.currency is not None:
        clean_currency = payload.currency.strip().upper()
        if clean_currency not in ALLOWED_CURRENCIES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid currency. Allowed: {sorted(ALLOWED_CURRENCIES)}",
            )

    new_budget_min = payload.budget_min if payload.budget_min is not None else project.budget_min
    new_budget_max = payload.budget_max if payload.budget_max is not None else project.budget_max

    if new_budget_min is not None and new_budget_max is not None:
        if new_budget_min > new_budget_max:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="budget_min cannot be greater than budget_max",
            )

    original_title = project.title
    original_description = project.description
    original_country = project.country
    original_city = project.city
    original_project_type = project.project_type
    original_budget_min = project.budget_min
    original_budget_max = project.budget_max
    original_currency = project.currency
    original_deadline_days = project.deadline_days
    original_status = project.status

    changed_fields = []

    if payload.title is not None:
        clean_title = payload.title.strip()
        if clean_title != project.title:
            project.title = clean_title
            changed_fields.append("title")

    if payload.description is not None:
        clean_description = payload.description.strip()
        if clean_description != project.description:
            project.description = clean_description
            changed_fields.append("description")

    if payload.country is not None:
        clean_country = payload.country.strip()
        if clean_country != project.country:
            project.country = clean_country
            changed_fields.append("country")

    if payload.city is not None:
        clean_city = payload.city.strip()
        if clean_city != project.city:
            project.city = clean_city
            changed_fields.append("city")

    if clean_project_type is not None and clean_project_type != project.project_type:
        project.project_type = clean_project_type
        changed_fields.append("project_type")

    if payload.budget_min is not None and payload.budget_min != project.budget_min:
        project.budget_min = payload.budget_min
        changed_fields.append("budget_min")

    if payload.budget_max is not None and payload.budget_max != project.budget_max:
        project.budget_max = payload.budget_max
        changed_fields.append("budget_max")

    if clean_currency is not None and clean_currency != project.currency:
        project.currency = clean_currency
        changed_fields.append("currency")

    if payload.deadline_days is not None and payload.deadline_days != project.deadline_days:
        project.deadline_days = payload.deadline_days
        changed_fields.append("deadline_days")

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
                    "city": original_city,
                    "project_type": original_project_type,
                    "budget_min": original_budget_min,
                    "budget_max": original_budget_max,
                    "currency": original_currency,
                    "deadline_days": original_deadline_days,
                    "status": original_status,
                },
                "after": {
                    "title": project.title,
                    "description": project.description,
                    "country": project.country,
                    "city": project.city,
                    "project_type": project.project_type,
                    "budget_min": project.budget_min,
                    "budget_max": project.budget_max,
                    "currency": project.currency,
                    "deadline_days": project.deadline_days,
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