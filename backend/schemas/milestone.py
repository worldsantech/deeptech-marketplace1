from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.attachment import AttachmentResponse


class MilestoneCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=5000)
    amount: Optional[float] = Field(default=None, ge=0)
    due_date: Optional[datetime] = None


class MilestoneUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=5000)
    amount: Optional[float] = Field(default=None, ge=0)
    due_date: Optional[datetime] = None


class MilestoneSubmit(BaseModel):
    provider_note: Optional[str] = Field(default=None, max_length=5000)
    attachment_ids: List[int] = Field(default_factory=list)


class MilestoneDecision(BaseModel):
    customer_note: Optional[str] = Field(default=None, max_length=5000)


class MilestoneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    customer_id: int
    provider_id: int
    title: str
    description: Optional[str] = None
    amount: Optional[float] = None
    due_date: Optional[datetime] = None
    status: str
    provider_note: Optional[str] = None
    customer_note: Optional[str] = None
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    attachments: List[AttachmentResponse] = Field(default_factory=list)