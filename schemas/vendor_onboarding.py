from pydantic import BaseModel, EmailStr, Field, HttpUrl, field_validator
from enum import Enum
import re

class PurposeEnum(str, Enum):
    feedback = "Collect feedback"
    roadmap = "Prioritize my roadmap"
    announcements = "Product announcements"
    sales = "Increase Sales"
    awareness = "Brand Awareness"
    reach = "Expand Reach"
    efficiency = "Operational Efficiency"
    other = "Other"

class PaymentPreferenceEnum(str, Enum):
    product_listing = "Payments for Product Listing"
    orders = "Payments for Orders"

class OnboardingRequest(BaseModel):
    profile_ref_id: str = Field(..., min_length=1, max_length=6)
    purpose: list[PurposeEnum]
    payment_preference: list[PaymentPreferenceEnum]
    store_name: str = Field(..., min_length=3, max_length=100)
    store_url: HttpUrl
    location: str = Field(..., min_length=2, max_length=100)
    industry_id: str = Field(..., min_length=6, max_length=6)  # must be exactly 6 characters

    @field_validator('purpose')
    @classmethod
    def validate_purpose(cls, v):
        if not v:
            raise ValueError("Purpose cannot be empty")
        return v

    @field_validator('payment_preference')
    @classmethod
    def validate_payment(cls, v):
        if not v:
            raise ValueError("Payment preference cannot be empty")
        return v

    @field_validator('store_name')
    @classmethod
    def validate_store_name(cls, v):
        if not re.match(r"^[a-zA-Z _\-']+$", v):
            raise ValueError("Store name contains invalid characters. Numbers are not allowed.")
        return v

    @field_validator('location')
    @classmethod
    def validate_location(cls, v):
        if not re.match(r'^[a-zA-Z0-9 ,]+$', v):
            raise ValueError("Location contains invalid characters")
        return v


class ResendVerificationRequest(BaseModel):
    email: EmailStr = Field(
        ...,
        title="Email Address",
        description="Email address to resend verification to."
    )
 
# Schema for store name availability check
class StoreNameCheckRequest(BaseModel):
    store_name: str

class StoreNameCheckResponse(BaseModel):
    status_code: int
    message: str