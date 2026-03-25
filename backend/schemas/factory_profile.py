from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class FactoryProfileCreate(BaseModel):
    user_id: int
    company_name: str
    description: Optional[str] = None
    capabilities: Optional[str] = None
    min_order_value: Optional[int] = None
    country: Optional[str] = None
    city: Optional[str] = None
    website_url: Optional[str] = None


class FactoryProfileResponse(BaseModel):
    id: int
    user_id: int
    company_name: str
    description: Optional[str] = None
    capabilities: Optional[str] = None
    min_order_value: Optional[int] = None
    country: Optional[str] = None
    city: Optional[str] = None
    website_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True