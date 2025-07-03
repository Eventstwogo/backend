from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ConfigOut(BaseModel):
    id: int = Field(
        default=...,
        title="Configuration ID",
        description="The unique identifier of the configuration record.",
        examples=[1],
    )
    default_password: str = Field(
        default=...,
        title="Default Password",
        description="The default plain text password (only for reference).",
        examples=["Welcome@123"],
    )
    default_password_hash: str = Field(
        default=...,
        title="Password Hash",
        description="Hashed version of the default password.",
        examples=["$2b$12$eX4Qx...HashedTextHere"],
    )
    logo_url: Optional[str] = Field(
        default=None,
        title="Logo URL",
        description="URL to the uploaded logo image.",
        examples=["config/logo/abcd1234.png"],
    )
    global_180_day_flag: bool = Field(
        default=...,
        title="Global 180-Day Flag",
        description="Indicates if the 180-day password reset rule is enabled.",
        examples=[True],
    )
    created_at: datetime = Field(
        default=...,
        title="Created At",
        description="Timestamp when the configuration was created.",
        examples=["2025-06-23T10:00:00+00:00"],
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        title="Updated At",
        description="Timestamp when the configuration was last updated.",
        examples=["2025-06-23T12:30:00+00:00"],
    )

    model_config = ConfigDict(from_attributes=True)
