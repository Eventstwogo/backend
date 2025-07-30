

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class VendorBusinessProfileRequest(BaseModel):
    business_profile_id: str = Field(..., min_length=6, max_length=6)
    abn_id: str


class BusinessProfileResponse(BaseModel):
    """Response schema for business profile data"""
    profile_ref_id: str
    profile_details: dict
    business_logo: Optional[str] = None
    payment_preference: Optional[List[str]] = None
    store_name: Optional[str] = None
    store_slug: Optional[str] = None
    store_url: Optional[str] = None
    industry: Optional[str] = None
    location: Optional[str] = None
    ref_number: str
    purpose: dict
    is_approved: int
    timestamp: datetime

    class Config:
        from_attributes = True