from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from utils.security_validators import validate_strict_input
from utils.validators import (
    is_valid_name,
    normalize_whitespace,
    validate_length_range,
)


class CreatePermission(BaseModel):
    permission_name: str = Field(
        ..., title="Permission Name", description="The name of the permission."
    )

    @field_validator("permission_name", mode="before")
    @classmethod
    def validate_permission_name(cls, value: Any) -> str:
        if value is None:
            raise ValueError("Permission name is required.")
        value = normalize_whitespace(value)

        if not value:
            raise ValueError("Permission name cannot be empty.")

        if not is_valid_name(value):
            raise ValueError(
                "Permission name must contain only letters, spaces, or hyphens."
            )

        if not validate_length_range(value, 3, 50):
            raise ValueError(
                "Permission name must be between 3 and 50 characters."
            )

        validate_strict_input("permission_name", value)

        return value.upper()


class PermissionDetails(BaseModel):
    permission_id: str = Field(
        ...,
        title="Permission ID",
        description="Unique identifier of the permission.",
    )
    permission_name: str = Field(
        ..., title="Permission Name", description="Name of the permission."
    )
    permission_status: bool = Field(
        ...,
        title="Permission Status",
        description="Indicates whether permission is active.",
    )


class PermissionUpdate(BaseModel):
    permission_name: Optional[str] = Field(
        None,
        title="Permission Name",
        description="Updated name of the permission.",
    )

    @field_validator("permission_name", mode="before")
    @classmethod
    def validate_permission_name(cls, value: Any) -> Optional[str]:
        if value is not None:
            value = normalize_whitespace(value)

            if not value:
                raise ValueError("Permission name cannot be empty.")

            if not is_valid_name(value):
                raise ValueError(
                    "Permission name must contain only letters, spaces, or hyphens."
                )

            if not validate_length_range(value, 3, 50):
                raise ValueError(
                    "Permission name must be between 3 and 50 characters."
                )

            validate_strict_input("permission_name", value)

            return value.upper()
        return value


class CreateRolePermission(BaseModel):
    role_id: str = Field(..., title="Role ID", description="ID of the role.")
    permission_id: str = Field(
        ...,
        title="Permission ID",
        description="ID of the permission to be assigned.",
    )


class RolePermissionDetails(BaseModel):
    id: int = Field(
        ...,
        title="Record ID",
        description="Unique identifier for the role-permission mapping.",
    )
    role_id: str = Field(..., title="Role ID", description="ID of the role.")
    permission_id: str = Field(
        ..., title="Permission ID", description="ID of the permission."
    )


class RolePermissionUpdate(BaseModel):
    role_id: str = Field(..., title="Role ID", description="Updated role ID.")
    permission_id: str = Field(
        ..., title="Permission ID", description="Updated permission ID."
    )


class CreateRole(BaseModel):
    role_name: str = Field(
        ..., title="Role Name", description="The name of the role."
    )

    @field_validator("role_name", mode="before")
    @classmethod
    def validate_role_name(cls, value: Any) -> str:
        if value is None:
            raise ValueError("Role name is required.")

        value = normalize_whitespace(value)

        if not value:
            raise ValueError("Role name cannot be empty.")

        if not is_valid_name(value):
            raise ValueError(
                "Role name must contain only letters and spaces or hyphens."
            )

        if not validate_length_range(value, 3, 50):
            raise ValueError(
                "Role name must be between 3 and 50 characters long."
            )

        validate_strict_input("role_name", value)

        return value.upper()


class RoleDetails(BaseModel):
    role_id: str = Field(
        ..., title="Role ID", description="Unique identifier of the role."
    )
    role_name: str = Field(
        ..., title="Role Name", description="Name of the role."
    )
    role_status: Optional[bool] = Field(
        None,
        title="Role Status",
        description="Indicates whether role is active.",
    )


class RoleUpdate(BaseModel):
    role_name: Optional[str] = Field(
        None, title="Role Name", description="Updated name of the role."
    )

    @field_validator("role_name", mode="before")
    @classmethod
    def validate_role_name(cls, value: Any) -> Optional[str]:
        if value is not None:
            value = normalize_whitespace(value)

            if not value:
                raise ValueError("Role name cannot be empty.")

            if not is_valid_name(value):
                raise ValueError(
                    "Role name must contain only letters, spaces, or hyphens."
                )

            if not validate_length_range(value, 3, 50):
                raise ValueError(
                    "Role name must be between 3 and 50 characters."
                )

            validate_strict_input("role_name", value)

            return value.upper()
        return value
