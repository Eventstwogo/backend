from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from schemas.partners import (
    PartnersResponse,
    validate_website_url_form,
)
from core.api_response import api_response
from core.config import settings
from db.models.superadmin import Partners
from db.sessions.database import get_db
from utils.exception_handlers import exception_handler
from utils.file_uploads import remove_file_if_exists, save_uploaded_file
from utils.id_generators import generate_digits_letters

router = APIRouter()


@router.post(
    "", response_model=PartnersResponse, status_code=status.HTTP_201_CREATED
)
@exception_handler
async def create_partner(
    logo: UploadFile = File(..., description="Partner logo file (required)"),
    website_url: str = Form(
        ..., description="Partner's website URL (required)", max_length=255
    ),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Create a new partner with file upload.

    Args:
        validated_data: Validated partner creation form data
        db: Database session

    Returns:
        JSONResponse: The created partner details
    """
    if not logo or not logo.filename:
        raise ValueError("Logo file is required.")

    # Validate website URL if provided
    website_url = validate_website_url_form(website_url)

    # Check if website URL already exists
    existing_url_stmt = select(Partners).where(
        Partners.website_url == website_url
    )
    existing_url_result = await db.execute(existing_url_stmt)
    if existing_url_result.scalar_one_or_none():
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=f"Website URL '{website_url}' is already associated with another partner",
            log_error=True,
        )

    # Generate unique ID
    partner_id = generate_digits_letters(6)

    # Ensure ID is unique
    while True:
        existing_stmt = select(Partners).where(
            Partners.partner_id == partner_id
        )
        result = await db.execute(existing_stmt)
        if not result.scalar_one_or_none():
            break
        partner_id = generate_digits_letters(6)

     
    try:
        partner_image_path = f"partners/{partner_id}"
         
        logo_path = await save_uploaded_file(logo, partner_image_path)
        if not logo_path:
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Failed to upload logo file",
                log_error=True,
            )
    except Exception as e:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=f"Logo upload error: {str(e)}",
            log_error=True,
        )

    # Create new partner
    new_partner = Partners(
        partner_id=partner_id,
        logo=logo_path,
        website_url=website_url,
    )

    db.add(new_partner)
    await db.commit()
    await db.refresh(new_partner)

    return api_response(
        status_code=status.HTTP_201_CREATED,
        message="Partner created successfully",
        data=PartnersResponse.model_validate(new_partner),
    )


@router.get("", response_model=List[PartnersResponse])
@exception_handler
async def get_all_partners(
    status_filter: Optional[bool] = Query(
        None,
        description="Filter partners by status",
    ),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Number of records to return"
    ),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Get all partners with optional filtering and pagination.

    Args:
        status_filter: Optional filter by partner status
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
        db: Database session

    Returns:
        JSONResponse: List of partners
    """
    # Build query
    stmt = select(Partners)

    # Apply status filter if provided
    if status_filter is not None:
        stmt = stmt.where(Partners.partner_status == status_filter)

    # Apply pagination and ordering
    stmt = stmt.order_by(Partners.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(stmt)
    partners = result.scalars().all()

    partner_responses = [
        PartnersResponse.model_validate(partner) for partner in partners
    ]

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Partners retrieved successfully",
        data=partner_responses,
    )


@router.get("/{partner_id}", response_model=PartnersResponse)
@exception_handler
async def get_partner_by_id(
    partner_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Get a specific partner by ID.

    Args:
        partner_id: The ID of the partner to retrieve
        db: Database session

    Returns:
        JSONResponse: The partner details
    """
    stmt = select(Partners).where(Partners.partner_id == partner_id)
    result = await db.execute(stmt)
    partner = result.scalar_one_or_none()

    if not partner:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"Partner with ID {partner_id} not found",
            log_error=True,
        )

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Partner retrieved successfully",
        data=PartnersResponse.model_validate(partner),
    )


@router.put(
    "/{partner_id}",
    response_model=PartnersResponse,
    status_code=status.HTTP_200_OK,
)
@exception_handler
async def update_partner(
    partner_id: str,
    logo: Optional[UploadFile] = File(
        None, description="Partner logo file (optional)"
    ),
    website_url: Optional[str] = Form(
        None, description="Partner's website URL (optional)", max_length=255
    ),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Update a partner with optional logo and website URL.

    Args:
        partner_id (str): The ID of the partner to update.
        logo (Optional[UploadFile]): Partner logo file.
        website_url (Optional[str]): Partner's website URL.
        db (AsyncSession): Database session.

    Returns:
        JSONResponse: The updated partner details.
    """
    # Find the partner
    stmt = select(Partners).where(Partners.partner_id == partner_id)
    result = await db.execute(stmt)
    partner = result.scalar_one_or_none()

    if not partner:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"Partner with ID {partner_id} not found",
            log_error=True,
        )

    # Update website URL if provided
    if website_url:
        validated_website_url = validate_website_url_form(website_url)

        # Check if the new website URL already exists for a different partner
        existing_url_stmt = select(Partners).where(
            Partners.website_url == validated_website_url,
            Partners.partner_id != partner_id,
        )
        existing_url_result = await db.execute(existing_url_stmt)
        if existing_url_result.scalar_one_or_none():
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=f"Website URL '{validated_website_url}' is already associated with another partner",
                log_error=True,
            )

        partner.website_url = validated_website_url

    # Handle logo upload if provided
    if logo:
        try:
            # Upload new logo
            partner_image_path = settings.PARTNERS_UPLOAD_PATH.format(
                partner_id=partner_id
            )
            logo_path = await save_uploaded_file(logo, partner_image_path)
            if not logo_path:
                return api_response(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="Failed to upload logo file",
                    log_error=True,
                )

            # Remove old logo if exists
            if partner.logo:
                await remove_file_if_exists(partner.logo)
            partner.logo = logo_path
        except Exception as e:
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=f"Logo upload error: {str(e)}",
                log_error=True,
            )

    await db.commit()
    await db.refresh(partner)

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Partner updated successfully",
        data=PartnersResponse.model_validate(partner),
    )


@router.delete(
    "/{partner_id}",
    status_code=status.HTTP_200_OK,
)
@exception_handler
async def delete_partner(
    partner_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Delete a partner and clean up associated files.

    Args:
        partner_id: The ID of the partner to delete
        db: Database session

    Returns:
        JSONResponse: Success message
    """
    # Check if partner exists
    stmt = select(Partners).where(Partners.partner_id == partner_id)
    result = await db.execute(stmt)
    partner = result.scalar_one_or_none()

    if not partner:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"Partner with ID {partner_id} not found",
            log_error=True,
        )

    # Remove logo file if exists
    if partner.logo:
        await remove_file_if_exists(partner.logo)

    # Delete the partner
    delete_stmt = delete(Partners).where(Partners.partner_id == partner_id)
    await db.execute(delete_stmt)
    await db.commit()

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Partner deleted successfully",
    )


@router.get("/active/all", response_model=List[PartnersResponse])
@exception_handler
async def get_active_partners(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Number of records to return"
    ),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Get all active partners.

    Args:
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
        db: Database session

    Returns:
        JSONResponse: List of active partners
    """
    stmt = (
        select(Partners)
        .where(Partners.partner_status == False)
        .order_by(Partners.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    result = await db.execute(stmt)
    partners = result.scalars().all()

    partner_responses = [
        PartnersResponse.model_validate(partner) for partner in partners
    ]

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Active partners retrieved successfully",
        data=partner_responses,
    )


@router.patch("/status/{partner_id}", response_model=PartnersResponse)
@exception_handler
async def toggle_partner_status(
    partner_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Toggle partner status (active/inactive).

    Args:
        partner_id: The ID of the partner to toggle status
        db: Database session

    Returns:
        JSONResponse: The updated partner details
    """
    # Find the partner
    stmt = select(Partners).where(Partners.partner_id == partner_id)
    result = await db.execute(stmt)
    partner = result.scalar_one_or_none()

    if not partner:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"Partner with ID {partner_id} not found",
            log_error=True,
        )

    # Toggle status
    partner.partner_status = not partner.partner_status

    await db.commit()
    await db.refresh(partner)

    status_text = "deactivated" if partner.partner_status else "activated"

    return api_response(
        status_code=status.HTTP_200_OK,
        message=f"Partner {status_text} successfully",
        data=PartnersResponse.model_validate(partner),
    )
