from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class EngineerProfileCreate(BaseModel):
    user_id: int
    title: str
    bio: Optional[str] = None
    skills: Optional[str] = None
    hourly_rate: Optional[int] = None
    country: Optional[str] = None
    city: Optional[str] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None


class EngineerProfileResponse(BaseModel):
    id: int
    user_id: int
    title: str
    bio: Optional[str] = None
    skills: Optional[str] = None
    hourly_rate: Optional[int] = None
    country: Optional[str] = None
    city: Optional[str] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True