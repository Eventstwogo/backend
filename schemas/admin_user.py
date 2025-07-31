from datetime import datetime
import re
from typing import List, Optional

from fastapi import Form
from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from utils.email_validators import EmailValidator
from utils.security_validators import contains_xss
from utils.validators import (
    has_excessive_repetition,
    is_valid_username,
    normalize_whitespace,
    validate_length_range,
)


class AdminRegisterRequest(BaseModel):
    username: str = Field(
        ...,
        min_length=3,
        max_length=255,
        title="Username",
        description="Unique username for the admin. Must be 4-32 characters, and start with 3 letters. Letters, numbers, spaces, and hyphens are allowed.",
    )
    email: EmailStr = Field(
        ...,
        title="Email Address",
        description="Valid email address for the admin.",
    )
    role_id: str = Field(
        ...,
        min_length=1,
        max_length=6,
        title="Role ID",
        description="The role identifier assigned to the admin. Must be exactly 6 characters long.",
    )

    @model_validator(mode="before")
    @classmethod
    def validate_fields(cls, values):
        if not values.get("username"):
            raise ValueError("Username is required.")
        if not values.get("email"):
            raise ValueError("Email is required.")
        if not values.get("role_id"):
            raise ValueError("Role ID is required.")
        return values

    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        v = normalize_whitespace(v)
        if not v:
            raise ValueError("Username cannot be empty.")
        if not is_valid_username(v, allow_spaces=True, allow_hyphens=True):
            raise ValueError(
                "Username can only contain letters, numbers, spaces, and hyphens."
            )
        if not validate_length_range(v, 4, 32):
            raise ValueError("Username must be 4-32 characters long.")
        if contains_xss(v):
            raise ValueError("Username contains potentially malicious content.")
        if has_excessive_repetition(v, max_repeats=3):
            raise ValueError("Username contains excessive repeated characters.")
        if len(v) < 3 or not all(c.isalpha() for c in v[:3]):
            raise ValueError(
                "First three characters of username must be letters."
            )
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        v = normalize_whitespace(v)
        if not v:
            raise ValueError("Email cannot be empty.")
        # Use your advanced email validator
        EmailValidator.validate(str(v))
        return v.lower()

    @field_validator("role_id")
    @classmethod
    def validate_role_id(cls, v):
        v = normalize_whitespace(v)
        if not v:
            raise ValueError("Role ID cannot be empty.")
        # Ensure role_id is exactly 6 characters long
        if not validate_length_range(v, 6, 6):
            raise ValueError("Role ID must be exactly 6 characters long.")
        return v


class AdminRegisterResponse(BaseModel):
    user_id: str
    email: EmailStr
    username: str
    password: str


class AdminUser(BaseModel):
    user_id: str
    username: str
    email: EmailStr
    role_id: str
    created_at: datetime
    is_active: bool = True


class AdminUpdateRequest(BaseModel):
    email: EmailStr | None = Field(
        None, title="Email Address", description="Updated email address."
    )
    role_id: str | None = Field(
        None,
        min_length=6,
        max_length=6,
        title="Role ID",
        description="Updated role ID (must be 6 characters).",
    )

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        v = normalize_whitespace(v)
        EmailValidator.validate(str(v))
        return v.lower()

    @field_validator("role_id")
    @classmethod
    def validate_role_id(cls, v):
        v = normalize_whitespace(v)
        if not validate_length_range(v, 6, 6):
            raise ValueError("Role ID must be exactly 6 characters long.")
        return v


class PaginatedAdminListResponse(BaseModel):
    total: int
    page: int
    per_page: int
    admins: List[AdminUser]


class AdminLoginRequest(BaseModel):
    email: str = Field(..., description="Username or email (case-insensitive)")
    password: str = Field(..., description="User password")


class AdminUserInfo(BaseModel):
    is_approved: int
    ref_number: str
    industry: str
    onboarding_status: str  

class AdminLoginResponse(BaseModel):
    access_token: str
    message: str
    user: Optional[AdminUserInfo] = None


class UpdatePasswordBody(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8)

class UpdatePasswordResponse(BaseModel):
    message: str    



class AdminResetPassword(BaseModel):
    new_password: str
    confirm_new_password: str


class ForgotPassword(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        v = normalize_whitespace(str(v))
        if not v:
            raise ValueError("Email cannot be empty.")
        EmailValidator.validate(str(v))
        return v.lower()


class ResetPasswordWithToken(BaseModel):
    email: EmailStr
    token: str
    new_password: str = Field(..., min_length=8)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        v = normalize_whitespace(str(v))
        if not v:
            raise ValueError("Email cannot be empty.")
        EmailValidator.validate(str(v))
        return v.lower()

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


class ChangeInitialPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=8, description="New password (minimum 8 characters)")

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


class ChangeInitialPasswordResponse(BaseModel):
    message: str


class AdminCreateRequest(BaseModel):
    username: str = Field(
        ...,
        min_length=3,
        max_length=255,
        title="Username",
        description="Unique username for the admin. Must be 4-32 characters, and start with 3 letters. Letters, numbers, spaces, and hyphens are allowed.",
    )
    email: EmailStr = Field(
        ...,
        title="Email Address",
        description="Valid email address for the admin.",
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        title="Password",
        description="Password for the admin user.",
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        v = normalize_whitespace(v)
        if not v:
            raise ValueError("Username cannot be empty.")
        if not is_valid_username(v, allow_spaces=True, allow_hyphens=True):
            raise ValueError(
                "Username can only contain letters, numbers, spaces, and hyphens."
            )
        if not validate_length_range(v, 4, 32):
            raise ValueError("Username must be 4-32 characters long.")
        if contains_xss(v):
            raise ValueError("Username contains potentially malicious content.")
        if has_excessive_repetition(v, max_repeats=3):
            raise ValueError("Username contains excessive repeated characters.")
        if len(v) < 3 or not all(c.isalpha() for c in v[:3]):
            raise ValueError(
                "First three characters of username must be letters."
            )
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        v = normalize_whitespace(v)
        if not v:
            raise ValueError("Email cannot be empty.")
        # Use your advanced email validator
        EmailValidator.validate(str(v))
        return v.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if not v:
            raise ValueError("Password cannot be empty.")
        
        # Check length
        if not (8 <= len(v) <= 128):
            raise ValueError("Password must be between 8 and 128 characters long.")
        
        # Check for lowercase letter
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter.")
        
        # Check for uppercase letter
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter.")
        
        # Check for digit
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit.")
        
        # Check for special character
        if not any(c in '!@#$%^&*()-_=+[]{}|;:,.<>?/~`' for c in v):
            raise ValueError("Password must contain at least one special character (!@#$%^&*()-_=+[]{}|;:,.<>?/~`).")
        
        return v


class AdminCreateResponse(BaseModel):
    user_id: str
    username: str
    email: EmailStr
    role_id: str
    message: str
    email_sent: bool