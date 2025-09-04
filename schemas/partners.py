from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_serializer, field_validator

from utils.file_uploads import get_media_url
from utils.security_validators import contains_xss
from utils.validators import normalize_whitespace, validate_length_range


class PartnersResponse(BaseModel):
    """Response model for partner data."""

    partner_id: str = Field(
        ...,
        title="Partner ID",
        description="Unique identifier for the partner.",
    )
    logo: str = Field(
        ...,
        title="Logo",
        description="Full URL path to the partner's logo.",
    )
    website_url: str = Field(
        ...,
        title="Website URL",
        description="Partner's website URL.",
    )
    partner_status: bool = Field(
        ...,
        title="Partner Status",
        description="Status of the partner (active/inactive).",
    )
    created_at: datetime = Field(
        ...,
        title="Created At",
        description="Timestamp when the partner was created.",
    )
    updated_at: Optional[datetime] = Field(
        None,
        title="Updated At",
        description="Timestamp when the partner was last updated.",
    )

    @field_serializer("logo")
    def serialize_logo(self, value: str, _info) -> str:
        """Convert relative logo path to full media URL."""
        return get_media_url(value) or ""

    class Config:
        from_attributes = True


class PartnersUpdateRequest(BaseModel):
    """Pydantic model for partner update validation (not used directly in endpoints)."""

    logo: Optional[str] = Field(
        None,
        title="Logo",
        description="URL or path to the partner's logo.",
        max_length=255,
    )
    website_url: Optional[str] = Field(
        None,
        title="Website URL",
        description="Partner's website URL.",
        max_length=255,
    )
    partner_status: Optional[bool] = Field(
        None,
        title="Partner Status",
        description="Status of the partner (active/inactive).",
    )

    @field_validator("logo")
    @classmethod
    def validate_logo(cls, v):
        if v is None:
            return v

        v = normalize_whitespace(v)
        if not v:  # If empty string after normalization, return None
            return None

        if not validate_length_range(v, 1, 255):
            raise ValueError("Logo URL must be 1-255 characters long.")

        if contains_xss(v):
            raise ValueError("Logo URL contains potentially malicious content.")

        return v

    @field_validator("website_url")
    @classmethod
    def validate_website_url(cls, v):
        if v is None:
            return v

        v = normalize_whitespace(v)
        if not v:  # If empty string after normalization, return None
            return None

        if not validate_length_range(v, 1, 255):
            raise ValueError("Website URL must be 1-255 characters long.")

        if contains_xss(v):
            raise ValueError(
                "Website URL contains potentially malicious content."
            )

        # Basic URL validation
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("Website URL must start with http:// or https://")

        return v


# Validation functions for form data
def validate_website_url_form(website_url: str) -> str:
    """Validate website URL from form data."""
    if not website_url:
        raise ValueError("Website URL is required.")

    website_url = normalize_whitespace(website_url)
    if not website_url:
        raise ValueError("Website URL cannot be empty.")

    if not validate_length_range(website_url, 1, 255):
        raise ValueError("Website URL must be 1-255 characters long.")

    if contains_xss(website_url):
        raise ValueError("Website URL contains potentially malicious content.")

    # Basic URL validation
    if not (
        website_url.startswith("http://") or website_url.startswith("https://")
    ):
        raise ValueError("Website URL must start with http:// or https://")

    return website_url
