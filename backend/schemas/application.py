from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.project import ProjectResponse


class ApplicationCreate(BaseModel):
    project_id: int = Field(..., ge=1)
    cover_letter: str = Field(..., min_length=1, max_length=5000)
    proposed_budget: int = Field(..., ge=0)
    estimated_timeline_days: int = Field(..., ge=1, le=3650)


class ApplicationStatusUpdate(BaseModel):
    status: str = Field(..., min_length=2, max_length=50)


class ApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    applicant_user_id: int
    application_type: str
    cover_letter: str
    proposed_budget: int
    estimated_timeline_days: int
    status: str
    created_at: Optional[datetime] = None


class ProjectSelectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    title: str
    description: str
    country: Optional[str] = None
    city: Optional[str] = None
    project_type: Optional[str] = None
    budget_min: Optional[int] = None
    budget_max: Optional[int] = None
    currency: Optional[str] = None
    deadline_days: Optional[int] = None
    status: str
    selected_application_id: Optional[int] = None
    selected_applicant_user_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ApplicationStatusUpdateResponse(BaseModel):
    application: ApplicationResponse
    project: ProjectSelectionResponse
    auto_rejected_applications: List[ApplicationResponse]


class MyApplicationProjectInfo(BaseModel):
    id: int
    title: str
    country: str
    city: Optional[str] = None
    project_type: Optional[str] = None
    budget_min: Optional[int] = None
    budget_max: Optional[int] = None
    currency: Optional[str] = None
    deadline_days: Optional[int] = None
    status: str
    owner_id: int


class MyApplicationListItem(BaseModel):
    application: ApplicationResponse
    project: MyApplicationProjectInfo


class MyApplicationsListResponse(BaseModel):
    total: int
    items: List[MyApplicationListItem]


class ProjectApplicationsListResponse(BaseModel):
    project_id: int
    total: int
    items: List[ApplicationResponse]


class ProviderUserSummary(BaseModel):
    id: int
    full_name: str
    email: str
    role: str


class ProviderProfileSummary(BaseModel):
    bio: Optional[str] = None
    skills: Optional[str] = None
    country: Optional[str] = None
    availability: Optional[str] = None


class ProviderStatsSummary(BaseModel):
    average_rating: Optional[float] = None
    reviews_count: int
    completed_projects_count: int
    active_projects_count: int


class DetailedProjectApplicationListItem(BaseModel):
    application: ApplicationResponse
    provider: ProviderUserSummary
    provider_profile: ProviderProfileSummary
    provider_stats: ProviderStatsSummary


class DetailedProjectApplicationsListResponse(BaseModel):
    project_id: int
    total: int
    items: List[DetailedProjectApplicationListItem]