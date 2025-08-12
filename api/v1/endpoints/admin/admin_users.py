from fastapi import APIRouter, Depends, Query, status, Path, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from core.api_response import api_response
from db.sessions.database import get_db
from schemas.admin_user import (
    PaginatedAdminListResponse,
    AdminUpdateRequest,
    AdminUpdateResponse,
    AdminDeleteResponse,
    AdminRestoreResponse,
    AdminProfilePictureUploadResponse,
    AdminUserDetailResponse
)
from services.admin_user import (
    get_all_admin_users,
    update_admin_user,
    soft_delete_admin_user,
    restore_admin_user,
    hard_delete_admin_user,
    upload_admin_profile_picture,
    get_admin_user_details
)
from utils.exception_handlers import exception_handler

router = APIRouter()


# @router.get(
#     "/",
#     response_model=PaginatedAdminListResponse,
#     status_code=status.HTTP_200_OK,
# )
# @exception_handler
# async def get_admin_users(
#     page: int = Query(1, ge=1, description="Page number (starts from 1)"),
#     per_page: int = Query(10, ge=1, le=100, description="Number of users per page (max 100)"),
#     db: AsyncSession = Depends(get_db),
# ) -> JSONResponse:

#     result = await get_all_admin_users(
#         db=db,
#         page=page,
#         per_page=per_page
#     )
    
#     if isinstance(result, JSONResponse):
#         return result
    
#     return api_response(
#         status_code=status.HTTP_200_OK,
#         message="Admin users retrieved successfully.",
#         data=result,
#     )



@router.get(
    "/",
    response_model=PaginatedAdminListResponse,
    status_code=status.HTTP_200_OK,
)
@exception_handler
async def get_admin_users(
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Get all admin users.
    """

    result = await get_all_admin_users(db=db)

    if isinstance(result, JSONResponse):
        return result

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Admin users retrieved successfully.",
        data=result,
    )


@router.get(
    "/admin-profile-details/{user_id}",
    response_model=AdminUserDetailResponse,
    status_code=status.HTTP_200_OK,
)
@exception_handler
async def admin_profile_details(
    user_id: str = Path(..., description="Admin user ID to retrieve"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Get detailed information about an admin user by ID.
    
    Returns the user's email, username, role, profile picture URL, and other details.
    """
    result = await get_admin_user_details(db=db, user_id=user_id)

    if isinstance(result, JSONResponse):
        return result

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Admin user details retrieved successfully.",
        data=result.model_dump(),
    )


@router.put(
    "/{user_id}",
    response_model=AdminUpdateResponse,
    status_code=status.HTTP_200_OK,
)
@exception_handler
async def update_admin_user_by_id(
    user_id: str = Path(..., description="Admin user ID to update"),
    update_data: AdminUpdateRequest = ...,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Update an admin user by ID.
    
    Admin users can update their username, email, and role_id.
    Validates that username and email are unique and ensures only one superadmin exists.
    """
    result = await update_admin_user(db=db, user_id=user_id, update_data=update_data)

    if isinstance(result, JSONResponse):
        return result

    return api_response(
        status_code=status.HTTP_200_OK,
        message=result.message,
        data=result.model_dump(),
    )


@router.post(
    "/profile-picture/{user_id}",
    response_model=AdminProfilePictureUploadResponse,
    status_code=status.HTTP_200_OK,
)
@exception_handler
async def upload_admin_profile_picture_by_id(
    user_id: str = Path(..., description="Admin user ID to upload profile picture for"),
    file: UploadFile = File(..., description="Profile picture file to upload"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Upload profile picture for an admin user by ID.
    
    Accepts image files (JPEG, PNG, GIF, WebP, SVG, AVIF, JXL) up to 10MB.
    Replaces any existing profile picture.
    """
    result = await upload_admin_profile_picture(db=db, user_id=user_id, file=file)

    if isinstance(result, JSONResponse):
        return result

    return api_response(
        status_code=status.HTTP_200_OK,
        message=result.message,
        data=result.model_dump(),
    )


@router.delete(
    "/soft/{user_id}",
    response_model=AdminDeleteResponse,
    status_code=status.HTTP_200_OK,
)
@exception_handler
async def soft_delete_admin_user_by_id(
    user_id: str = Path(..., description="Admin user ID to soft delete"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Soft delete an admin user by ID.
    
    The user will be marked as deleted but not permanently removed from the database.
    Prevents deletion of the last active superadmin.
    """
    result = await soft_delete_admin_user(db=db, user_id=user_id)

    if isinstance(result, JSONResponse):
        return result

    return api_response(
        status_code=status.HTTP_200_OK,
        message=result.message,
        data=result.model_dump(),
    )


@router.post(
    "/restore/{user_id}",
    response_model=AdminRestoreResponse,
    status_code=status.HTTP_200_OK,
)
@exception_handler
async def restore_admin_user_by_id(
    user_id: str = Path(..., description="Admin user ID to restore"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Restore a soft deleted admin user by ID.
    
    Validates that username and email don't conflict with existing active users.
    """
    result = await restore_admin_user(db=db, user_id=user_id)

    if isinstance(result, JSONResponse):
        return result

    return api_response(
        status_code=status.HTTP_200_OK,
        message=result.message,
        data=result.model_dump(),
    )


@router.delete(
    "/hard/{user_id}",
    response_model=AdminDeleteResponse,
    status_code=status.HTTP_200_OK,
)
@exception_handler
async def hard_delete_admin_user_by_id(
    user_id: str = Path(..., description="Admin user ID to permanently delete"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Permanently delete an admin user by ID.
    
    This action cannot be undone. The user will be completely removed from the database.
    Prevents deletion of the last active superadmin.
    """
    result = await hard_delete_admin_user(db=db, user_id=user_id)

    if isinstance(result, JSONResponse):
        return result

    return api_response(
        status_code=status.HTTP_200_OK,
        message=result.message,
        data=result.model_dump(),
    )