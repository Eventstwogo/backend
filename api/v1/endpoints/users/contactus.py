from typing import List, Optional
 
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse
 
from schemas.contactus import (
    EnquiryCreateRequest,
    EnquiryDeleteResponse,
    EnquiryResponse,
    EnquiryUpdateRequest,
)
from services.user_service import get_user_by_email_hash
from core.api_response import api_response
from db.models.superadmin import Enquiry, EnquiryStatus
from db.sessions.database import get_db
from utils.exception_handlers import exception_handler
from utils.id_generators import hash_data
 
router = APIRouter()
 
 
@router.post(
    "", response_model=EnquiryResponse, status_code=status.HTTP_201_CREATED
)
@exception_handler
async def create_enquiry(
    enquiry_data: EnquiryCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Create a new enquiry from registered users only.
 
    Args:
        enquiry_data: The enquiry data to create
        db: Database session
 
    Returns:
        JSONResponse: The created enquiry details
    """
    # Normalize and hash the email to check if user exists
    normalized_email = enquiry_data.email.lower().strip()
    email_hash = hash_data(normalized_email)
   
    # Check if the email exists in the user table
    existing_user = await get_user_by_email_hash(db, email_hash)
    if not existing_user:
        return api_response(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Only registered users can submit enquiries. Please register first.",
            log_error=True,
        )
   
    # Check if enquiry with same email and message already exists
    existing_enquiry_stmt = select(Enquiry).where(
        Enquiry.email == enquiry_data.email,
        Enquiry.message == enquiry_data.message
    )
    result = await db.execute(existing_enquiry_stmt)
    existing_enquiry = result.scalar_one_or_none()
 
    if existing_enquiry:
        return api_response(
            status_code=status.HTTP_409_CONFLICT,
            message="Enquiry already sent. An enquiry with the same email and message already exists.",
            log_error=True,
        )
 
    # Create new enquiry
    new_enquiry = Enquiry(
        firstname=enquiry_data.firstname,
        lastname=enquiry_data.lastname,
        email=enquiry_data.email,
        phone_number=enquiry_data.phone_number,
        message=enquiry_data.message,
        enquiry_status=EnquiryStatus.PENDING,
    )
 
    db.add(new_enquiry)
    await db.commit()
    await db.refresh(new_enquiry)
 
    return api_response(
        status_code=status.HTTP_201_CREATED,
        message="Enquiry created successfully",
        data=EnquiryResponse.model_validate(new_enquiry),
    )
 
 
@router.get("", response_model=List[EnquiryResponse])
@exception_handler
async def get_all_enquiries(
    status_filter: Optional[EnquiryStatus] = Query(
        None,
        description="Filter enquiries by status",
    ),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Number of records to return"
    ),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Get all enquiries with optional filtering and pagination.
 
    Args:
        status_filter: Optional filter by enquiry status
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
        db: Database session
 
    Returns:
        JSONResponse: List of enquiries
    """
    # Build query
    stmt = select(Enquiry)
 
    # Apply status filter if provided
    if status_filter:
        stmt = stmt.where(Enquiry.enquiry_status == status_filter)
 
    # Apply pagination and ordering
    stmt = stmt.order_by(Enquiry.created_at.desc()).offset(skip).limit(limit)
 
    result = await db.execute(stmt)
    enquiries = result.scalars().all()
 
    enquiry_responses = [
        EnquiryResponse.model_validate(enquiry) for enquiry in enquiries
    ]
 
    return api_response(
        status_code=status.HTTP_200_OK,
        message="Enquiries retrieved successfully",
        data=enquiry_responses,
    )
 
 
@router.get("/{enquiry_id}", response_model=EnquiryResponse)
@exception_handler
async def get_enquiry_by_id(
    enquiry_id: int,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Get a specific enquiry by ID.
 
    Args:
        enquiry_id: The ID of the enquiry to retrieve
        db: Database session
 
    Returns:
        JSONResponse: The enquiry details
    """
    stmt = select(Enquiry).where(Enquiry.enquiry_id == enquiry_id)
    result = await db.execute(stmt)
    enquiry = result.scalar_one_or_none()
 
    if not enquiry:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"Enquiry with ID {enquiry_id} not found",
            log_error=True,
        )
 
    return api_response(
        status_code=status.HTTP_200_OK,
        message="Enquiry retrieved successfully",
        data=EnquiryResponse.model_validate(enquiry),
    )
 
 
@router.put("/{enquiry_id}", response_model=EnquiryResponse)
@exception_handler
async def update_enquiry(
    enquiry_id: int,
    enquiry_update: EnquiryUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Update an enquiry (e.g., status).
 
    Args:
        enquiry_id: The ID of the enquiry to update
        enquiry_update: The update data
        db: Database session
 
    Returns:
        JSONResponse: The updated enquiry details
    """
    # Find the enquiry
    stmt = select(Enquiry).where(Enquiry.enquiry_id == enquiry_id)
    result = await db.execute(stmt)
    enquiry = result.scalar_one_or_none()
 
    if not enquiry:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"Enquiry with ID {enquiry_id} not found",
            log_error=True,
        )
 
    # Update fields if provided
    if enquiry_update.enquiry_status is not None:
        enquiry.enquiry_status = enquiry_update.enquiry_status
 
    await db.commit()
    await db.refresh(enquiry)
 
    return api_response(
        status_code=status.HTTP_200_OK,
        message="Enquiry updated successfully",
        data=EnquiryResponse.model_validate(enquiry),
    )
 
 
@router.delete("/{enquiry_id}", response_model=EnquiryDeleteResponse, status_code=status.HTTP_200_OK)
@exception_handler
async def delete_enquiry(
    enquiry_id: int,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Delete an enquiry.
 
    Args:
        enquiry_id: The ID of the enquiry to delete
        db: Database session
 
    Returns:
        JSONResponse: Success message
    """
    # Check if enquiry exists
    stmt = select(Enquiry).where(Enquiry.enquiry_id == enquiry_id)
    result = await db.execute(stmt)
    enquiry = result.scalar_one_or_none()
 
    if not enquiry:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"Enquiry with ID {enquiry_id} not found",
            log_error=True,
        )
 
    # Delete the enquiry
    delete_stmt = delete(Enquiry).where(Enquiry.enquiry_id == enquiry_id)
    await db.execute(delete_stmt)
    await db.commit()
 
    return api_response(
        status_code=status.HTTP_200_OK,
        message="Enquiry deleted successfully",
        data=EnquiryDeleteResponse(
            message="Enquiry deleted successfully"
        ),
    )
 