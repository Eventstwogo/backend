from datetime import datetime
from typing import List

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
