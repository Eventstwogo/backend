from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Import QueryStatus from the model to avoid duplication
from db.models.superadmin import QueryStatus
from utils.security_validators import contains_xss
from utils.validators import (
    has_excessive_repetition,
    normalize_whitespace,
    validate_length_range,
)


class ThreadMessage(BaseModel):
    type: Literal["query", "response", "followup"]
    sender_type: Literal["vendor", "admin"]
    user_id: str
    username: str = Field(..., description="Store name for vendors, username for admins")
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("message", mode="before")
    @classmethod
    def normalize_message(cls, v: str) -> str:
        """
        Normalize whitespace before other validations.
        """
        if not isinstance(v, str):
            raise TypeError("Message must be a string.")
        return normalize_whitespace(v)

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        """
        Validate content of the message.
        """
        if not v.strip():
            raise ValueError("Message cannot be empty or just whitespace.")
        if contains_xss(v):
            raise ValueError(
                "Message contains potentially unsafe input (XSS detected)."
            )
        if has_excessive_repetition(v):
            raise ValueError("Message contains excessive repetition.")
        if not validate_length_range(v, min_len=1, max_len=2000):
            raise ValueError("Message length is outside the acceptable range.")
        return v


class CreateQueryRequest(BaseModel):
    user_id: str = Field(..., description="ID of the user asking the question")
    title: str = Field(..., min_length=1, max_length=100)
    category: str = Field(..., min_length=1, max_length=50)
    message: str = Field(..., min_length=1, max_length=2000)

    @field_validator("title", "category", "message", mode="before")
    @classmethod
    def normalize_strings(cls, v: str) -> str:
        """
        Normalize whitespace before other validations.
        """
        if not isinstance(v, str):
            raise TypeError("Field must be a string.")
        return normalize_whitespace(v)

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """
        Validate title content.
        """
        if not v.strip():
            raise ValueError("Title cannot be empty or just whitespace.")
        if contains_xss(v):
            raise ValueError(
                "Title contains potentially unsafe input (XSS detected)."
            )
        if has_excessive_repetition(v):
            raise ValueError("Title contains excessive repetition.")
        if not validate_length_range(v, min_len=1, max_len=100):
            raise ValueError("Title length is outside the acceptable range.")
        return v

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        """
        Validate category content.
        """
        if not v.strip():
            raise ValueError("Category cannot be empty or just whitespace.")
        if contains_xss(v):
            raise ValueError(
                "Category contains potentially unsafe input (XSS detected)."
            )
        if has_excessive_repetition(v):
            raise ValueError("Category contains excessive repetition.")
        if not validate_length_range(v, min_len=1, max_len=50):
            raise ValueError("Category length is outside the acceptable range.")
        return v

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        """
        Validate message content.
        """
        if not v.strip():
            raise ValueError("Message cannot be empty or just whitespace.")
        if contains_xss(v):
            raise ValueError(
                "Message contains potentially unsafe input (XSS detected)."
            )
        if has_excessive_repetition(v):
            raise ValueError("Message contains excessive repetition.")
        if not validate_length_range(v, min_len=1, max_len=2000):
            raise ValueError("Message length is outside the acceptable range.")
        return v


class AddMessageRequest(BaseModel):
    user_id: str = Field(..., description="ID of the user sending the message")
    message: str = Field(..., min_length=1, max_length=2000)
    message_type: Literal["response", "followup"] = "followup"

    @field_validator("message", mode="before")
    @classmethod
    def normalize_message(cls, v: str) -> str:
        """
        Normalize whitespace before other validations.
        """
        if not isinstance(v, str):
            raise TypeError("Message must be a string.")
        return normalize_whitespace(v)

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        """
        Validate message content.
        """
        if not v.strip():
            raise ValueError("Message cannot be empty or just whitespace.")
        if contains_xss(v):
            raise ValueError(
                "Message contains potentially unsafe input (XSS detected)."
            )
        if has_excessive_repetition(v):
            raise ValueError("Message contains excessive repetition.")
        if not validate_length_range(v, min_len=1, max_len=2000):
            raise ValueError("Message length is outside the acceptable range.")
        return v


class UpdateQueryStatusRequest(BaseModel):
    user_id: str = Field(..., description="ID of the user updating the status")
    query_status: QueryStatus
    message: Optional[str] = None

    @field_validator("message", mode="before")
    @classmethod
    def normalize_message(cls, v: Optional[str]) -> Optional[str]:
        """
        Normalize whitespace before other validations.
        """
        if v is None:
            return None
        if not isinstance(v, str):
            raise TypeError("Message must be a string.")
        return normalize_whitespace(v)

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: Optional[str]) -> Optional[str]:
        """
        Validate message content if provided.
        """
        if v is None:
            return None
        if not v.strip():
            raise ValueError(
                "Message cannot be empty or just whitespace if provided."
            )
        if contains_xss(v):
            raise ValueError(
                "Message contains potentially unsafe input (XSS detected)."
            )
        if has_excessive_repetition(v):
            raise ValueError("Message contains excessive repetition.")
        if not validate_length_range(v, min_len=1, max_len=2000):
            raise ValueError("Message length is outside the acceptable range.")
        return v


class QueryResponse(BaseModel):
    id: int
    sender_user_id: str
    receiver_user_id: Optional[str]
    title: str
    category: str
    thread: List[ThreadMessage]
    query_status: QueryStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QueryListResponse(BaseModel):
    id: int
    sender_user_id: str
    receiver_user_id: Optional[str]
    title: str
    category: str
    query_status: QueryStatus
    created_at: datetime
    updated_at: datetime
    last_message: Optional[str] = None
    unread_count: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)


class QueryFilters(BaseModel):
    query_status: Optional[QueryStatus] = None
    category: Optional[str] = None
    sender_user_id: Optional[str] = None
    receiver_user_id: Optional[str] = None
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)


class QueryStatsResponse(BaseModel):
    total_queries: int
    open_queries: int
    in_progress_queries: int
    answered_queries: int
    closed_queries: int
    my_queries: int
    assigned_to_me: int
