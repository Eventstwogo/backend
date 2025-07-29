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


# User Registration Schemas
class UserRegisterRequest(BaseModel):
    """Schema for user registration request."""
    
    first_name: str = Field(
        ...,
        min_length=2,
        max_length=50,
        title="First Name",
        description="User's first name (2-50 characters).",
    )
    last_name: str = Field(
        ...,
        min_length=2,
        max_length=50,
        title="Last Name",
        description="User's last name (2-50 characters).",
    )

    username: str = Field(
        ...,
        min_length=4,
        max_length=50,
        title="Username",
        description="Unique username (4-50 characters).",
    )

    email: EmailStr = Field(
        ...,
        title="Email Address",
        description="Valid email address for the user.",
    )
    phone_number: str = Field(
        ...,
        min_length=10,
        max_length=20,
        title="Phone Number",
        description="User's phone number (10-20 characters).",
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=12,
        title="Password",
        description="Secure password (8-12 characters with uppercase, lowercase, digit, and special character).",
    )

    @model_validator(mode="before")
    @classmethod
    def validate_fields(cls, values):
        """Validate required fields."""
        required_fields = ["first_name", "last_name", "username", "email", "phone_number", "password"]
        for field in required_fields:
            if not values.get(field):
                raise ValueError(f"{field.replace('_', ' ').title()} is required.")
        return values

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_names(cls, v):
        """Validate first and last names."""
        v = normalize_whitespace(v)
        if not v:
            raise ValueError("Name cannot be empty.")
        if not validate_length_range(v, 2, 50):
            raise ValueError("Name must be 2-50 characters long.")
        if not v.replace(" ", "").replace("-", "").isalpha():
            raise ValueError("Name can only contain letters, spaces, and hyphens.")
        return v.title()

    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        """Validate username."""
        v = normalize_whitespace(v)
        if not v:
            raise ValueError("Username cannot be empty.")
        if not validate_length_range(v, 4, 50):
            raise ValueError("Username must be 4-50 characters long.")
        if not re.match(r"^[a-zA-Z0-9_. ]+$", v):
            raise ValueError("Username can only contain letters, numbers, underscores, dots, hyphens, and spaces.")
        return v.lower()

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        """Validate email address."""
        v = normalize_whitespace(v)
        if not v:
            raise ValueError("Email cannot be empty.")
        EmailValidator.validate(str(v))
        return v.lower()

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v):
        """Validate phone number."""
        v = normalize_whitespace(v)
        if not v:
            raise ValueError("Phone number cannot be empty.")
        # Remove common phone number formatting
        cleaned_phone = re.sub(r'[^\d+]', '', v)
        if not validate_length_range(cleaned_phone, 10, 20):
            raise ValueError("Phone number must be 10-20 digits long.")
        if not re.match(r'^\+?[\d]+$', cleaned_phone):
            raise ValueError("Phone number can only contain digits and optional leading +.")
        return cleaned_phone

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        """Validate password strength."""
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


class UserRegisterResponse(BaseModel):
    """Schema for user registration response."""
    
    user_id: str = Field(
        ...,
        title="User ID",
        description="Unique identifier for the registered user.",
    )
    email: EmailStr = Field(
        ...,
        title="Email Address",
        description="Email address of the registered user.",
    )


class UserInfo(BaseModel):
    """Schema for user information."""
    
    user_id: str
    username: str
    first_name: str
    last_name: str
    email: EmailStr
    phone_number: str | None
    login_status: int
    successful_logins: int
    failed_logins: int
    last_login: datetime | None
    account_locked_at: datetime | None
    created_at: datetime
    is_active: bool


# User Login Schemas
class UserLoginRequest(BaseModel):
    """Schema for user login request."""
    
    email: EmailStr = Field(
        ...,
        title="Email Address",
        description="User's email address for login.",
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=12,
        title="Password",
        description="User's password for login.",
    )

    @model_validator(mode="before")
    @classmethod
    def validate_fields(cls, values):
        """Validate required fields."""
        if not values.get("email"):
            raise ValueError("Email is required.")
        if not values.get("password"):
            raise ValueError("Password is required.")
        return values

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        """Validate email address."""
        v = normalize_whitespace(v)
        if not v:
            raise ValueError("Email cannot be empty.")
        EmailValidator.validate(str(v))
        return v.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        """Validate password."""
        if not v:
            raise ValueError("Password cannot be empty.")
        return v


class UserLoginResponse(BaseModel):
    """Schema for user login response."""
    
    message: str = Field(
        ...,
        title="Message",
        description="Login success message.",
    )
    user_id: str = Field(
        ...,
        title="User ID",
        description="Unique identifier for the logged-in user.",
    )


# User Verification Schemas
class UserVerificationRequest(BaseModel):
    """Schema for user email verification request."""
    
    email: EmailStr = Field(
        ...,
        title="Email Address",
        description="User's email address for verification.",
    )
    token: str = Field(
        ...,
        min_length=1,
        title="Verification Token",
        description="Email verification token.",
    )

    @model_validator(mode="before")
    @classmethod
    def validate_fields(cls, values):
        """Validate required fields."""
        if not values.get("email"):
            raise ValueError("Email is required.")
        if not values.get("token"):
            raise ValueError("Verification token is required.")
        return values

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        """Validate email address."""
        v = normalize_whitespace(v)
        if not v:
            raise ValueError("Email cannot be empty.")
        EmailValidator.validate(str(v))
        return v.lower()

    @field_validator("token")
    @classmethod
    def validate_token(cls, v):
        """Validate verification token."""
        v = normalize_whitespace(v)
        if not v:
            raise ValueError("Verification token cannot be empty.")
        return v


class UserVerificationResponse(BaseModel):
    """Schema for user email verification response."""
    
    message: str = Field(
        ...,
        title="Message",
        description="Verification success message.",
    )
    user_id: str = Field(
        ...,
        title="User ID",
        description="Unique identifier for the verified user.",
    )


# User GET Routes Schemas
class BasicUserResponse(BaseModel):
    """Schema for basic user information response."""
    
    user_id: str = Field(
        ...,
        title="User ID",
        description="Unique identifier for the user.",
    )
    username: str = Field(
        ...,
        title="Username",
        description="User's username.",
    )
    first_name: str = Field(
        ...,
        title="First Name",
        description="User's first name.",
    )
    last_name: str = Field(
        ...,
        title="Last Name", 
        description="User's last name.",
    )
    email: str = Field(
        ...,
        title="Email Address",
        description="User's email address.",
    )
    phone_number: str | None = Field(
        None,
        title="Phone Number",
        description="User's phone number.",
    )


class UserDetailResponse(BaseModel):
    """Schema for single user detail response."""
    
    user_id: str = Field(
        ...,
        title="User ID",
        description="Unique identifier for the user.",
    )
    username: str = Field(
        ...,
        title="Username",
        description="User's username.",
    )
    first_name: str = Field(
        ...,
        title="First Name",
        description="User's first name.",
    )
    last_name: str = Field(
        ...,
        title="Last Name", 
        description="User's last name.",
    )
    email: str = Field(
        ...,
        title="Email Address",
        description="User's email address.",
    )
    phone_number: str | None = Field(
        None,
        title="Phone Number",
        description="User's phone number.",
    )
    login_status: int = Field(
        ...,
        title="Login Status",
        description="User's login status (-1: unverified, 0: active, 1: locked).",
    )
    successful_logins: int = Field(
        ...,
        title="Successful Logins",
        description="Number of successful logins.",
    )
    failed_logins: int = Field(
        ...,
        title="Failed Logins",
        description="Number of failed login attempts.",
    )
    last_login: datetime | None = Field(
        None,
        title="Last Login",
        description="Last login timestamp.",
    )
    account_locked_at: datetime | None = Field(
        None,
        title="Account Locked At",
        description="Account lock timestamp.",
    )
    created_at: datetime = Field(
        ...,
        title="Created At",
        description="Account creation timestamp.",
    )
    is_active: bool = Field(
        ...,
        title="Is Active",
        description="Whether the account is active.",
    )


class BasicUsersListResponse(BaseModel):
    """Schema for basic users list response."""
    
    users: List[BasicUserResponse] = Field(
        ...,
        title="Users",
        description="List of users with basic information.",
    )
    total_count: int = Field(
        ...,
        title="Total Count",
        description="Total number of users.",
    )


class UsersListResponse(BaseModel):
    """Schema for detailed users list response."""
    
    users: List[UserDetailResponse] = Field(
        ...,
        title="Users",
        description="List of users.",
    )
    total_count: int = Field(
        ...,
        title="Total Count",
        description="Total number of users.",
    )


# User Password Reset Schemas
class UserForgotPasswordRequest(BaseModel):
    """Schema for user forgot password request."""
    
    email: EmailStr = Field(
        ...,
        title="Email Address",
        description="User's email address for password reset.",
    )

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        """Validate email address."""
        v = normalize_whitespace(v)
        if not v:
            raise ValueError("Email cannot be empty.")
        EmailValidator.validate(str(v))
        return v.lower()


class UserForgotPasswordResponse(BaseModel):
    """Schema for user forgot password response."""
    
    message: str = Field(
        ...,
        title="Message",
        description="Password reset request confirmation message.",
    )


class UserResetPasswordRequest(BaseModel):
    """Schema for user reset password with token request."""
    
    email: EmailStr = Field(
        ...,
        title="Email Address",
        description="User's email address.",
    )
    token: str = Field(
        ...,
        min_length=1,
        title="Reset Token",
        description="Password reset token received via email.",
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=12,
        title="New Password",
        description="New password (8-12 characters with uppercase, lowercase, digit, and special character).",
    )

    @model_validator(mode="before")
    @classmethod
    def validate_fields(cls, values):
        """Validate required fields."""
        required_fields = ["email", "token", "new_password"]
        for field in required_fields:
            if not values.get(field):
                raise ValueError(f"{field.replace('_', ' ').title()} is required.")
        return values

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        """Validate email address."""
        v = normalize_whitespace(v)
        if not v:
            raise ValueError("Email cannot be empty.")
        EmailValidator.validate(str(v))
        return v.lower()

    @field_validator("token")
    @classmethod
    def validate_token(cls, v):
        """Validate reset token."""
        v = normalize_whitespace(v)
        if not v:
            raise ValueError("Reset token cannot be empty.")
        return v

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v):
        """Validate password strength."""
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


class UserResetPasswordResponse(BaseModel):
    """Schema for user reset password response."""
    
    message: str = Field(
        ...,
        title="Message",
        description="Password reset confirmation message.",
    )
