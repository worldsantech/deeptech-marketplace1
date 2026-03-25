from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CustomerProfileUpdate(BaseModel):
    company_name: Optional[str] = None
    company_description: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    website: Optional[str] = None


class CustomerProfileResponse(BaseModel):
    id: int
    user_id: int
    company_name: Optional[str] = None
    company_description: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    website: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProviderProfileUpdate(BaseModel):
    provider_type: Optional[str] = None
    headline: Optional[str] = None
    bio: Optional[str] = None
    skills: Optional[str] = None
    industries: Optional[str] = None
    years_of_experience: Optional[int] = None
    country: Optional[str] = None
    city: Optional[str] = None
    availability: Optional[str] = None
    rate_type: Optional[str] = None
    rate_amount: Optional[int] = None
    currency: Optional[str] = None
    website: Optional[str] = None


class ProviderProfileResponse(BaseModel):
    id: int
    user_id: int
    provider_type: Optional[str] = None
    headline: Optional[str] = None
    bio: Optional[str] = None
    skills: Optional[str] = None
    industries: Optional[str] = None
    years_of_experience: Optional[int] = None
    country: Optional[str] = None
    city: Optional[str] = None
    availability: Optional[str] = None
    rate_type: Optional[str] = None
    rate_amount: Optional[int] = None
    currency: Optional[str] = None
    website: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MyProfileResponse(BaseModel):
    role: str
    user_id: int
    email: str
    full_name: str
    customer_profile: Optional[CustomerProfileResponse] = None
    provider_profile: Optional[ProviderProfileResponse] = None