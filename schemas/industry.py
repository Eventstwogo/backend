from pydantic import BaseModel, Field, field_validator
from typing import Any, Optional
from datetime import datetime

from utils.security_validators import validate_strict_input
from utils.validators import (
    is_valid_name,
    normalize_whitespace,
    validate_length_range,
)


class CreateIndustry(BaseModel):
    industry_name: str = Field(
        ..., title="Industry Name", description="The name of the industry."
    )
    industry_slug: str = Field(
        ..., title="Industry Slug", description="URL-friendly slug for the industry."
    )
    
    @field_validator("industry_name", mode="before")
    @classmethod
    def validate_industry_name(cls, value: Any) -> str:
        if value is None:
            raise ValueError("Industry name is required.")
        
        value = normalize_whitespace(value)
        
        if not value:
            raise ValueError("Industry name cannot be empty.")
        
        if not is_valid_name(value):
            raise ValueError(
                "Industry name must contain only letters, spaces, or hyphens."
            )
        
        if not validate_length_range(value, 2, 50):
            raise ValueError(
                "Industry name must be between 2 and 50 characters."
            )
        
        validate_strict_input("industry_name", value)
        
        return value.upper()
    
    @field_validator("industry_slug", mode="before")
    @classmethod
    def validate_industry_slug(cls, value: Any) -> str:
        if value is None:
            raise ValueError("Industry slug is required.")
        
        value = normalize_whitespace(value)
        
        if not value:
            raise ValueError("Industry slug cannot be empty.")
        
        if not validate_length_range(value, 2, 50):
            raise ValueError(
                "Industry slug must be between 2 and 50 characters."
            )
        
        validate_strict_input("industry_slug", value)
        
        return value.lower()


class IndustryUpdate(BaseModel):
    industry_name: Optional[str] = Field(
        None, title="Industry Name", description="Updated name of the industry."
    )
    industry_slug: Optional[str] = Field(
        None, title="Industry Slug", description="Updated slug for the industry."
    )
    
    @field_validator("industry_name", mode="before")
    @classmethod
    def validate_industry_name(cls, value: Any) -> Optional[str]:
        if value is not None:
            value = normalize_whitespace(value)
            
            if not value:
                raise ValueError("Industry name cannot be empty.")
            
            if not is_valid_name(value):
                raise ValueError(
                    "Industry name must contain only letters, spaces, or hyphens."
                )
            
            if not validate_length_range(value, 2, 50):
                raise ValueError(
                    "Industry name must be between 2 and 50 characters."
                )
            
            validate_strict_input("industry_name", value)
            
            return value.upper()
        return value
    
    @field_validator("industry_slug", mode="before")
    @classmethod
    def validate_industry_slug(cls, value: Any) -> Optional[str]:
        if value is not None:
            value = normalize_whitespace(value)
            
            if not value:
                raise ValueError("Industry slug cannot be empty.")
            
            if not validate_length_range(value, 2, 50):
                raise ValueError(
                    "Industry slug must be between 2 and 50 characters."
                )
            
            validate_strict_input("industry_slug", value)
            
            return value.lower()
        return value


class IndustryDetails(BaseModel):
    industry_id: str
    industry_name: str
    industry_slug: str
    is_active: bool
    timestamp: datetime

    class Config:
        from_attributes = True


class VendorCategoryRequest(BaseModel):
    vendor_ref_id: str
    category_id: str
    subcategory_id: Optional[str] = None