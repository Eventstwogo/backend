
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from core.api_response import api_response
from db.sessions.database import get_db
from schemas.admin_user import PaginatedAdminListResponse
from services.admin_user import get_all_admin_users
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