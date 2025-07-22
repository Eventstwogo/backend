from pydantic import BaseModel, constr
from typing import Optional
from datetime import datetime


class CreateIndustry(BaseModel):
    industry_name: Optional[str]
    industry_slug: str


class IndustryUpdate(BaseModel):
    industry_name: Optional[str] = None
    industry_slug: Optional[str] = None


class IndustryDetails(BaseModel):
    industry_id: str
    industry_name: str
    industry_slug: str
    is_active: bool
    timestamp: datetime

    class Config:
        orm_mode = True


class VendorCategoryRequest(BaseModel):
    vendor_ref_id: str
    category_id: str
    subcategory_id: str