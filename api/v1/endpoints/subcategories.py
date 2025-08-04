from datetime import datetime
from typing import Optional, cast

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import case, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from starlette.responses import JSONResponse

from core.api_response import api_response
from db.models.superadmin import SubCategory
from db.sessions.database import get_db
from utils.exception_handlers import exception_handler
from utils.file_uploads import get_media_url

router = APIRouter()


@router.get("/")
@exception_handler
async def get_all_subcategories(
    status_filter: Optional[bool] = Query(
        None,
        description="Filter by subcategory status: true, false, or omit for all",
    ),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    stmt = select(SubCategory)

    if status_filter is not None:
        stmt = stmt.where(SubCategory.subcategory_status == status_filter)

    result = await db.execute(stmt)
    subcategories = result.scalars().all()

    data = [
        {
            "subcategory_id": sub.subcategory_id,
            "category_id": sub.category_id,
            "subcategory_name": sub.subcategory_name.title(),
            "subcategory_description": sub.subcategory_description,
            "subcategory_slug": sub.subcategory_slug,
            "subcategory_meta_title": sub.subcategory_meta_title,
            "subcategory_meta_description": sub.subcategory_meta_description,
            "subcategory_img_thumbnail": get_media_url(
                sub.subcategory_img_thumbnail
            ),
            "featured_subcategory": sub.featured_subcategory,
            "show_in_menu": sub.show_in_menu,
            "subcategory_status": sub.subcategory_status,
            "subcategory_tstamp": (
                cast(datetime, sub.subcategory_tstamp).isoformat()
                if sub.subcategory_tstamp
                else None
            ),
        }
        for sub in subcategories
    ]

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Subcategories fetched successfully",
        data=data,
    )


@router.get("/analytics")
@exception_handler
async def subcategory_analytics(
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    stats_query = await db.execute(
        select(
            func.count().label("total_subcategories"),
            func.count(
                case((SubCategory.subcategory_status.is_(False), 1))
            ).label("active_subcategories"),
            func.count(
                case((SubCategory.subcategory_status.is_(True), 1))
            ).label("inactive_subcategories"),
            func.count(
                case((SubCategory.featured_subcategory.is_(True), 1))
            ).label("featured_subcategories"),
            func.count(case((SubCategory.show_in_menu.is_(True), 1))).label(
                "shown_in_menu"
            ),
            func.count(case((SubCategory.show_in_menu.is_(False), 1))).label(
                "hidden_from_menu"
            ),
        )
    )

    stats = stats_query.first()

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Subcategory analytics fetched successfully",
        data={
            "total_subcategories": getattr(stats, "total_subcategories", 0),
            "active_subcategories": getattr(stats, "active_subcategories", 0),
            "inactive_subcategories": getattr(
                stats, "inactive_subcategories", 0
            ),
            "featured_subcategories": getattr(
                stats, "featured_subcategories", 0
            ),
            "shown_in_menu": getattr(stats, "shown_in_menu", 0),
            "hidden_from_menu": getattr(stats, "hidden_from_menu", 0),
        },
    )
