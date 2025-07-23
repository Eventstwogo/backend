from datetime import datetime
import re
from typing import List

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from utils.email_validators import EmailValidator
from utils.validators import (
    normalize_whitespace,
    validate_length_range,
)


class VendorRegisterRequest(BaseModel):
    
    email: EmailStr = Field(
        ...,
        title="Email Address",
        description="Valid email address for the vendor.",
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=12,
        title="Password",
        description="Secure password for the vendor. Must be exactly 8-12 characters long.",
    )

   

    @model_validator(mode="before")
    @classmethod
    def validate_fields(cls, values):
        
        if not values.get("email"):
            raise ValueError("Email is required.")
        if not values.get("password"):
            raise ValueError("Password is required.")
       
        return values

    # @field_validator("username")
    # @classmethod
    # def validate_username(cls, v):
    #     v = normalize_whitespace(v)
    #     if not v:
    #         raise ValueError("Username cannot be empty.")
    #     if not is_valid_username(v, allow_spaces=True, allow_hyphens=True):
    #         raise ValueError(
    #             "Username can only contain letters, numbers, spaces, and hyphens."
    #         )
    #     if not validate_length_range(v, 4, 32):
    #         raise ValueError("Username must be 4-32 characters long.")
    #     if contains_xss(v):
    #         raise ValueError("Username contains potentially malicious content.")
    #     if has_excessive_repetition(v, max_repeats=3):
    #         raise ValueError("Username contains excessive repeated characters.")
    #     if len(v) < 3 or not all(c.isalpha() for c in v[:3]):
    #         raise ValueError(
    #             "First three characters of username must be letters."
    #         )
    #     return v

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
    
    # @field_validator("category")
    # @classmethod
    # def validate_category(cls, v):
    #     v = normalize_whitespace(v)
    #     if not v:
    #         raise ValueError("Category cannot be empty.")
    #     # Ensure category is exactly 6 characters long
    #     if not validate_length_range(v, 6, 6):
    #         raise ValueError("Category must be exactly 6 characters long.")
    #     return v


class VendorRegisterResponse(BaseModel):
    signup_id: str
    email: EmailStr
    


class VendorUser(BaseModel):
    user_id: str
    email: EmailStr
    password: str
    created_at: datetime
    is_active: bool = True


class VendorUpdateRequest(BaseModel):
    email: EmailStr | None = Field(
        None, title="Email Address", description="Updated email address."
    )
    password: str | None = Field(
        None,
        min_length=8,
        max_length=12,
        title="Password",
        description="Updated password (must be 8-12 characters).",
    )

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        v = normalize_whitespace(v)
        EmailValidator.validate(str(v))
        return v.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        v = normalize_whitespace(v)
        if not validate_length_range(v, 8, 12):
            raise ValueError("Password must be exactly 8-12 characters long.")
        return v


class PaginatedVendorListResponse(BaseModel):
    total: int
    page: int
    per_page: int
    vendors: List[VendorUser]
