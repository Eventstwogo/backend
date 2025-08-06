"""
Vendor password management schemas.
"""

import re
from pydantic import BaseModel, Field, field_validator

class VendorForgotPasswordRequest(BaseModel):
    """Schema for vendor forgot password request."""
    email: str = Field(..., description="Vendor email address")


class VendorForgotPasswordResponse(BaseModel):
    """Schema for vendor forgot password response."""
    message: str = Field(..., description="Response message")


class VendorResetPasswordRequest(BaseModel):
    """Schema for vendor reset password with token request."""
    email: str = Field(..., description="Vendor email address")
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(
        ..., 
        min_length=8, 
        max_length=12,
        description="New password (8-12 characters)"
    )

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if len(v) > 12:
            raise ValueError("Password must be at most 12 characters long.")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must include at least one uppercase letter.")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must include at least one lowercase letter.")
        if not re.search(r"\d", v):
            raise ValueError("Password must include at least one digit.")
        if not re.search(r"[^\w\s]", v):
            raise ValueError("Password must include at least one special character.")
        return v


class VendorResetPasswordResponse(BaseModel):
    """Schema for vendor reset password response."""
    message: str = Field(..., description="Response message")


class VendorChangePasswordRequest(BaseModel):
    """Schema for vendor change password request."""
    user_id: str = Field(..., description="Vendor user ID")
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(
        ..., 
        min_length=8, 
        max_length=12,
        description="New password (8-12 characters)"
    )

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if len(v) > 12:
            raise ValueError("Password must be at most 12 characters long.")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must include at least one uppercase letter.")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must include at least one lowercase letter.")
        if not re.search(r"\d", v):
            raise ValueError("Password must include at least one digit.")
        if not re.search(r"[^\w\s]", v):
            raise ValueError("Password must include at least one special character.")
        return v


class VendorChangePasswordResponse(BaseModel):
    """Schema for vendor change password response."""
    message: str = Field(..., description="Response message")


class VendorChangeInitialPasswordRequest(BaseModel):
    """Schema for vendor change initial password request."""
    new_password: str = Field(
        ..., 
        min_length=8, 
        max_length=12,
        description="New password (8-12 characters)"
    )

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if len(v) > 12:
            raise ValueError("Password must be at most 12 characters long.")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must include at least one uppercase letter.")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must include at least one lowercase letter.")
        if not re.search(r"\d", v):
            raise ValueError("Password must include at least one digit.")
        if not re.search(r"[^\w\s]", v):
            raise ValueError("Password must include at least one special character.")
        return v


class VendorChangeInitialPasswordResponse(BaseModel):
    """Schema for vendor change initial password response."""
    message: str = Field(..., description="Response message")