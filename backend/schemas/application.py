from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from backend.schemas.profile import ProviderProfileResponse


class ApplicationCreate(BaseModel):
    project_id: int
    cover_letter: Optional[str] = None
    proposed_budget: Optional[int] = None
    estimated_timeline_days: Optional[int] = None


class ApplicationResponse(BaseModel):
    id: int
    project_id: int
    applicant_user_id: int
    application_type: str
    cover_letter: Optional[str] = None
    proposed_budget: Optional[int] = None
    estimated_timeline_days: Optional[int] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class ApplicationStatusUpdate(BaseModel):
    status: str


# 🔥 НОВИЙ СХЕМА ДЛЯ DETAILED VIEW
class ApplicationWithProviderProfile(BaseModel):
    application: ApplicationResponse
    provider_profile: Optional[ProviderProfileResponse] = None