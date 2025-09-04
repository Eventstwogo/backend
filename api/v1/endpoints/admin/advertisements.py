from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from schemas.advertisement import (
    AdvertisementResponse,
    validate_target_url_form,
    validate_title_form,
)
from services.advertisement import AdvertisementService
from core.api_response import api_response
from core.config import settings
from db.sessions.database import get_db
from utils.exception_handlers import exception_handler
from utils.file_uploads import remove_file_if_exists, save_uploaded_file
from utils.id_generators import generate_digits_letters

router = APIRouter()


@router.post(
    "",
    response_model=AdvertisementResponse,
    status_code=status.HTTP_201_CREATED,
)
@exception_handler
async def create_advertisement(
    title: str = Form(
        ..., description="Advertisement title (required)", max_length=255
    ),
    banner: UploadFile = File(..., description="Banner image file (required)"),
    target_url: Optional[str] = Form(
        None, description="Target URL (optional)", max_length=255
    ),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Create a new advertisement with file upload.
    """
    if not banner or not banner.filename:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Banner file is required.",
            log_error=True,
        )

    validated_title = validate_title_form(title)
    validated_target_url = (
        validate_target_url_form(target_url) if target_url else None
    )

    ad_id = generate_digits_letters(6)

    banner_path = f"advertisements/{ad_id}"
    banner_path = await save_uploaded_file(banner, banner_path)
    if not banner_path:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Failed to upload banner file",
            log_error=True,
        )

    new_advertisement = await AdvertisementService.create_advertisement(
        db=db,
        id=ad_id,
        title=validated_title,
        banner=banner_path,
        target_url=validated_target_url,
    )

    return api_response(
        status_code=status.HTTP_201_CREATED,
        message="Advertisement created successfully",
        data=AdvertisementResponse.model_validate(new_advertisement),
    )


@router.get("", response_model=List[AdvertisementResponse])
@exception_handler
async def get_all_advertisements(
    status_filter: Optional[bool] = Query(
        None,
        description="Filter advertisements by status",
    ),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Number of records to return"
    ),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Get all advertisements with optional filtering and pagination.

    Args:
        status_filter: Optional filter by advertisement status
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
        db: Database session

    Returns:
        JSONResponse: List of advertisements
    """
    advertisements = await AdvertisementService.get_all_advertisements(
        db=db, status_filter=status_filter, skip=skip, limit=limit
    )

    advertisement_responses = [
        AdvertisementResponse.model_validate(ad) for ad in advertisements
    ]

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Advertisements retrieved successfully",
        data=advertisement_responses,
    )


@router.get("/{ad_id}", response_model=AdvertisementResponse)
@exception_handler
async def get_advertisement_by_id(
    ad_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Get a specific advertisement by ID.

    Args:
        ad_id: The ID of the advertisement to retrieve
        db: Database session

    Returns:
        JSONResponse: The advertisement details
    """
    advertisement = await AdvertisementService.get_advertisement_by_id(
        db, ad_id
    )

    if not advertisement:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"Advertisement with ID {ad_id} not found",
            log_error=True,
        )

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Advertisement retrieved successfully",
        data=AdvertisementResponse.model_validate(advertisement),
    )


@router.put(
    "/{ad_id}",
    response_model=AdvertisementResponse,
    status_code=status.HTTP_200_OK,
)
@exception_handler
async def update_advertisement(
    ad_id: str,
    title: Optional[str] = Form(
        None, description="Advertisement title (optional)", max_length=255
    ),
    banner: Optional[UploadFile] = File(
        None, description="Banner image file (optional)"
    ),
    target_url: Optional[str] = Form(
        None, description="Target URL (optional)", max_length=255
    ),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Update an advertisement with optional title, banner, and target URL.
    """
    # Check if advertisement exists
    advertisement = await AdvertisementService.get_advertisement_by_id(
        db, ad_id
    )
    if not advertisement:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"Advertisement with ID {ad_id} not found",
            log_error=True,
        )

    validated_title = validate_title_form(title) if title else None
    validated_target_url = (
        validate_target_url_form(target_url) if target_url else None
    )

    banner_path = None
    if banner and banner.filename:
        banner_path = settings.ADVERTISEMENT_BANNER_UPLOAD_PATH.format(
            ad_id=advertisement.ad_id
        )
        banner_path = await save_uploaded_file(banner, banner_path)
        if not banner_path:
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Failed to upload banner file",
                log_error=True,
            )

        # Remove old banner if exists
        if advertisement.banner:
            await remove_file_if_exists(advertisement.banner)

    updated_advertisement = await AdvertisementService.update_advertisement(
        db=db,
        ad_id=ad_id,
        title=validated_title,
        banner=banner_path,
        target_url=validated_target_url,
    )

    if not updated_advertisement:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"Advertisement with ID {ad_id} not found",
            log_error=True,
        )

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Advertisement updated successfully",
        data=AdvertisementResponse.model_validate(updated_advertisement),
    )


@router.delete(
    "/{ad_id}",
    status_code=status.HTTP_200_OK,
)
@exception_handler
async def delete_advertisement(
    ad_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Delete an advertisement and clean up associated files.

    Args:
        ad_id: The ID of the advertisement to delete
        db: Database session

    Returns:
        JSONResponse: Success message
    """
    # Get advertisement to access banner path for cleanup
    advertisement = await AdvertisementService.get_advertisement_by_id(
        db, ad_id
    )
    if not advertisement:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"Advertisement with ID {ad_id} not found",
            log_error=True,
        )

    # Remove banner file if exists
    if advertisement.banner:
        await remove_file_if_exists(advertisement.banner)

    # Delete the advertisement
    deleted = await AdvertisementService.delete_advertisement(db, ad_id)
    if not deleted:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"Advertisement with ID {ad_id} not found",
            log_error=True,
        )

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Advertisement deleted successfully",
    )


@router.get("/active/all", response_model=List[AdvertisementResponse])
@exception_handler
async def get_active_advertisements(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Number of records to return"
    ),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Get all active advertisements.

    Args:
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
        db: Database session

    Returns:
        JSONResponse: List of active advertisements
    """
    advertisements = await AdvertisementService.get_active_advertisements(
        db=db, skip=skip, limit=limit
    )

    advertisement_responses = [
        AdvertisementResponse.model_validate(ad) for ad in advertisements
    ]

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Active advertisements retrieved successfully",
        data=advertisement_responses,
    )


@router.patch("/status/{ad_id}", response_model=AdvertisementResponse)
@exception_handler
async def toggle_advertisement_status(
    ad_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Toggle advertisement status (active/inactive).

    Args:
        ad_id: The ID of the advertisement to toggle status
        db: Database session

    Returns:
        JSONResponse: The updated advertisement details
    """
    updated_advertisement = (
        await AdvertisementService.toggle_advertisement_status(db, ad_id)
    )

    if not updated_advertisement:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"Advertisement with ID {ad_id} not found",
            log_error=True,
        )

    status_text = (
        "deactivated" if updated_advertisement.ad_status else "activated"
    )

    return api_response(
        status_code=status.HTTP_200_OK,
        message=f"Advertisement {status_text} successfully",
        data=AdvertisementResponse.model_validate(updated_advertisement),
    )
