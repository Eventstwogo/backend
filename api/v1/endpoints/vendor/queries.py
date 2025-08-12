from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.responses import JSONResponse

from core.api_response import api_response
from db.sessions.database import get_db
from db.models.superadmin import QueryStatus
from schemas.queries import (
    CreateQueryRequest, 
    QueryResponse, 
    ThreadMessage,
    AddMessageRequest,
    UpdateQueryStatusRequest,
    QueryFilters,
    QueryStatsResponse
)
from services.vendor_queries import (
    get_user_by_id,
    get_query_by_id,
    get_query_stats_service,
    update_query_status_service,
    get_user_role,
    get_user_display_name
)
from utils.exception_handlers import exception_handler
from db.models.superadmin import VendorQuery, AdminUser, VendorLogin



router = APIRouter()


@router.post(
    "", response_model=QueryResponse, summary="Create a new vendor query"
)
@exception_handler
async def create_query(
    request: CreateQueryRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    sender = await get_user_by_id(request.user_id, db)

    if not sender:
        return api_response(
            status.HTTP_404_NOT_FOUND, "Sender user not found", log_error=True
        )

    sender_role = get_user_role(sender)
    
    if sender_role != "vendor":
        return api_response(
            status.HTTP_403_FORBIDDEN,
            "Only vendors can create queries",
            log_error=True,
        )

    # Check for duplicate open query with same vendor, title, category, and message
    existing_query_stmt = select(VendorQuery).where(
        VendorQuery.sender_user_id == request.user_id,
        VendorQuery.title == request.title,
        VendorQuery.category == request.category,
        VendorQuery.query_status == QueryStatus.QUERY_OPEN
    )
    
    existing_result = await db.execute(existing_query_stmt)
    existing_queries = existing_result.scalars().all()
    
    # Check if any existing open query has the same initial message
    for existing_query in existing_queries:
        if existing_query.thread and len(existing_query.thread) > 0:
            first_message = existing_query.thread[0].get("message", "")
            if first_message == request.message:
                return api_response(
                    status.HTTP_409_CONFLICT,
                    "A query with the same title, category, and message already exists and is still open",
                    log_error=True,
                )

    initial_message = ThreadMessage(
        type="query",
        sender_type="vendor",
        user_id=sender.user_id,
        username=get_user_display_name(sender),
        message=request.message,
        timestamp=datetime.now(timezone.utc),
    )

    query = VendorQuery(
        sender_user_id=sender.user_id,
        title=request.title,
        category=request.category,
        thread=[initial_message.model_dump(mode="json")],
        query_status=QueryStatus.QUERY_OPEN,
    )

    db.add(query)
    await db.commit()
    await db.refresh(query)

    return api_response(
        status.HTTP_201_CREATED,
        "Vendor Query created successfully",
        QueryResponse.model_validate(query).model_dump(),
    )


@router.get("/list", summary="Get paginated list of queries")
@exception_handler
async def get_queries_list(
    user_id: str,
    status_filter: Optional[QueryStatus] = Query(None, alias="status"),
    category: Optional[str] = Query(None),
    sender_user_id: Optional[str] = Query(None),
    receiver_user_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
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
    
    filters = QueryFilters(
        query_status=status_filter,
        category=category,
        sender_user_id=sender_user_id,
        receiver_user_id=receiver_user_id,
        page=page,
        limit=limit,
    )

    # Build base query
    query_stmt = select(VendorQuery)

    if user_role == "vendor":
        query_stmt = query_stmt.where(VendorQuery.sender_user_id == user_id)
    elif user_role in ["admin", "superadmin"]:
        if filters.sender_user_id:
            query_stmt = query_stmt.where(
                VendorQuery.sender_user_id == filters.sender_user_id
            )
        if filters.receiver_user_id:
            query_stmt = query_stmt.where(
                VendorQuery.receiver_user_id == filters.receiver_user_id
            )
    else:
        return api_response(
            status.HTTP_403_FORBIDDEN, "Invalid user role", log_error=True
        )

    if filters.query_status:
        query_stmt = query_stmt.where(
            VendorQuery.query_status == filters.query_status
        )
    if filters.category:
        query_stmt = query_stmt.where(
            VendorQuery.category.ilike(f"%{filters.category}%")
        )

    # Get total count
    count_stmt = select(func.count()).select_from(query_stmt.subquery())
    count_result = await db.execute(count_stmt)
    total_count = count_result.scalar() or 0

    # Apply ordering and pagination
    query_stmt = query_stmt.order_by(desc(VendorQuery.updated_at))
    query_stmt = query_stmt.offset((filters.page - 1) * filters.limit).limit(
        filters.limit
    )

    result = await db.execute(query_stmt)
    queries = result.scalars().all()

    total_pages = (total_count + filters.limit - 1) // filters.limit

    queries_response = []
    for query in queries:
        query_dict = QueryResponse.model_validate(query).model_dump()
        query_dict["last_message"] = (
            query.thread[-1].get("message", "")[:100] if query.thread else None
        )
        query_dict["unread_count"] = 0
        queries_response.append(query_dict)

    return api_response(
        status.HTTP_200_OK,
        "Queries retrieved successfully",
        {
            "queries": queries_response,
            "pagination": {
                "current_page": filters.page,
                "total_pages": total_pages,
                "total_items": total_count,
                "items_per_page": filters.limit,
                "has_next": filters.page < total_pages,
                "has_prev": filters.page > 1,
            },
        },
    )


@router.get("/all", summary="Get all queries")
@exception_handler
async def get_all_queries(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Get all queries in the database without any restrictions.
    This endpoint returns all queries from all users.
    """
    # Build query to get all queries
    query_stmt = select(VendorQuery)

    # Get total count
    count_stmt = select(func.count()).select_from(query_stmt.subquery())
    count_result = await db.execute(count_stmt)
    total_count = count_result.scalar() or 0

    # Apply ordering and pagination
    query_stmt = query_stmt.order_by(desc(VendorQuery.updated_at))
    query_stmt = query_stmt.offset((page - 1) * limit).limit(limit)

    # Execute query
    result = await db.execute(query_stmt)
    queries = result.scalars().all()

    # Calculate pagination info
    total_pages = (total_count + limit - 1) // limit

    # Format response
    queries_response = []
    for query in queries:
        query_dict = QueryResponse.model_validate(query).model_dump()
        query_dict["last_message"] = (
            query.thread[-1].get("message", "")[:100] if query.thread else None
        )
        query_dict["unread_count"] = 0
        queries_response.append(query_dict)

    return api_response(
        status.HTTP_200_OK,
        "All queries retrieved successfully",
        {
            "queries": queries_response,
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_items": total_count,
                "items_per_page": limit,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
        },
    )


@router.get(
    "/{query_id}", response_model=QueryResponse, summary="Get query by ID"
)
@exception_handler
async def get_query(
    user_id: str,
    query_id: int = Path(..., description="Query ID"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
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
    
    if (
        user_role == "vendor"
        and query.sender_user_id != user_id
    ):
        return api_response(
            status.HTTP_403_FORBIDDEN, "Access denied", log_error=True
        )

    return api_response(
        status.HTTP_200_OK,
        "Query retrieved successfully",
        QueryResponse.model_validate(query).model_dump(),
    )


@router.post(
    "/messages/{query_id}",
    response_model=QueryResponse,
    summary="Add message to query",
)
@exception_handler
async def add_message_to_query(
    request: AddMessageRequest,
    query_id: int = Path(..., description="Query ID"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    user = await get_user_by_id(request.user_id, db)
    if not user:
        return api_response(
            status.HTTP_404_NOT_FOUND, "User not found", log_error=True
        )

    query = await get_query_by_id(query_id, db)
    if not query:
        return api_response(
            status.HTTP_404_NOT_FOUND, "Query not found", log_error=True
        )

    if query.query_status == QueryStatus.QUERY_CLOSED:
        return api_response(
            status.HTTP_400_BAD_REQUEST,
            "Cannot add messages to closed queries",
            log_error=True,
        )

    user_role = get_user_role(user)
    
    # Vendor employees have no access to queries
    if user_role == "vendor_employee":
        return api_response(
            status.HTTP_403_FORBIDDEN, "Vendor employees do not have access to queries", log_error=True
        )
    
    if user_role == "vendor":
        if query.sender_user_id != request.user_id:
            return api_response(
                status.HTTP_403_FORBIDDEN, "Access denied", log_error=True
            )
        sender_type = "vendor"
    elif user_role in ["admin", "superadmin"]:
        sender_type = "admin"
        if not query.receiver_user_id:
            query.receiver_user_id = request.user_id
    else:
        return api_response(
            status.HTTP_403_FORBIDDEN, "Invalid user role", log_error=True
        )

    new_message = ThreadMessage(
        type=request.message_type,
        sender_type=sender_type,
        user_id=request.user_id,
        username=get_user_display_name(user),
        message=request.message,
        timestamp=datetime.now(timezone.utc),
    )

    query.thread = (query.thread or []) + [new_message.model_dump(mode="json")]

    if sender_type == "admin" and query.query_status == QueryStatus.QUERY_OPEN:
        query.query_status = QueryStatus.QUERY_IN_PROGRESS
    elif sender_type == "admin" and request.message_type == "response":
        query.query_status = QueryStatus.QUERY_ANSWERED

    query.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(query)

    return api_response(
        status.HTTP_200_OK,
        "Message added successfully",
        QueryResponse.model_validate(query).model_dump(),
    )


@router.patch(
    "/status/{query_id}",
    response_model=QueryResponse,
    summary="Update query status",
)
@exception_handler
async def update_query_status(
    request: UpdateQueryStatusRequest,
    query_id: int = Path(..., description="Query ID"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    user = await get_user_by_id(request.user_id, db)
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
    
    if request.query_status == QueryStatus.QUERY_CLOSED:
        if user_role != "vendor":
            return api_response(
                status.HTTP_403_FORBIDDEN,
                "Only vendors can update query status as closed",
                log_error=True,
            )

    query = await get_query_by_id(query_id, db)
    if not query:
        return api_response(
            status.HTTP_404_NOT_FOUND, "Query not found", log_error=True
        )

    # Check if query is already closed
    if query.query_status == QueryStatus.QUERY_CLOSED:
        return api_response(
            status.HTTP_400_BAD_REQUEST,
            "Cannot update status for closed queries",
            log_error=True,
        )

    query.query_status = request.query_status
    query.updated_at = datetime.now(timezone.utc)
    if not query.receiver_user_id:
        query.receiver_user_id = request.user_id

    if request.message:
        status_message = ThreadMessage(
            type="response",
            sender_type=(
                "admin"
                if user_role in ["admin", "superadmin"]
                else "vendor"
            ),
            user_id=request.user_id,
            username=get_user_display_name(user),
            message=request.message,
            timestamp=datetime.now(timezone.utc),
        )
        query.thread = (query.thread or []) + [
            status_message.model_dump(mode="json")
        ]

    await db.commit()
    await db.refresh(query)

    return api_response(
        status.HTTP_200_OK,
        "Query status updated successfully",
        QueryResponse.model_validate(query).model_dump(),
    )


@router.get(
    "/stats/dashboard",
    response_model=QueryStatsResponse,
    summary="Get query statistics",
)
@exception_handler
async def get_query_stats(
    user_id: str, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    """
    Get query statistics for dashboard based on user role (vendor/admin).
    """
    stats = await get_query_stats_service(db, user_id)
    if isinstance(stats, JSONResponse):
        return stats

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Query statistics retrieved successfully",
        data=QueryStatsResponse(**stats).model_dump(),
    )


@router.delete("/{query_id}", summary="Close query")
@exception_handler
async def delete_query(
    user_id: str,
    query_id: int = Path(..., description="Query ID"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Soft delete a query (mark as closed). Only vendors allowed.
    """
    request = UpdateQueryStatusRequest(
        user_id=user_id,
        query_status=QueryStatus.QUERY_CLOSED,
        message="Query has been closed.",
    )
    query = await update_query_status_service(db, query_id, user_id, request)
    if isinstance(query, JSONResponse):
        return query

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Query has been successfully closed",
        data={"query_id": query_id, "status": query.query_status.value},
    )


@router.get("/categories/list", summary="Get query categories")
@exception_handler
async def get_query_categories(
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Get list of available query categories.
    """
    categories = [
        "Account Management",
        "Profile Setup",
        "Product Listing",
        "Payment Issues",
        "Technical Support",
        "Feature Request",
        "Bug Report",
        "General Inquiry",
        "Business Verification",
        "API Integration",
        "Order Management",
        "Inventory Issues",
    ]
    return api_response(
        status_code=status.HTTP_200_OK,
        message="Query categories retrieved successfully",
        data={"categories": categories},
    )


@router.get("/templates/message", summary="Get message templates")
@exception_handler
async def get_message_templates(
    template_type: str = Query(
        "admin", description="Type of templates (admin/vendor)"
    ),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Get predefined message templates for quick responses.
    """
    admin_templates = [
        {
            "id": "welcome",
            "title": "Welcome Message",
            "content": "Thank you for contacting us. We have received your query and will respond within 24 hours.",
        },
        {
            "id": "more_info",
            "title": "Request More Information",
            "content": "To better assist you, could you please provide more details about your issue?",
        },
        {
            "id": "resolved",
            "title": "Issue Resolved",
            "content": "Your issue has been resolved. Please let us know if you need any further assistance.",
        },
        {
            "id": "escalated",
            "title": "Escalated to Technical Team",
            "content": "Your query has been escalated to our technical team. You will receive an update within 48 hours.",
        },
    ]
    vendor_templates = [
        {
            "id": "followup",
            "title": "Follow-up Question",
            "content": "Thank you for your response. I have a follow-up question:",
        },
        {
            "id": "clarification",
            "title": "Need Clarification",
            "content": "Could you please clarify the following:",
        },
        {
            "id": "thanks",
            "title": "Thank You",
            "content": "Thank you for your help. This resolves my query.",
        },
    ]
    templates = (
        admin_templates if template_type in ["admin", "superadmin"] else vendor_templates
    )
    return api_response(
        status_code=status.HTTP_200_OK,
        message="Message templates retrieved successfully",
        data={"templates": templates},
    )
