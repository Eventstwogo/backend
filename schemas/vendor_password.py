"""
Vendor password management schemas.
"""

from pydantic import BaseModel, Field

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


class VendorChangeInitialPasswordResponse(BaseModel):
    """Schema for vendor change initial password response."""
    message: str = Field(..., description="Response message")