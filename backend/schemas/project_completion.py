from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CompletionRequestCreate(BaseModel):
    provider_message: Optional[str] = Field(
        default=None,
        max_length=3000,
        description="Optional message from provider when requesting completion",
    )


class CompletionRequestDecision(BaseModel):
    customer_message: Optional[str] = Field(
        default=None,
        max_length=3000,
        description="Optional message from customer when approving or reopening",
    )


class CompletionRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    provider_id: int
    customer_id: int
    status: str
    provider_message: Optional[str] = None
    customer_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None