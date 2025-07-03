from datetime import datetime
from typing import List, Optional, cast

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Query,
    UploadFile,
    status,
)
from slugify import slugify
from sqlalchemy import case, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from starlette.responses import JSONResponse

from core.api_response import api_response
from core.status_codes import APIResponse, StatusCode
from db.models.superadmin import Category, SubCategory
from db.sessions.database import get_db
from schemas.categories import CategoryOut
from services.category_service import (
    check_category_description_exists,
    check_category_meta_title_exists,
    check_category_name_exists,
    check_category_slug_exists,
    validate_category_conflicts,
    validate_category_data,
    validate_subcategory_conflicts,
)
from utils.exception_handlers import exception_handler
from utils.file_uploads import get_media_url, save_uploaded_file
from utils.id_generators import (
    generate_digits_lowercase,
    generate_digits_uppercase,
    generate_lower_uppercase,
)

router = APIRouter()


@router.post("/create")
@exception_handler
async def create_category_or_subcategory(
    category_id: Optional[str] = Form(None),
    name: str = Form(...),
    slug: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    meta_title: Optional[str] = Form(None),
    meta_description: Optional[str] = Form(None),
    featured: bool = Form(False),
    show_in_menu: bool = Form(True),
    file: UploadFile = File(None),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    is_subcategory = bool(category_id)

    # Sanitize and validate inputs
    name, slug, description, meta_title, meta_description = (
        validate_category_data(
            name,
            slug,
            description,
            meta_title,
            meta_description,
            is_subcategory,
        )
    )

    check_category_name_exists(db, name)
    check_category_slug_exists(db, slug)
    check_category_description_exists(db, description)
    check_category_meta_title_exists(db, meta_title)



    final_slug = slugify(slug)

    if is_subcategory:
        # Subcategory: validate parent category
        result = await db.execute(
            select(Category).where(Category.category_id == category_id)
        )
        parent_category = result.scalars().first()
        if not parent_category:
            return api_response(
                status.HTTP_404_NOT_FOUND, "Parent category not found"
            )

        # Check for subcategory conflicts
        conflict_error = await validate_subcategory_conflicts(
            db, name, final_slug, description, meta_title, meta_description
        )
        if conflict_error:
            return api_response(
                status.HTTP_400_BAD_REQUEST, conflict_error, log_error=True
            )

        # Create SubCategory
        new_subcategory = SubCategory(
            id=generate_lower_uppercase(6),
            subcategory_id=generate_digits_lowercase(6),
            category_id=category_id,
            subcategory_name=name,
            subcategory_slug=final_slug,
            subcategory_description=description,
            subcategory_meta_title=meta_title,
            subcategory_meta_description=meta_description,
            featured_subcategory=featured,
            show_in_menu=show_in_menu,
        )

        sub_path = f"subcategories/{category_id}/{final_slug}"
        uploaded_url = await save_uploaded_file(file, sub_path)
        if uploaded_url:
            new_subcategory.subcategory_img_thumbnail = uploaded_url

        db.add(new_subcategory)
        await db.commit()
        await db.refresh(new_subcategory)

        return api_response(
            status.HTTP_201_CREATED,
            "Subcategory created successfully",
            data={"subcategory_id": new_subcategory.subcategory_id},
        )

    # Category creation
    conflict_error = await validate_category_conflicts(
        db, name, final_slug, description, meta_title, meta_description
    )
    if conflict_error:
        return api_response(
            status.HTTP_400_BAD_REQUEST, conflict_error, log_error=True
        )

    # Create Category
    new_category = Category(
        category_id=generate_digits_uppercase(6),
        category_name=name,
        category_slug=final_slug,
        category_description=description,
        category_meta_title=meta_title,
        category_meta_description=meta_description,
        featured_category=featured,
        show_in_menu=show_in_menu,
    )

    cat_path = f"categories/{final_slug}"
    uploaded_url = await save_uploaded_file(file, cat_path)
    if uploaded_url:
        new_category.category_img_thumbnail = uploaded_url

    db.add(new_category)
    await db.commit()
    await db.refresh(new_category)

    return api_response(
        status_code=status.HTTP_201_CREATED,
        message="Category created successfully",
        data={"category_id": new_category.category_id},
    )


@router.get("/")
@exception_handler
async def get_all_categories(
    status_filter: Optional[bool] = Query(
        None,
        description="Filter by category status: true, false, or omit for all",
    ),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    # Load categories with subcategories
    stmt = select(Category).options(selectinload(Category.subcategories))

    if status_filter is not None:
        stmt = stmt.where(Category.category_status == status_filter)

    result = await db.execute(stmt)
    categories = result.scalars().unique().all()

    data = []

    for cat in categories:
        # Filter subcategories by status_filter
        if status_filter is not None:
            subcats = [
                s
                for s in cat.subcategories
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
                "category_img_thumbnail": get_media_url(
                    cat.category_img_thumbnail
                ),
                "featured_category": cat.featured_category,
                "show_in_menu": cat.show_in_menu,
                "category_status": cat.category_status,
                "category_tstamp": (
                    cast(datetime, cat.category_tstamp).isoformat()
                    if cat.category_tstamp
                    else None
                ),
                "has_subcategories": len(subcats) > 0,
                "subcategory_count": len(subcats),
            }
        )

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Categories fetched successfully",
        data=data,
    )


@router.get("/analytics")
@exception_handler
async def category_analytics(
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    # Optimized Aggregation Query
    stats_query = await db.execute(
        select(
            func.count().label("total"),
            func.count(case((Category.category_status, 1))).label("active"),
            func.count(case((Category.category_status, 1))).label("inactive"),
            func.count(case((Category.featured_category.is_(True), 1))).label(
                "featured"
            ),
            func.count(case((Category.show_in_menu.is_(True), 1))).label(
                "show_in_menu"
            ),
            func.count(case((Category.show_in_menu.is_(False), 1))).label(
                "hidden_from_menu"
            ),
        )
    )
    stats = stats_query.first()

    # Subcategory Stats in One ORM Query
    result = await db.execute(
        select(Category).options(selectinload(Category.subcategories))
    )
    categories = result.scalars().all()

    total_subcategories = 0
    categories_with_subs = 0
    subcategory_distribution = []

    for category in categories:
        sub_count = len(category.subcategories)
        total_subcategories += sub_count
        if sub_count > 0:
            categories_with_subs += 1
        subcategory_distribution.append(
            {
                "category_name": category.category_name,
                "subcategory_count": sub_count,
            }
        )

    total_categories = getattr(stats, "total", 0) if stats else 0
    avg_subcategories_per_category = (
        total_subcategories / total_categories if total_categories else 0
    )

    top_categories_by_subs = sorted(
        subcategory_distribution,
        key=lambda x: x["subcategory_count"],
        reverse=True,
    )[:5]

    return api_response(
        status.HTTP_200_OK,
        "Category analytics fetched successfully",
        data={
            "totals": {
                "total_categories": getattr(stats, "total", 0),
                "active_categories": getattr(stats, "active", 0),
                "inactive_categories": getattr(stats, "inactive", 0),
                "featured_categories": getattr(stats, "featured", 0),
                "show_in_menu": getattr(stats, "show_in_menu", 0),
                "hidden_from_menu": getattr(stats, "hidden_from_menu", 0),
            },
            "subcategory_stats": {
                "total_subcategories": total_subcategories,
                "categories_with_subcategories": (categories_with_subs),
                "avg_subcategories_per_category": round(
                    avg_subcategories_per_category, 2
                ),
                "top_categories_by_subcategory_count": top_categories_by_subs,
            },
        },
    )


@router.get(
    "/list-categories",
    response_model=List[CategoryOut],
    summary="Fetch all categories and subcategories by status",
)
@exception_handler
async def get_categories_and_subcategories_by_status(
    status_value: Optional[bool] = Query(
        None, description="Filter by category status: true / false / none"
    ),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    stmt = select(Category).options(selectinload(Category.subcategories))

    # Apply category status filter if provided
    if status_value is not None:
        stmt = stmt.where(Category.category_status.is_(status_value))

    result = await db.execute(stmt)
    categories = result.scalars().unique().all()

    for category in categories:
        category.category_name = category.category_name.title()

        if category.category_status:
            # If category is active, override subcategory status to True in response
            for sub in category.subcategories:
                sub.subcategory_status = True

        for sub in category.subcategories:
            sub.subcategory_name = sub.subcategory_name.title()

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Categories fetched successfully",
        data=categories,
    )


@router.get("/total_categories_count")
@exception_handler
async def total_categories_count(
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    # Category aggregation
    category_query = await db.execute(
        select(
            func.count().label("total"),
            func.count(case((Category.category_status.is_(False), 1))).label(
                "active"
            ),
            func.count(case((Category.category_status.is_(True), 1))).label(
                "inactive"
            ),
        )
    )
    category_stats = category_query.first()

    # Subcategory aggregation
    subcategory_query = await db.execute(
        select(
            func.count().label("total"),
            func.count(
                case((SubCategory.subcategory_status.is_(False), 1))
            ).label("active"),
            func.count(
                case((SubCategory.subcategory_status.is_(True), 1))
            ).label("inactive"),
        )
    )
    subcategory_stats = subcategory_query.first()

    # Load category names with subcategory stats
    result = await db.execute(
        select(Category).options(selectinload(Category.subcategories))
    )
    categories = result.scalars().all()

    category_distribution = []
    for cat in categories:
        total = len(cat.subcategories)
        active = sum(
            1 for s in cat.subcategories if s.subcategory_status is False
        )
        inactive = sum(
            1 for s in cat.subcategories if s.subcategory_status is True
        )

        category_distribution.append(
            {
                "category_name": cat.category_name,
                "total_subcategories": total,
                "active_subcategories": active,
                "inactive_subcategories": inactive,
            }
        )

    return api_response(
        status.HTTP_200_OK,
        "Category total count fetched successfully",
        data={
            "totals": {
                "total_categories": getattr(category_stats, "total", 0),
                "active_categories": getattr(category_stats, "active", 0),
                "inactive_categories": getattr(category_stats, "inactive", 0),
            },
            "subcategory_stats": {
                "total_subcategories": getattr(subcategory_stats, "total", 0),
                "active_subcategories": getattr(subcategory_stats, "active", 0),
                "inactive_subcategories": getattr(
                    subcategory_stats, "inactive", 0
                ),
                "category_distribution": category_distribution,
            },
        },
    )
