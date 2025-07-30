from pydantic import BaseModel, Field
from typing import Optional


class VendorActionRequest(BaseModel):
    """Schema for vendor management actions (soft delete, restore, etc.)"""
    user_id: str = Field(..., description="Vendor user ID from ven_login table", min_length=1, max_length=6)


class VendorActionResponse(BaseModel):
    """Schema for vendor management action responses"""
    message: str = Field(..., description="Action result message")
    user_id: Optional[str] = Field(None, description="Vendor user ID")
    status: Optional[str] = Field(None, description="Current vendor status")


class VendorStatusResponse(BaseModel):
    """Schema for vendor status information"""
    user_id: str = Field(..., description="Vendor user ID")
    username: str = Field(..., description="Vendor username")
    email: str = Field(..., description="Vendor email")
    is_active: bool = Field(..., description="Whether vendor is active")
    is_verified: int = Field(..., description="Vendor verification status")
    last_login: Optional[str] = Field(None, description="Last login timestamp")
    created_at: str = Field(..., description="Account creation timestamp")