from datetime import datetime
from typing import Optional

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from utils.email_validators import EmailValidator
from utils.format_validators import PasswordValidator
from utils.security_validators import contains_xss
from utils.validators import (
    has_excessive_repetition,
    is_valid_username,
    normalize_whitespace,
    validate_length_range,
)


class AdminUserCreate(BaseModel):
    username: str
    email: EmailStr
    role_id: str

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


class AdminUserLogin(BaseModel):
    email: EmailStr = Field(
        ...,
        title="Email Address",
        description="Registered email address of the admin user.",
    )
    password: str = Field(
        ..., title="Password", description="Account password."
    )

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        v = normalize_whitespace(v)
        if not v:
            raise ValueError("Email cannot be empty.")
        EmailValidator.validate(str(v))
        return v.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        v = normalize_whitespace(v)
        if not v:
            raise ValueError("Password cannot be empty.")
        if contains_xss(v):
            raise ValueError("Password contains potentially malicious content.")
        return v


class AdminUserOut(BaseModel):
    user_id: str = Field(
        ...,
        title="User ID",
        description="Unique identifier for the admin user.",
    )
    role_id: str = Field(
        ..., title="Role ID", description="Role identifier for the admin user."
    )
    username: str = Field(
        ..., title="Username", description="Admin user's username."
    )
    email: EmailStr = Field(
        ..., title="Email Address", description="Admin user's email address."
    )
    profile_picture: Optional[str] = Field(
        None,
        title="Profile Picture",
        description="URL or filename of the admin user's profile picture.",
    )
    last_login: Optional[datetime] = Field(
        None,
        title="Last Login",
        description="Timestamp of the admin user's last login.",
    )

    class Config:
        from_attributes = True


class AdminUserPasswordReset(BaseModel):
    email: EmailStr = Field(
        ...,
        title="Email Address",
        description="Registered email address for password reset.",
    )
    new_password: str = Field(
        ...,
        title="New Password",
        description="New password for the admin user. Must be strong.",
        min_length=8,
    )

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        v = normalize_whitespace(v)
        if not v:
            raise ValueError("Email cannot be empty.")
        EmailValidator.validate(str(v))
        return v.lower()

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        v = normalize_whitespace(v)
        if not v:
            raise ValueError("New password cannot be empty.")
        if contains_xss(v):
            raise ValueError("Password contains potentially malicious content.")
        password_check = PasswordValidator.validate(v)
        if password_check["status_code"] != 200:
            raise ValueError(password_check["message"])
        return v


class AdminUserResponse(BaseModel):
    user_id: str = Field(
        ...,
        title="User ID",
        description="A unique 6-character identifier for the admin user.",
    )
    username: str = Field(
        ..., title="Username", description="The username used for login."
    )
    email: str = Field(
        ...,
        title="Email Address",
        description="The admin user's email address.",
    )
    role_id: str = Field(
        ...,
        title="Role ID",
        description="Identifier linking the user to a specific role.",
    )
    role_name: str = Field(
        ...,
        title="Role Name",
        description="Human-readable name of the assigned role.",
    )
    profile_picture: Optional[str] = Field(
        None,
        title="Profile Picture",
        description="URL or path to the user's profile picture.",
    )
    is_active: bool = Field(
        ...,
        title="Active Status",
        description="Indicates if the account is active (True) or inactive (False).",
    )
    last_login: Optional[datetime] = Field(
        None,
        title="Last Login",
        description="The date and time when the user last logged in.",
    )
    created_at: datetime = Field(
        ...,
        title="Created At",
        description="Timestamp when the user account was created.",
    )

    class Config:
        from_attributes = True


class AdminUserUpdateInput(BaseModel):
    new_username: Optional[str] = None
    new_role_id: Optional[str] = None

    @field_validator("new_username")
    @classmethod
    def validate_username(cls, v):
        if v is None:
            return v
        v = normalize_whitespace(v)
        if not v:
            raise ValueError("Username cannot be empty.")
        if not is_valid_username(v, allow_spaces=True, allow_hyphens=True):
            raise ValueError(
                "Username can only contain letters, numbers, spaces, and hyphens."
            )
        if not validate_length_range(v, 4, 32):
            raise ValueError("Username must be 4–32 characters long.")
        if contains_xss(v):
            raise ValueError("Username contains potentially malicious content.")
        if has_excessive_repetition(v, max_repeats=3):
            raise ValueError("Username contains excessive repeated characters.")
        if len(v) < 3 or not all(c.isalpha() for c in v[:3]):
            raise ValueError(
                "First three characters of username must be letters."
            )
        return v

    @field_validator("new_role_id")
    @classmethod
    def validate_role_id(cls, v):
        if v is None:
            return v
        v = normalize_whitespace(v)
        if not validate_length_range(v, 6, 6):
            raise ValueError("Role ID must be exactly 6 characters long.")
        return v
