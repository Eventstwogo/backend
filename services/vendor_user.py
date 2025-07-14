
from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from core.api_response import api_response
from db.models.superadmin import Category, Config, VendorSignup


async def validate_unique_user(db: AsyncSession, email_hash: str):
    result = await db.execute(
        select(VendorSignup).where(
          
                VendorSignup.email_hash == email_hash
            
        )
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="A user with the given email already exists.",
        )



async def validate_category(db: AsyncSession, category_id: str) -> JSONResponse | Category:
    category_query = await db.execute(select(Category).where(Category.category_id == category_id))
    category = category_query.scalar_one_or_none()
    if not category:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="ategory not found.",
            log_error=True,
        )
    if category.category_status:
        return api_response(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Category is inactive.",
            log_error=True,
        )
    return category


async def get_config_or_404(
    db: AsyncSession,
) -> JSONResponse | Config:
    config_result = await db.execute(select(Config).limit(1))
    config = config_result.scalar_one_or_none()
    if not config:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Configuration not found.",
            log_error=True,
        )
    if not config.default_password_hash:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Default password hash not set in configuration.",
            log_error=True,
        )
    return config