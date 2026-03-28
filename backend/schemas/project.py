from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=10)
    country: str = Field(..., min_length=2, max_length=100)
    city: Optional[str] = Field(default=None, max_length=100)
    project_type: str = Field(..., min_length=2, max_length=50)
    budget_min: int = Field(..., ge=0)
    budget_max: int = Field(..., ge=0)
    currency: Optional[str] = Field(default="EUR", min_length=3, max_length=10)
    deadline_days: Optional[int] = Field(default=None, ge=1, le=365)


class ProjectUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=255)
    description: Optional[str] = Field(default=None, min_length=10)
    country: Optional[str] = Field(default=None, min_length=2, max_length=100)
    city: Optional[str] = Field(default=None, max_length=100)
    project_type: Optional[str] = Field(default=None, min_length=2, max_length=50)
    budget_min: Optional[int] = Field(default=None, ge=0)
    budget_max: Optional[int] = Field(default=None, ge=0)
    currency: Optional[str] = Field(default=None, min_length=3, max_length=10)
    deadline_days: Optional[int] = Field(default=None, ge=1, le=365)
    status: Optional[str] = Field(default=None, min_length=2, max_length=50)


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    owner_id: int
    status: str

    country: Optional[str] = None
    city: Optional[str] = None
    project_type: Optional[str] = None

    budget_min: Optional[int] = None
    budget_max: Optional[int] = None
    currency: Optional[str] = None

    deadline_days: Optional[int] = None

    selected_application_id: Optional[int] = None
    selected_applicant_user_id: Optional[int] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None