from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime
from utils.email_validators import EmailValidator
from utils.validators import normalize_whitespace


class VendorEmployeeCreateRequest(BaseModel):
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        title="Username",
        description="Unique username for the vendor employee.",
    )
    email: EmailStr = Field(
        ...,
        title="Email Address",
        description="Valid email address for the vendor employee.",
    )
    role_id: str = Field(
        ...,
        min_length=6,
        max_length=6,
        title="Role ID",
        description="6-character role ID for the vendor employee.",
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        import re
        
        v = normalize_whitespace(v)
        if not v:
            raise ValueError("Username cannot be empty.")
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters long.")
        if len(v) > 50:
            raise ValueError("Username must be at most 50 characters long.")
        
        # Check if first 3 characters are letters
        if len(v) >= 3 and not v[:3].replace(" ", "").isalpha():
            raise ValueError("First 3 characters must be letters.")
        
        # Check if username contains only numbers (no letters)
        if v.replace(" ", "").isdigit():
            raise ValueError("Username cannot contain only numbers.")
        
        # Check for special characters (allow only letters, numbers, and spaces)
        if not re.match(r"^[a-zA-Z0-9\s]+$", v):
            raise ValueError("Username can only contain letters, numbers, and spaces.")
        
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        v = normalize_whitespace(v)
        if not v:
            raise ValueError("Email cannot be empty.")
        EmailValidator.validate(str(v))
        return v.lower()


class VendorEmployeeCreateResponse(BaseModel):
    user_id: str
    username: str
    email: EmailStr
    password: str
    vendor_ref_id: str
    message: str


class VendorEmployeeUpdateRequest(BaseModel):
    username: Optional[str] = Field(
        None,
        min_length=3,
        max_length=50,
        title="Username",
        description="Unique username for the vendor employee.",
    )
    email: Optional[EmailStr] = Field(
        None,
        title="Email Address",
        description="Valid email address for the vendor employee.",
    )
    role_id: Optional[str] = Field(
        None,
        min_length=6,
        max_length=6,
        title="Role ID",
        description="6-character role ID for the vendor employee.",
    )
    is_active: Optional[bool] = Field(
        None,
        title="Active Status",
        description="Whether the employee account is active.",
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        import re
        
        if v is None:
            return v
        v = normalize_whitespace(v)
        if not v:
            raise ValueError("Username cannot be empty.")
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters long.")
        if len(v) > 50:
            raise ValueError("Username must be at most 50 characters long.")
        
        # Check if first 3 characters are letters
        if len(v) >= 3 and not v[:3].replace(" ", "").isalpha():
            raise ValueError("First 3 characters must be letters.")
        
        # Check if username contains only numbers (no letters)
        if v.replace(" ", "").isdigit():
            raise ValueError("Username cannot contain only numbers.")
        
        # Check for special characters (allow only letters, numbers, and spaces)
        if not re.match(r"^[a-zA-Z0-9\s]+$", v):
            raise ValueError("Username can only contain letters, numbers, and spaces.")
        
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if v is None:
            return v
        v = normalize_whitespace(v)
        if not v:
            raise ValueError("Email cannot be empty.")
        EmailValidator.validate(str(v))
        return v.lower()


class VendorEmployeeResponse(BaseModel):
    user_id: str
    username: str
    email: str
    role_id: Optional[str]
    role_name: Optional[str]
    vendor_ref_id: Optional[str]


class VendorEmployeeListResponse(BaseModel):
    employees: List[VendorEmployeeResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class VendorEmployeeUpdateResponse(BaseModel):
    user_id: str
    username: str
    email: str
    role_id: Optional[str]
    vendor_ref_id: Optional[str]
    is_active: bool
    message: str


class VendorEmployeeDeleteResponse(BaseModel):
    user_id: str
    message: str