from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class ApplicationCreate(BaseModel):
    project_id: int
    cover_letter: str
    proposed_budget: int
    estimated_timeline_days: int


class ApplicationStatusUpdate(BaseModel):
    status: str


class ApplicationResponse(BaseModel):
    id: int
    project_id: int
    applicant_user_id: int
    application_type: str
    cover_letter: str
    proposed_budget: int
    estimated_timeline_days: int
    status: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProjectSelectionResponse(BaseModel):
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

    class Config:
        from_attributes = True


class ApplicationStatusUpdateResponse(BaseModel):
    application: ApplicationResponse
    project: ProjectSelectionResponse
    auto_rejected_applications: List[ApplicationResponse]