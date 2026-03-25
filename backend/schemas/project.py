from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ProjectCreate(BaseModel):
   
    title: str
    description: str
    project_type: str
    budget_min: Optional[int] = None
    budget_max: Optional[int] = None
    currency: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    project_type: Optional[str] = None
    budget_min: Optional[int] = None
    budget_max: Optional[int] = None
    currency: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    status: Optional[str] = None


class ProjectResponse(BaseModel):
    id: int
    client_id: int
    title: str
    description: str
    project_type: str
    status: str
    budget_min: Optional[int] = None
    budget_max: Optional[int] = None
    currency: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    selected_applicant_user_id: Optional[int] = None
    selected_application_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True