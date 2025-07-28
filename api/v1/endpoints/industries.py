from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from slugify import slugify
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from utils.file_uploads import get_media_url
from core.api_response import api_response
from core.status_codes import APIResponse, StatusCode
from db.models.superadmin import Category, Industries, VendorLogin  
from db.sessions.database import get_db
from schemas.industry import CreateIndustry, IndustryDetails, IndustryUpdate
from utils.exception_handlers import exception_handler
from utils.id_generators import generate_digits_lowercase
from utils.validators import is_single_reserved_word
from sqlalchemy.orm import selectinload

router = APIRouter()


@router.post("/", summary="Create a new industry")
@exception_handler
async def create_industry(
    industry: CreateIndustry,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    result = await db.execute(
        select(Industries).where(Industries.industry_name == industry.industry_name)
    )
    existing = result.scalars().first()

    if existing:
        if not existing.is_active:
            return APIResponse.response(
                StatusCode.EXISTS,
                message="Industry with this name already exists.",
                log_error=True,
            )
        else:
            existing.is_active = False
            existing.timestamp = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(existing)
            return api_response(
                status_code=status.HTTP_200_OK,
                message="Soft-deleted industry reactivated successfully.",
                data={"industry_id": existing.industry_id},
            )

    if is_single_reserved_word(industry.industry_name):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Python reserved words are not allowed in industry names.",
        )

    industry_id = generate_digits_lowercase()
    new_industry = Industries(
        industry_id=industry_id,
        industry_name=industry.industry_name,
        industry_slug=industry.industry_slug,
        
    )
    db.add(new_industry)
    await db.commit()
    await db.refresh(new_industry)

    return api_response(
        status_code=status.HTTP_201_CREATED,
        message="Industry created successfully.",
        data={"industry_id": new_industry.industry_id},
    )


@router.get("/", response_model=List[IndustryDetails], summary="Get industries by active status")
@exception_handler
async def get_industries(
    is_active: Optional[bool] = Query(None, description="Filter industries by active status"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    query = select(Industries)
    if is_active is not None:
        query = query.where(Industries.is_active == is_active)

    result = await db.execute(query)
    industries = result.scalars().all()

    if not industries:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="No industries found.",
            log_error=True,
        )

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Industries retrieved successfully.",
        data=industries,
    )


@router.get("/find", summary="Find industry by name")
@exception_handler
async def get_industry_by_name(
    industry_name: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    result = await db.execute(
        select(Industries).where(func.upper(Industries.industry_name) == func.upper(industry_name))
    )
    industry = result.scalars().first()

    if not industry:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Industry not found.",
            log_error=True,
        )

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Industry found successfully.",
        data={"industry_id": industry.industry_id},
    )


@router.put("/{industry_id}", summary="Update industry by ID")
@exception_handler
async def update_industry(
    industry_id: str,
    update_data: IndustryUpdate,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    result = await db.execute(select(Industries).where(Industries.industry_id == industry_id))
    industry = result.scalars().first()

    if not industry:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Industry not found.",
            log_error=True,
        )

    if is_single_reserved_word(update_data.industry_name):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Reserved words are not allowed in industry names.",
        )

    if update_data.industry_name:
        # Check for duplicate
        dup_check = await db.execute(
            select(Industries).where(
                Industries.industry_name == update_data.industry_name,
                Industries.industry_id != industry_id,
            )
        )
        if dup_check.scalars().first():
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="An industry with this name already exists.",
            )
        industry.industry_name = update_data.industry_name

    if update_data.industry_slug:
        industry.industry_slug = update_data.industry_slug

    await db.commit()
    await db.refresh(industry)

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Industry updated successfully.",
        data=industry,
    )


@router.patch("/{industry_id}/status", summary="Update industry status")
@exception_handler
async def update_industry_status(
    industry_id: str,
    is_active: bool = Query(False, description="Set industry status"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    result = await db.execute(select(Industries).where(Industries.industry_id == industry_id))
    industry = result.scalars().first()

    if not industry:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Industry not found.",
        )

    industry.is_active = is_active
    await db.commit()
    await db.refresh(industry)

    return api_response(
        status_code=status.HTTP_200_OK,
        message=f"Industry status updated to {'Inactive' if is_active else 'Active'}.",
        data=industry,
    )


@router.delete("/{industry_id}", summary="Delete industry by ID (soft or hard)")
@exception_handler
async def delete_industry(
    industry_id: str,
    hard_delete: bool = Query(False, description="Set to true for hard delete"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    result = await db.execute(select(Industries).where(Industries.industry_id == industry_id))
    industry = result.scalars().first()

    if not industry:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Industry not found.",
        )

    if industry.is_active and not hard_delete:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Industry already soft-deleted.",
        )

    if hard_delete:
        await db.delete(industry)
        await db.commit()
        return api_response(
            status_code=status.HTTP_200_OK,
            message="Industry permanently deleted.",
        )
    else:
        industry.is_active = True  # soft-delete flag
        await db.commit()
        return api_response(
            status_code=status.HTTP_200_OK,
            message="Industry soft-deleted successfully.",
        )



@router.get("/by-industry/{industry_id}")
@exception_handler
async def get_categories_by_industry(
    industry_id: str,
    status_filter: Optional[bool] = Query(
        None,
        description="Filter by category/subcategory status: true, false, or omit for all",
    ),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    # Query all categories for the given industry, load subcategories eagerly
    stmt = (
        select(Category)
        .where(Category.industry_id == industry_id)
        .options(selectinload(Category.subcategories))
    )

    if status_filter is not None:
        stmt = stmt.where(Category.category_status == status_filter)

    result = await db.execute(stmt)
    categories = result.scalars().unique().all()

    data = []

    for cat in categories:
        # Filter subcategories if needed
        if status_filter is not None:
            subcats = [
                s for s in cat.subcategories
                if s.subcategory_status == status_filter
            ]
        else:
            subcats = cat.subcategories

        data.append(
            {
                "category_id": cat.category_id,
                "category_name": cat.category_name.title(),
                "category_description": cat.category_description,
                "category_slug": cat.category_slug,
                "category_meta_title": cat.category_meta_title,
                "category_meta_description": cat.category_meta_description,
                "category_img_thumbnail": get_media_url(cat.category_img_thumbnail),
                "featured_category": cat.featured_category,
                "show_in_menu": cat.show_in_menu,
                "category_status": cat.category_status,
                
                "has_subcategories": len(subcats) > 0,
                "subcategory_count": len(subcats),
                "subcategories": [
                    {
                        "subcategory_id": sub.subcategory_id,
                        "subcategory_name": sub.subcategory_name.title(),
                        "subcategory_description": sub.subcategory_description,
                        "subcategory_slug": sub.subcategory_slug,
                        "subcategory_meta_title": sub.subcategory_meta_title,
                        "subcategory_meta_description": sub.subcategory_meta_description,
                        "subcategory_img_thumbnail": get_media_url(sub.subcategory_img_thumbnail),
                        "featured_subcategory": sub.featured_subcategory,
                        "show_in_menu": sub.show_in_menu,
                        "subcategory_status": sub.subcategory_status,
                       
                    }
                    for sub in subcats
                ],
            }
        )

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Categories and subcategories fetched successfully",
        data=data,
    )




@router.get("/by-vendor/{vendor_id}")
@exception_handler
async def get_categories_by_vendor(
    vendor_id: str,
    status_filter: Optional[bool] = Query(
        None,
        description="Filter by category/subcategory status: true, false, or omit for all",
    ),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    # Step 1: Get Vendor -> Business Profile -> Industry ID
    vendor_stmt = (
        select(VendorLogin)
        .options(selectinload(VendorLogin.business_profile))
        .where(VendorLogin.user_id == vendor_id)
    )

    vendor_result = await db.execute(vendor_stmt)
    vendor = vendor_result.scalars().first()

    if not vendor or not vendor.business_profile:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Vendor or associated business profile not found",
        )

    industry_id = vendor.business_profile.industry

    if not industry_id:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Industry not associated with vendor's business profile",
        )

    # Step 2: Fetch categories by industry_id
    stmt = (
        select(Category)
        .where(Category.industry_id == industry_id)
        .options(selectinload(Category.subcategories))
    )

    if status_filter is not None:
        stmt = stmt.where(Category.category_status == status_filter)

    result = await db.execute(stmt)
    categories = result.scalars().unique().all()

    data = []

    for cat in categories:
        # Filter subcategories if needed
        subcats = [
            s for s in cat.subcategories
            if status_filter is None or s.subcategory_status == status_filter
        ]

        data.append(
            {
                "category_id": cat.category_id,
                "category_name": cat.category_name.title(),
                "category_description": cat.category_description,
                "category_slug": cat.category_slug,
                "category_meta_title": cat.category_meta_title,
                "category_meta_description": cat.category_meta_description,
                "category_img_thumbnail": get_media_url(cat.category_img_thumbnail),
                "featured_category": cat.featured_category,
                "show_in_menu": cat.show_in_menu,
                "category_status": cat.category_status,
                "has_subcategories": len(subcats) > 0,
                "subcategory_count": len(subcats),
                "subcategories": [
                    {
                        "subcategory_id": sub.subcategory_id,
                        "subcategory_name": sub.subcategory_name.title(),
                        "subcategory_description": sub.subcategory_description,
                        "subcategory_slug": sub.subcategory_slug,
                        "subcategory_meta_title": sub.subcategory_meta_title,
                        "subcategory_meta_description": sub.subcategory_meta_description,
                        "subcategory_img_thumbnail": get_media_url(sub.subcategory_img_thumbnail),
                        "featured_subcategory": sub.featured_subcategory,
                        "show_in_menu": sub.show_in_menu,
                        "subcategory_status": sub.subcategory_status,
                    }
                    for sub in subcats
                ],
            }
        )

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Categories and subcategories fetched successfully by vendor",
        data=data,
    )
