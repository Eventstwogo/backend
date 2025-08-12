# roles.py (Router)
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse
from core.status_codes import APIResponse, StatusCode
from core.api_response import api_response
from db.models.superadmin import Role
from db.sessions.database import get_db
from schemas.role_perm_schemas import CreateRole, RoleDetails, RoleUpdate
from utils.exception_handlers import exception_handler
from utils.id_generators import generate_digits_lowercase
from utils.validators import is_single_reserved_word

router = APIRouter()


@router.post("/", summary="Create a new role")
@exception_handler
async def create_role(
    role: CreateRole,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    result = await db.execute(
        select(Role).where(Role.role_name == role.role_name)
    )
    existing_role: Role | None = result.scalars().first()

    if existing_role:
        if existing_role.role_status is False:
            return APIResponse.response(
                # status_code=status.HTTP_409_CONFLICT,
                StatusCode.EXISTS,
                message="Role with this name already exists.",
                log_error=True,
            )
        else:
            # Reactivate the soft-deleted role
            existing_role.role_status = False
            existing_role.role_tstamp = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(existing_role)
            return api_response(
                status_code=status.HTTP_200_OK,
                message="Soft-deleted role reactivated successfully.",
                data={"role_id": existing_role.role_id},
            )

    if is_single_reserved_word(role.role_name):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Python reserved words are not allowed in role names.",
        )

    # Create new role if not found at all
    role_id = generate_digits_lowercase()
    new_role = Role(
        role_id=role_id,
        role_name=role.role_name,
        role_status=False,
        role_tstamp=datetime.now(timezone.utc),
    )
    db.add(new_role)
    await db.commit()
    await db.refresh(new_role)

    return api_response(
        status_code=status.HTTP_201_CREATED,
        message="Role created successfully.",
        data={"role_id": new_role.role_id},
    )


@router.get(
    "/", response_model=List[RoleDetails], summary="Get roles by active status"
)
@exception_handler
async def get_roles(
    is_active: Optional[bool] = Query(
        None, description="Filter roles by active status"
    ),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    query = select(Role)

    if is_active is not None:
        query = query.where(Role.role_status == is_active)

    result = await db.execute(query)
    roles = result.scalars().all()

    if not roles:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="No roles found for the given status.",
            log_error=True,
        )

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Roles retrieved successfully.",
        data=roles,
    )


@router.get("/find", summary="Find role by name")
@exception_handler
async def get_role_by_name(
    role_name: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    result = await db.execute(
        select(Role).where(func.upper(Role.role_name) == func.upper(role_name))
    )
    role = result.scalars().first()

    if not role:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Role not found.",
            log_error=True,
        )

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Role found successfully.",
        data={"role_id": role.role_id},
    )


@router.put("/{role_id}", summary="Update a role by ID")
@exception_handler
async def update_role(
    role_id: str,
    update_data: RoleUpdate,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    result = await db.execute(select(Role).where(Role.role_id == role_id))
    role = result.scalars().first()

    if not role:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Role not found.",
            log_error=True,
        )

    if role.role_status:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,    
            message="Cannot update an inactive role."
        )

    if is_single_reserved_word(update_data.role_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Python reserved words are not allowed in role names.",
        )

    if update_data.role_name:
        # Check for duplicate role_name in a different role
        duplicate_check = await db.execute(
            select(Role).where(
                Role.role_name == update_data.role_name,
                Role.role_id != role_id,
            )
        )
        duplicate_role = duplicate_check.scalars().first()

        if duplicate_role:
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="A role with this name already exists.",
                log_error=False,
            )

        role.role_name = update_data.role_name

    await db.commit()
    await db.refresh(role)

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Role updated successfully.",
        data=role,
    )


@router.patch("/status/{role_id}", summary="Update role status")
@exception_handler
async def update_role_status(
    role_id: str,
    role_status: bool = Query(
        False, description="Set role status to true/false"
    ),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    result = await db.execute(select(Role).where(Role.role_id == role_id))
    role = result.scalars().first()

    if not role:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Role not found.",
            log_error=True,
        )

    role.role_status = role_status
    await db.commit()
    await db.refresh(role)

    return api_response(
        status_code=status.HTTP_200_OK,
        message=f"Role status updated to {'Inactive' if role_status else 'Active'}.",
        data=role,
    )


@router.delete("/{role_id}", summary="Delete role by ID (soft or hard)")
@exception_handler
async def delete_role(
    role_id: str,
    hard_delete: bool = Query(
        False, description="Set to true for hard (permanent) deletion"
    ),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    result = await db.execute(select(Role).where(Role.role_id == role_id))
    role = result.scalars().first()

    if not role:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Role not found.",
            log_error=True,
        )

    # Handle already soft-deleted role
    if role.role_status is True:
        if not hard_delete:
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Role is already soft-deleted.",
                log_error=False,
            )
        # Proceed with hard delete
        await db.delete(role)
        await db.commit()
        return api_response(
            status_code=status.HTTP_200_OK,
            message="Role permanently deleted (hard delete).",
        )

    if hard_delete:
        await db.delete(role)
        await db.commit()
        return api_response(
            status_code=status.HTTP_200_OK,
            message="Role permanently deleted (hard delete).",
        )
    else:
        role.role_status = True  # Soft delete
        await db.commit()
        return api_response(
            status_code=status.HTTP_200_OK,
            message="Role soft-deleted successfully.",
        )
