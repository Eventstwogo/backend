from fastapi import APIRouter, Depends, status, Path, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from core.api_response import api_response

from db.sessions.database import get_db
from schemas.vendor_details import VendorProfilePictureUploadResponse, VendorUserDetailResponse, VendorBannerUploadResponse, VendorBannerResponse
from services.vendor_user import (
    upload_vendor_profile_picture,
    get_vendor_user_details,
    upload_vendor_banner_image,
    get_vendor_banner_image
)
from utils.exception_handlers import exception_handler

router = APIRouter()


@router.get(
    "/vendor-profile-details/{user_id}",
    response_model=VendorUserDetailResponse,
    status_code=status.HTTP_200_OK,
)
@exception_handler
async def vendor_profile_details(
    user_id: str = Path(..., description="Vendor user ID to retrieve"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Get detailed information about a vendor user by ID.
    
    Returns the user's email, username, store name (null for employees), role, and profile picture URL.
    """
    result = await get_vendor_user_details(db=db, user_id=user_id)

    if isinstance(result, JSONResponse):
        return result

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Vendor user details retrieved successfully.",
        data=result.model_dump(),
    )


@router.post(
    "/profile-picture/{user_id}",
    response_model=VendorProfilePictureUploadResponse,
    status_code=status.HTTP_200_OK,
)
@exception_handler
async def upload_vendor_profile_picture_by_id(
    user_id: str = Path(..., description="Vendor user ID to upload profile picture for"),
    file: UploadFile = File(..., description="Profile picture file to upload"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Upload profile picture for a vendor user by ID.
    
    Accepts image files (JPEG, PNG, GIF, WebP, SVG, AVIF, JXL) up to 10MB.
    Replaces any existing profile picture.
    """
    result = await upload_vendor_profile_picture(db=db, user_id=user_id, file=file)

    if isinstance(result, JSONResponse):
        return result

    return api_response(
        status_code=status.HTTP_200_OK,
        message=result.message,
        data=result.model_dump(),
    )


@router.post(
    "/banner-image/{user_id}",
    response_model=VendorBannerUploadResponse,
    status_code=status.HTTP_200_OK,
)
@exception_handler
async def upload_vendor_banner_image_by_id(
    user_id: str = Path(..., description="Vendor user ID to upload banner image for"),
    file: UploadFile = File(..., description="Banner image file to upload"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Upload banner image for a vendor business by user ID.
    """
    result = await upload_vendor_banner_image(db=db, user_id=user_id, file=file)

    if isinstance(result, JSONResponse):
        return result

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Banner image uploaded successfully.",
        data=result.model_dump(),
    )


@router.get(
    "/banner-image/{user_id}",
    response_model=VendorBannerResponse,
    status_code=status.HTTP_200_OK,
)
@exception_handler
async def get_vendor_banner_image_by_id(
    user_id: str = Path(..., description="Vendor user ID to retrieve banner image for"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Get banner image for a vendor business by user ID.
    """
    result = await get_vendor_banner_image(db=db, user_id=user_id)

    if isinstance(result, JSONResponse):
        return result

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Vendor banner image retrieved successfully.",
        data=result.model_dump(),
    )