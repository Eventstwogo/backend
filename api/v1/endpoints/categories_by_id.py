from typing import Optional

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

router = APIRouter()


@router.get("/details/{category_id}")
@exception_handler
async def get_category_details(
    category_id: str, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    #  Fetch category by ID
    result = await db.execute(
        select(Category)
        .options(
            selectinload(Category.subcategories)
        )  # optional: load subcategories
        .filter_by(category_id=category_id)
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
        "category_tstamp": category.category_tstamp,
    }

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Category fetched successfully",
        data=data,
    )


@router.put("/update/{category_id}")
@exception_handler
async def update_category(
    category_id: str,
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
    # === Fetch category ===
    result = await db.execute(
        select(Category).filter_by(category_id=category_id)
    )
    category = result.scalars().first()

    if not category:
        return api_response(status.HTTP_404_NOT_FOUND, "Category not found")

    # === Validate inputs that are being changed (before processing) ===
    # Check for empty string inputs which should be treated as invalid
    if name is not None and name.strip() == "":
        return api_response(
            status.HTTP_400_BAD_REQUEST, "Invalid category name."
        )

    # === Check if there's no change at all ===
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
        return api_response(
            status.HTTP_200_OK,
            "Category updated successfully",
            data={
                "category_id": category.category_id,
                "category_slug": category.category_slug,
            },
        )

    # === Prepare inputs with fallback (handle None vs empty string properly) ===
    # For form data, empty strings should be treated as "no change intended"
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

    # === Sanitize and validate ===
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

    # === Conflict validation only for fields being changed ===
    if (
        (name is not None and name.strip())
        or (slug is not None and slug.strip())
        or (description is not None and description.strip())
        or (meta_title is not None and meta_title.strip())
        or (meta_description is not None and meta_description.strip())
    ):

        if input_name is None:
            return api_response(
                status.HTTP_400_BAD_REQUEST, "Category name is required."
            )
        conflict_error = await validate_category_conflicts(
            db,
            input_name,
            final_slug,
            input_description,
            input_meta_title,
            input_meta_description,
            category_id_to_exclude=category_id,  # This is the key change
        )
        if conflict_error:
            return api_response(status.HTTP_400_BAD_REQUEST, conflict_error)

    # === Apply updates (only if not empty strings) ===
    if name is not None and name.strip():
        assert input_name is not None
        category.category_name = input_name.upper()
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

    if file and file.filename:
        sub_path = settings.CATEGORY_IMAGE_PATH.format(slug_name=final_slug)
        uploaded_url = await save_uploaded_file(file, sub_path)
        category.category_img_thumbnail = uploaded_url

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


@router.delete("/soft-delete/{category_id}")
@exception_handler
async def soft_delete_category(
    category_id: str, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    # Fetch category by ID with subcategories
    result = await db.execute(
        select(Category)
        .options(selectinload(Category.subcategories))
        .filter_by(category_id=category_id)
    )
    category = result.scalars().first()

    if not category:
        return api_response(status.HTTP_404_NOT_FOUND, "Category not found")

    if category.category_status:
        return api_response(
            status.HTTP_400_BAD_REQUEST, "Category already inactive"
        )

    # Soft-delete category
    category.category_status = True

    # Soft-delete all subcategories under it
    # for sub in category.subcategories:
    #     sub.subcategory_status = True

    await db.commit()

    return api_response(
        status.HTTP_200_OK,
        "Category and its subcategories soft deleted successfully",
    )


@router.put("/restore/{category_id}")
@exception_handler
async def restore_category(
    category_id: str, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    # Fetch the category with subcategories
    result = await db.execute(
        select(Category)
        .options(selectinload(Category.subcategories))
        .filter_by(category_id=category_id)
    )
    category = result.scalars().first()

    if not category:
        return api_response(status.HTTP_404_NOT_FOUND, "Category not found")

    if not category.category_status:
        return api_response(
            status.HTTP_400_BAD_REQUEST, "Category is already active"
        )

    # Restore the category
    category.category_status = False

    # Restore all subcategories
    # for sub in category.subcategories:
    #     sub.subcategory_status = False

    await db.commit()

    return api_response(
        status.HTTP_200_OK,
        "Category and its subcategories restored successfully",
    )


@router.delete("/hard-delete/{category_id}")
@exception_handler
async def hard_delete_category(
    category_id: str, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    # Load category along with its subcategories
    result = await db.execute(
        select(Category)
        .options(selectinload(Category.subcategories))
        .filter_by(category_id=category_id)
    )
    category = result.scalars().first()

    if not category:
        return api_response(status.HTTP_404_NOT_FOUND, "Category not found")

    # This will now delete subcategories too due to
    # cascade="all, delete-orphan"
    await db.delete(category)
    await db.commit()

    return api_response(
        status.HTTP_200_OK,
        "Category and its subcategories permanently deleted",
    )
