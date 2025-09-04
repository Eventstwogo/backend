import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_serializer, field_validator

from utils.file_uploads import get_media_url
from utils.security_validators import contains_xss
from utils.validators import normalize_whitespace, validate_length_range

TITLE_REGEX = re.compile(
    r"^(?=.*[A-Za-z0-9])[A-Za-z0-9\s\-\.,'!&()%]{1,255}$", re.UNICODE
)


class AdvertisementResponse(BaseModel):
    """Response model for advertisement data."""

    ad_id: str = Field(
        ...,
        title="Advertisement ID",
        description="Unique identifier for the advertisement.",
    )
    title: str = Field(
        ...,
        title="Title",
        description="Advertisement title.",
    )
    banner: str = Field(
        ...,
        title="Banner",
        description="Full URL path to the advertisement banner image.",
    )
    target_url: Optional[str] = Field(
        None,
        title="Target URL",
        description="URL that the advertisement links to.",
    )
    ad_status: bool = Field(
        ...,
        title="Advertisement Status",
        description="Status of the advertisement (active/inactive).",
    )
    created_at: datetime = Field(
        ...,
        title="Created At",
        description="Timestamp when the advertisement was created.",
    )
    updated_at: Optional[datetime] = Field(
        None,
        title="Updated At",
        description="Timestamp when the advertisement was last updated.",
    )

    @field_serializer("banner")
    def serialize_banner(self, value: str, _info) -> str:
        """Convert relative banner path to full media URL."""
        return get_media_url(value) or ""

    class Config:
        from_attributes = True


# Validation functions for form data
def validate_title_form(title: str) -> str:
    """Validate title from form data."""
    if not title:
        raise ValueError("Title is required.")

    title = normalize_whitespace(title)
    if not title:
        raise ValueError("Title cannot be empty.")

    if not TITLE_REGEX.match(title):
        raise ValueError(
            "Title can only contain letters, numbers, spaces, and basic punctuation, "
            "and must include at least one letter or number."
        )

    # Prevent all-digits input
    if title.isdigit():
        raise ValueError("Title cannot consist of only numbers.")

    if not validate_length_range(title, 1, 255):
        raise ValueError("Title must be 1-255 characters long.")

    if contains_xss(title):
        raise ValueError("Title contains potentially malicious content.")

    return title


def validate_target_url_form(target_url: Optional[str]) -> Optional[str]:
    """Validate target URL from form data."""
    if not target_url:
        return None

    target_url = normalize_whitespace(target_url)
    if not target_url:
        return None

    if not validate_length_range(target_url, 1, 255):
        raise ValueError("Target URL must be 1-255 characters long.")

    if contains_xss(target_url):
        raise ValueError("Target URL contains potentially malicious content.")

    # Basic URL validation
    if not (
        target_url.startswith("http://") or target_url.startswith("https://")
    ):
        raise ValueError("Target URL must start with http:// or https://")

    return target_url
