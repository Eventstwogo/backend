"""
Vendor Queries Service

This module provides service functions for managing vendor queries,
including CRUD operations and statistics.
"""

from datetime import datetime, timezone
from typing import Dict, Optional

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.responses import JSONResponse

from core.api_response import api_response
from db.models.superadmin import VendorQuery, QueryStatus, AdminUser, VendorLogin
from schemas.queries import UpdateQueryStatusRequest
from utils.id_generators import decrypt_data


def get_user_display_name(user: AdminUser | VendorLogin) -> str:
    """
    Get the display name for a user (store name for vendors, decrypted username for admins).
    
    Args:
        user: AdminUser or VendorLogin object
        
    Returns:
        String representing the display name
    """
    if isinstance(user, VendorLogin):
        # For vendors, prioritize store name from business profile
        if hasattr(user, 'business_profile') and user.business_profile and user.business_profile.store_name:
            return user.business_profile.store_name
        # If no store name available, return a placeholder indicating missing store name
        return f"Store Name Not Set (User: {user.user_id})"
    elif isinstance(user, AdminUser):
        # For admins, decrypt the encrypted username
        try:
            decrypted_username = decrypt_data(user.username)
            return decrypted_username
        except Exception as e:
            # If decryption fails, return a fallback
            return f"Admin User ({user.user_id})"
    else:
        return "Unknown User"


def get_user_role(user: AdminUser | VendorLogin) -> str:
    """
    Determine user role based on user type and vendor_ref_id.
    
    Args:
        user: AdminUser or VendorLogin object
        
    Returns:
        String representing the user role
    """
    if isinstance(user, AdminUser):
        # Check if role relationship is loaded
        if hasattr(user, 'role') and user.role:
            return user.role.role_name.lower()
        else:
            return "admin"  # Default fallback for admin users
    elif isinstance(user, VendorLogin):
        # Identify vendor type based on vendor_ref_id
        if user.vendor_ref_id == "unknown":
            return "vendor"  # Main vendor (can create and access queries)
        elif user.vendor_ref_id and len(user.vendor_ref_id) == 6:
            return "vendor_employee"  # Vendor employee (no access to queries)
        else:
            return "vendor"  # Default fallback
    else:
        return "unknown"


async def get_user_by_id(user_id: str, db: AsyncSession) -> Optional[AdminUser | VendorLogin]:
    """
    Get a user by ID, checking both admin and vendor tables.
    
    Args:
        user_id: The ID of the user to retrieve
        db: Database session
        
    Returns:
        AdminUser or VendorLogin object if found, None otherwise
    """
    # First try to find in admin users with role relationship loaded
    admin_result = await db.execute(
        select(AdminUser)
        .options(selectinload(AdminUser.role))
        .where(AdminUser.user_id == user_id)
    )
    admin_user = admin_result.scalar_one_or_none()
    if admin_user:
        return admin_user
    
    # Then try to find in vendor users with role relationship and business profile loaded
    vendor_result = await db.execute(
        select(VendorLogin)
        .options(
            selectinload(VendorLogin.role_details),
            selectinload(VendorLogin.business_profile)
        )
        .where(VendorLogin.user_id == user_id)
    )
    vendor_user = vendor_result.scalar_one_or_none()
    return vendor_user


async def get_query_by_id(query_id: int, db: AsyncSession) -> Optional[VendorQuery]:
    """
    Get a vendor query by its ID.
    
    Args:
        query_id: The ID of the query to retrieve
        db: Database session
        
    Returns:
        VendorQuery object if found, None otherwise
    """
    result = await db.execute(
        select(VendorQuery).where(VendorQuery.id == query_id)
    )
    return result.scalar_one_or_none()


async def get_query_stats_service(db: AsyncSession, user_id: str) -> Dict | JSONResponse:
    """
    Get query statistics for dashboard based on user role (vendor/admin).
    
    Args:
        db: Database session
        user_id: ID of the user requesting stats
        
    Returns:
        Dictionary with statistics or JSONResponse with error
    """
    user = await get_user_by_id(user_id, db)
    if not user:
        return api_response(
            status.HTTP_404_NOT_FOUND, "User not found", log_error=True
        )

    user_role = get_user_role(user)
    
    # Vendor employees have no access to queries
    if user_role == "vendor_employee":
        return api_response(
            status.HTTP_403_FORBIDDEN, "Vendor employees do not have access to queries", log_error=True
        )
    
    # Base query for counting
    base_query = select(func.count(VendorQuery.id))
    
    if user_role == "vendor":
        # Vendor can only see their own queries
        base_query = base_query.where(VendorQuery.sender_user_id == user_id)
        
        # Get counts for different statuses
        total_result = await db.execute(base_query)
        total_queries = total_result.scalar() or 0
        
        open_result = await db.execute(
            base_query.where(VendorQuery.query_status == QueryStatus.QUERY_OPEN)
        )
        open_queries = open_result.scalar() or 0
        
        in_progress_result = await db.execute(
            base_query.where(VendorQuery.query_status == QueryStatus.QUERY_IN_PROGRESS)
        )
        in_progress_queries = in_progress_result.scalar() or 0
        
        answered_result = await db.execute(
            base_query.where(VendorQuery.query_status == QueryStatus.QUERY_ANSWERED)
        )
        answered_queries = answered_result.scalar() or 0
        
        closed_result = await db.execute(
            base_query.where(VendorQuery.query_status == QueryStatus.QUERY_CLOSED)
        )
        closed_queries = closed_result.scalar() or 0
        
        return {
            "total_queries": total_queries,
            "open_queries": open_queries,
            "in_progress_queries": in_progress_queries,
            "answered_queries": answered_queries,
            "closed_queries": closed_queries,
            "my_queries": total_queries,  # For vendors, all queries are their own
            "assigned_to_me": 0,  # Vendors don't get assigned queries
        }

    elif user_role in ["admin", "superadmin"]:
        # Admin can see all queries
        total_result = await db.execute(base_query)
        total_queries = total_result.scalar() or 0
        
        open_result = await db.execute(
            base_query.where(VendorQuery.query_status == QueryStatus.QUERY_OPEN)
        )
        open_queries = open_result.scalar() or 0
        
        in_progress_result = await db.execute(
            base_query.where(VendorQuery.query_status == QueryStatus.QUERY_IN_PROGRESS)
        )
        in_progress_queries = in_progress_result.scalar() or 0
        
        answered_result = await db.execute(
            base_query.where(VendorQuery.query_status == QueryStatus.QUERY_ANSWERED)
        )
        answered_queries = answered_result.scalar() or 0
        
        closed_result = await db.execute(
            base_query.where(VendorQuery.query_status == QueryStatus.QUERY_CLOSED)
        )
        closed_queries = closed_result.scalar() or 0
        
        # Queries assigned to this admin
        assigned_result = await db.execute(
            base_query.where(VendorQuery.receiver_user_id == user_id)
        )
        assigned_to_me = assigned_result.scalar() or 0
        
        return {
            "total_queries": total_queries,
            "open_queries": open_queries,
            "in_progress_queries": in_progress_queries,
            "answered_queries": answered_queries,
            "closed_queries": closed_queries,
            "my_queries": 0,  # Admins don't create queries
            "assigned_to_me": assigned_to_me,
        }
    
    else:
        return api_response(
            status.HTTP_403_FORBIDDEN, "Invalid user role", log_error=True
        )


async def update_query_status_service(
    db: AsyncSession, 
    query_id: int, 
    user_id: str, 
    request: UpdateQueryStatusRequest
) -> VendorQuery | JSONResponse:
    """
    Update the status of a vendor query.
    
    Args:
        db: Database session
        query_id: ID of the query to update
        user_id: ID of the user making the update
        request: Update request data
        
    Returns:
        Updated VendorQuery object or JSONResponse with error
    """
    user = await get_user_by_id(user_id, db)
    if not user:
        return api_response(
            status.HTTP_404_NOT_FOUND, "User not found", log_error=True
        )

    query = await get_query_by_id(query_id, db)
    if not query:
        return api_response(
            status.HTTP_404_NOT_FOUND, "Query not found", log_error=True
        )

    user_role = get_user_role(user)
    
    # Vendor employees have no access to queries
    if user_role == "vendor_employee":
        return api_response(
            status.HTTP_403_FORBIDDEN, "Vendor employees do not have access to queries", log_error=True
        )
    
    # Check permissions
    if user_role == "vendor" and query.sender_user_id != user_id:
        return api_response(
            status.HTTP_403_FORBIDDEN, "Access denied", log_error=True
        )
    
    # Only vendors can close queries
    if request.query_status == QueryStatus.QUERY_CLOSED and user_role != "vendor":
        return api_response(
            status.HTTP_403_FORBIDDEN,
            "Only vendors can close queries",
            log_error=True,
        )

    # Update the query
    query.query_status = request.query_status
    query.updated_at = datetime.now(timezone.utc)
    
    # Set receiver if not already set and user is admin
    if not query.receiver_user_id and user_role == "admin":
        query.receiver_user_id = user_id

    await db.commit()
    await db.refresh(query)
    
    return query