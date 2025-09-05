from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from slugify import slugify
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from utils.file_uploads import get_media_url
from core.api_response import api_response
from core.status_codes import APIResponse, StatusCode
from db.models.superadmin import Category, Industries, SubCategory, VendorLogin  
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
    # Case-insensitive duplicate check (industry_name is already validated and stripped by schema)
    result = await db.execute(
        select(Industries).where(func.upper(Industries.industry_name) == func.upper(industry.industry_name))
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
            # Check if the new slug conflicts with existing active industries
            if existing.industry_slug != industry.industry_slug:
                slug_result = await db.execute(
                    select(Industries).where(
                        Industries.industry_slug == industry.industry_slug,
                        Industries.is_active == False
                    )
                )
                existing_slug = slug_result.scalars().first()
                
                if existing_slug:
                    return api_response(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        message="An industry with this slug already exists.",
                        log_error=True,
                    )
            
            existing.is_active = False
            existing.industry_name = industry.industry_name  # Already processed by schema
            existing.industry_slug = industry.industry_slug  # Already processed by schema
            existing.timestamp = datetime.now()
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

    # Check for duplicate slug
    slug_result = await db.execute(
        select(Industries).where(Industries.industry_slug == industry.industry_slug)
    )
    existing_slug = slug_result.scalars().first()
    
    if existing_slug:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="An industry with this slug already exists.",
            log_error=True,
        )

    industry_id = generate_digits_lowercase()
    # Store industry data (name and slug already processed by schema)
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

    # Check if industry is inactive before allowing updates
    if industry.is_active:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Cannot update an inactive industry."
        )

    if update_data.industry_name:
        if is_single_reserved_word(update_data.industry_name):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Reserved words are not allowed in industry names.",
            )

        # Case-insensitive duplicate check (industry_name is already validated and stripped by schema)
        dup_check = await db.execute(
            select(Industries).where(
                func.upper(Industries.industry_name) == func.upper(update_data.industry_name),
                Industries.industry_id != industry_id,
            )
        )
        if dup_check.scalars().first():
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="An industry with this name already exists.",
            )
        # Store industry name in uppercase for consistency (already handled by schema)
        industry.industry_name = update_data.industry_name

    if update_data.industry_slug:
        # Check for duplicate slug
        slug_check = await db.execute(
            select(Industries).where(
                Industries.industry_slug == update_data.industry_slug,
                Industries.industry_id != industry_id,
            )
        )
        if slug_check.scalars().first():
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="An industry with this slug already exists.",
            )
        # Store industry slug (already handled by schema)
        industry.industry_slug = update_data.industry_slug

    await db.commit()
    await db.refresh(industry)

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Industry updated successfully.",
        data=industry,
    )


@router.patch("/status/{industry_id}", summary="Update industry status")
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
        message=f"Industry status updated to {'Active' if not is_active else 'Inactive'}.",
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

    # Handle already soft-deleted industry
    if industry.is_active is True:
        if not hard_delete:
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Industry is already soft-deleted.",
                log_error=False,
            )
        # Proceed with hard delete
        await db.delete(industry)
        await db.commit()
        return api_response(
            status_code=status.HTTP_200_OK,
            message="Industry permanently deleted (hard delete).",
        )

    if hard_delete:
        await db.delete(industry)
        await db.commit()
        return api_response(
            status_code=status.HTTP_200_OK,
            message="Industry permanently deleted (hard delete).",
        )
    else:
        industry.is_active = True  # Soft delete
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


@router.get("/industries/full", summary="Get active industries with categories and subcategories")
@exception_handler
async def get_all_industries_with_categories_and_subcategories(
    db: AsyncSession = Depends(get_db),
):
    # Join industries → categories → subcategories with filters
    stmt = (
        select(Industries, Category, SubCategory)
        .join(Category, Category.industry_id == Industries.industry_id, isouter=True)
        .join(SubCategory, SubCategory.category_id == Category.category_id, isouter=True)
        .where(
            Industries.is_active == False,           # only active industries
            or_(Category.category_status == False, Category.category_status.is_(None)),  # active categories
            or_(SubCategory.subcategory_status == False, SubCategory.subcategory_status.is_(None))  # active subcategories
        )
    )

    result = await db.execute(stmt)
    rows = result.all()

    if not rows:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="No active industries found.",
            log_error=True,
        )

    # Build nested structure manually
    industries_dict: dict[str, dict] = {}

    for industry, category, subcategory in rows:
        if industry.industry_id not in industries_dict:
            industries_dict[industry.industry_id] = {
                "industry_id": industry.industry_id,
                "industry_name": industry.industry_name,
                "industry_slug": industry.industry_slug,
                "categories": {},
            }

        if category and category.category_status == False:  # active category
            if category.category_id not in industries_dict[industry.industry_id]["categories"]:
                industries_dict[industry.industry_id]["categories"][category.category_id] = {
                    "category_id": category.category_id,
                    "category_name": category.category_name,
                    "category_slug": category.category_slug,
                    "subcategories": [],
                }

            if subcategory and subcategory.subcategory_status == False:  # active subcategory
                industries_dict[industry.industry_id]["categories"][category.category_id]["subcategories"].append({
                    "subcategory_id": subcategory.subcategory_id,
                    "subcategory_name": subcategory.subcategory_name,
                    "subcategory_slug": subcategory.subcategory_slug,
                })

    # Convert categories dict back to list
    data = []
    for industry in industries_dict.values():
        industry["categories"] = list(industry["categories"].values())
        data.append(industry)

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Active industries with categories and subcategories retrieved successfully.",
        data=data,
    )
