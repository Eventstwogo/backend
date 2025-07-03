from datetime import datetime
from typing import Optional, cast

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    UploadFile,
    status,
)
from slugify import slugify
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from starlette.responses import JSONResponse

from core.api_response import api_response
from core.config import settings
from db.models.superadmin import Category
from db.sessions.database import get_db
from services.category_service import (
    validate_category_conflicts,
    validate_category_data,
)
from utils.exception_handlers import exception_handler
from utils.file_uploads import get_media_url, save_uploaded_file
from utils.format_validators import is_valid_filename
from utils.security_validators import sanitize_input
from utils.validators import normalize_whitespace

router = APIRouter()


@router.get("/slug/{slug}")
@exception_handler
async def get_category_by_slug(
    slug: str, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    result = await db.execute(
        select(Category)
        .options(selectinload(Category.subcategories))
        .filter_by(category_slug=slug)
    )
    category = result.scalars().first()

    if not category:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Category not found",
        )

    data = {
        "category_id": category.category_id,
        "category_name": category.category_name.title(),
        "category_description": category.category_description,
        "category_slug": category.category_slug,
        "category_meta_title": category.category_meta_title,
        "category_meta_description": category.category_meta_description,
        "category_img_thumbnail": get_media_url(
            category.category_img_thumbnail
        ),
        "featured_category": category.featured_category,
        "show_in_menu": category.show_in_menu,
        "category_status": category.category_status,
        "category_tstamp": (
            cast(datetime, category.category_tstamp).isoformat()
            if category.category_tstamp
            else None
        ),
        "subcategories": [
            {
                "subcategory_id": sub.subcategory_id,
                "subcategory_name": sub.subcategory_name.title(),
                "subcategory_description": (sub.subcategory_description),
                "subcategory_slug": sub.subcategory_slug,
                "subcategory_meta_title": sub.subcategory_meta_title,
                "subcategory_meta_description": (
                    sub.subcategory_meta_description
                ),
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
            for sub in category.subcategories
        ],
    }

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Category fetched successfully",
        data=data,
    )


@router.put("/update/by-slug/{category_slug}")
@exception_handler
async def update_category_by_slug(
    category_slug: str,
    name: Optional[str] = Form(None),
    slug: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    meta_title: Optional[str] = Form(None),
    meta_description: Optional[str] = Form(None),
    featured: Optional[bool] = Form(None),
    show_in_menu: Optional[bool] = Form(None),
    file: UploadFile = File(None),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    result = await db.execute(
        select(Category).filter_by(category_slug=category_slug)
    )
    category = result.scalars().first()

    if not category:
        return api_response(status.HTTP_404_NOT_FOUND, "Category not found")

    # Check if no changes at all
    no_change = (
        (name is None or name.strip() == "")
        and (slug is None or slug.strip() == "")
        and (description is None or description.strip() == "")
        and (meta_title is None or meta_title.strip() == "")
        and (meta_description is None or meta_description.strip() == "")
        and (featured is None or featured == category.featured_category)
        and (show_in_menu is None or show_in_menu == category.show_in_menu)
        and not (file and file.filename)
    )
    if no_change:
        return api_response(status.HTTP_400_BAD_REQUEST, "No changes detected.")

    # Prepare new values with fallback
    input_name = (
        category.category_name if (name is None or name.strip() == "") else name
    )
    input_slug = (
        category.category_slug if (slug is None or slug.strip() == "") else slug
    )
    input_description = (
        category.category_description
        if (description is None or description.strip() == "")
        else description
    )
    input_meta_title = (
        category.category_meta_title
        if (meta_title is None or meta_title.strip() == "")
        else meta_title
    )
    input_meta_description = (
        category.category_meta_description
        if (meta_description is None or meta_description.strip() == "")
        else meta_description
    )

    # Sanitize inputs
    input_name = (
        normalize_whitespace(sanitize_input(input_name)) if input_name else ""
    )
    input_slug = (
        normalize_whitespace(sanitize_input(input_slug)) if input_slug else ""
    )
    input_description = (
        normalize_whitespace(sanitize_input(input_description))
        if input_description
        else ""
    )
    input_meta_title = (
        normalize_whitespace(sanitize_input(input_meta_title))
        if input_meta_title
        else ""
    )
    input_meta_description = (
        normalize_whitespace(sanitize_input(input_meta_description))
        if input_meta_description
        else ""
    )

    # Validate format if changed
    if (
        (name is not None and name.strip())
        or (slug is not None and slug.strip())
        or (description is not None and description.strip())
        or (meta_title is not None and meta_title.strip())
        or (meta_description is not None and meta_description.strip())
    ):
        (
            input_name,
            input_slug,
            input_description,
            input_meta_title,
            input_meta_description,
        ) = validate_category_data(
            input_name,
            input_slug,
            input_description,
            input_meta_title,
            input_meta_description,
            is_subcategory=False,
        )

    final_slug = slugify(input_slug)

    # Conflict check if anything was changed
    if (
        (name is not None and name.strip())
        or (slug is not None and slug.strip())
        or (description is not None and description.strip())
        or (meta_title is not None and meta_title.strip())
        or (meta_description is not None and meta_description.strip())
    ):

        if input_name is None:
            return api_response(
                status.HTTP_400_BAD_REQUEST, "Category Name is required."
            )
        conflict_error = await validate_category_conflicts(
            db=db,
            name=input_name,
            slug=final_slug,
            description=input_description,
            meta_title=input_meta_title,
            meta_description=input_meta_description,
            category_id_to_exclude=category.category_id,  # ✅ skip self
        )
        if conflict_error:
            return api_response(status.HTTP_400_BAD_REQUEST, conflict_error)

    # Apply changes
    if name is not None and name.strip():
        category.category_name = name.upper()
    if slug is not None and slug.strip():
        category.category_slug = final_slug
    if description is not None and description.strip():
        category.category_description = input_description
    if meta_title is not None and meta_title.strip():
        category.category_meta_title = input_meta_title
    if meta_description is not None and meta_description.strip():
        category.category_meta_description = input_meta_description
    if featured is not None:
        category.featured_category = featured
    if show_in_menu is not None:
        category.show_in_menu = show_in_menu

    # Handle file upload
    if file and file.filename:
        if not is_valid_filename(file.filename):
            return api_response(
                status.HTTP_400_BAD_REQUEST, "Invalid file name."
            )
        sub_path = settings.CATEGORY_IMAGE_PATH.format(slug_name=final_slug)
        try:
            uploaded_url = await save_uploaded_file(file, sub_path)
            category.category_img_thumbnail = uploaded_url
        except ValueError as ve:
            return api_response(status.HTTP_400_BAD_REQUEST, str(ve))
        except Exception as e:
            return api_response(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Failed to save uploaded file: {str(e)}",
                log_error=True,
            )

    await db.commit()
    await db.refresh(category)

    return api_response(
        status.HTTP_200_OK,
        "Category updated successfully",
        data={
            "category_id": category.category_id,
            "category_slug": category.category_slug,
        },
    )


@router.delete("/soft-delete/by-slug/{category_slug}")
@exception_handler
async def soft_delete_category_by_slug(
    category_slug: str, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    result = await db.execute(
        select(Category)
        .options(selectinload(Category.subcategories))
        .filter_by(category_slug=category_slug)
    )
    category = result.scalars().first()

    if not category:
        return api_response(status.HTTP_404_NOT_FOUND, "Category not found")

    category.category_status = True
    for subcategory in category.subcategories:
        subcategory.subcategory_status = True

    await db.commit()
    return api_response(
        status.HTTP_200_OK,
        "Category and subcategories soft deleted successfully",
    )


@router.put("/restore/by-slug/{category_slug}")
@exception_handler
async def restore_category_by_slug(
    category_slug: str, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    result = await db.execute(
        select(Category)
        .options(selectinload(Category.subcategories))
        .filter_by(category_slug=category_slug)
    )
    category = result.scalars().first()

    if not category:
        return api_response(status.HTTP_404_NOT_FOUND, "Category not found")

    category.category_status = False
    for subcategory in category.subcategories:
        subcategory.subcategory_status = False

    await db.commit()
    return api_response(
        status.HTTP_200_OK,
        "Category and subcategories restored successfully",
    )


@router.delete("/hard-delete/by-slug/{category_slug}")
@exception_handler
async def hard_delete_category_by_slug(
    category_slug: str, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    result = await db.execute(
        select(Category)
        .options(selectinload(Category.subcategories))
        .filter_by(category_slug=category_slug)
    )
    category = result.scalars().first()

    if not category:
        return api_response(status.HTTP_404_NOT_FOUND, "Category not found")

    await db.delete(category)
    await db.commit()

    return api_response(
        status.HTTP_200_OK,
        "Category and its subcategories permanently deleted",
    )
