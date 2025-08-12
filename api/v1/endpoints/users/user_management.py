"""
User management endpoints for update, soft delete, restore, and hard delete operations.
"""

from fastapi import APIRouter, Depends, Path, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.api_response import api_response
from db.models.general import User, UserVerification
from db.sessions.database import get_db
from schemas.register import (
    UserUpdateRequest,
    UserUpdateResponse,
    UserDeleteResponse,
    UserRestoreResponse,
)
from services.user_service import (
    get_user_by_id,
)
from utils.exception_handlers import exception_handler
from utils.id_generators import encrypt_data, hash_data
from sqlalchemy import select, delete


router = APIRouter()


@router.put(
    "/{user_id}",
    response_model=UserUpdateResponse,
    status_code=status.HTTP_200_OK,
)
@exception_handler
async def update_user(
    user_id: str = Path(..., description="User ID to update"),
    user_data: UserUpdateRequest = ...,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Update user information.
    
    User can update first name, last name, username, phone number, and email.
    Same validations as registration are applied.
    """
    
    # Check if user exists
    user = await get_user_by_id(db, user_id)
    if not user:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found.",
            log_error=True,
        )
    
    # Check if user is soft deleted
    if user.is_active:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Cannot update a deleted user. Please restore the user first.",
            log_error=True,
        )
    
    # Check if at least one field is provided for update
    update_fields = {
        k: v for k, v in user_data.model_dump().items() 
        if v is not None
    }
    
    if not update_fields:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="At least one field must be provided for update.",
            log_error=True,
        )
    
    # Validate first name and last name are not the same if both are being updated
    if (user_data.first_name and user_data.last_name and 
        user_data.first_name.strip().lower() == user_data.last_name.strip().lower()):
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="First name and last name cannot be the same.",
            log_error=True,
        )
    
    # Check for uniqueness of username, email, and phone if they're being updated
    username_hash = None
    email_hash = None
    phone_number_hash = None
    
    if user_data.username:
        username_hash = hash_data(user_data.username.lower())
        # Check if this username is already taken by another user
        existing_user = await db.execute(
            select(User).where(
                User.username_hash == username_hash,
                User.user_id != user_id
            )
        )
        if existing_user.scalar_one_or_none():
            return api_response(
                status_code=status.HTTP_409_CONFLICT,
                message="Username already exists. Please choose a different username.",
                log_error=True,
            )
    
    if user_data.email:
        email_hash = hash_data(user_data.email.lower())
        # Check if this email is already taken by another user
        existing_user = await db.execute(
            select(User).where(
                User.email_hash == email_hash,
                User.user_id != user_id
            )
        )
        if existing_user.scalar_one_or_none():
            return api_response(
                status_code=status.HTTP_409_CONFLICT,
                message="User with this email already exists.",
                log_error=True,
            )
    
    if user_data.phone_number:
        phone_number_hash = hash_data(user_data.phone_number)
        # Check if this phone number is already taken by another user
        existing_user = await db.execute(
            select(User).where(
                User.phone_number_hash == phone_number_hash,
                User.user_id != user_id
            )
        )
        if existing_user.scalar_one_or_none():
            return api_response(
                status_code=status.HTTP_409_CONFLICT,
                message="User with this phone number already exists.",
                log_error=True,
            )
    
    # Update user fields
    if user_data.first_name:
        user.first_name = encrypt_data(user_data.first_name.title())
    
    if user_data.last_name:
        user.last_name = encrypt_data(user_data.last_name.title())
    
    if user_data.username:
        user.username = encrypt_data(user_data.username.lower())
        user.username_hash = username_hash
    
    if user_data.email:
        user.email = encrypt_data(user_data.email.lower())
        user.email_hash = email_hash
    
    if user_data.phone_number:
        user.phone_number = encrypt_data(user_data.phone_number)
        user.phone_number_hash = phone_number_hash
    
    # Save changes
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return api_response(
        status_code=status.HTTP_200_OK,
        message="User updated successfully.",
        data=UserUpdateResponse(
            user_id=user_id,
            message="User updated successfully.",
        ),
    )


@router.patch(
    "/soft-delete/{user_id}",
    response_model=UserDeleteResponse,
    status_code=status.HTTP_200_OK,
)
@exception_handler
async def soft_delete_user(
    user_id: str = Path(..., description="User ID to soft delete"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Soft delete a user by setting is_active to True.
    """
    
    # Check if user exists
    user = await get_user_by_id(db, user_id)
    if not user:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found.",
            log_error=True,
        )
    
    # Check if user is already soft deleted
    if user.is_active:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="User is already deleted.",
            log_error=True,
        )
    
    # Soft delete user
    user.is_active = True
    
    # Save changes
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return api_response(
        status_code=status.HTTP_200_OK,
        message="User soft deleted successfully.",
        data=UserDeleteResponse(
            user_id=user_id,
            message="User soft deleted successfully.",
        ),
    )


@router.patch(
    "/restore/{user_id}",
    response_model=UserRestoreResponse,
    status_code=status.HTTP_200_OK,
)
@exception_handler
async def restore_user(
    user_id: str = Path(..., description="User ID to restore"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Restore a soft deleted user by setting is_active to False.
    """
    
    # Check if user exists
    user = await get_user_by_id(db, user_id)
    if not user:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found.",
            log_error=True,
        )
    
    # Check if user is not soft deleted
    if not user.is_active:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="User is already restored.",
            log_error=True,
        )
    
    # Restore user
    user.is_active = False
    
    # Save changes
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return api_response(
        status_code=status.HTTP_200_OK,
        message="User restored successfully.",
        data=UserRestoreResponse(
            user_id=user_id,
            message="User restored successfully.",
        ),
    )


@router.delete(
    "/hard-delete/{user_id}",
    response_model=UserDeleteResponse,
    status_code=status.HTTP_200_OK,
)
@exception_handler
async def hard_delete_user(
    user_id: str = Path(..., description="User ID to permanently delete"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Permanently delete a user and all associated data.
    This action cannot be undone.
    """
    
    # Check if user exists
    user = await get_user_by_id(db, user_id)
    if not user:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found.",
            log_error=True,
        )
    
    # Delete user verification records first (due to foreign key constraints)
    await db.execute(
        delete(UserVerification).where(UserVerification.user_id == user_id)
    )
    
    # Delete the user
    await db.execute(
        delete(User).where(User.user_id == user_id)
    )
    
    # Commit the transaction
    await db.commit()
    
    return api_response(
        status_code=status.HTTP_200_OK,
        message="User permanently deleted successfully.",
        data=UserDeleteResponse(
            user_id=user_id,
            message="User permanently deleted successfully.",
        ),
    )