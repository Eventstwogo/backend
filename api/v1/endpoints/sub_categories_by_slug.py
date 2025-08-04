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
from db.models.superadmin import SubCategory, Category, Industries
from db.sessions.database import get_db
from services.category_service import (
    check_subcategory_conflicts,
    check_subcategory_vs_category_conflicts,
    validate_subcategory_fields,
)
from utils.exception_handlers import exception_handler
from utils.file_uploads import get_media_url, save_uploaded_file
from utils.format_validators import is_valid_filename

router = APIRouter()


@router.get("/slug/{slug}")
@exception_handler
async def get_subcategory_by_slug(
    slug: str, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    # Fetch subcategory by slug with parent category
    result = await db.execute(
        select(SubCategory)
        .options(selectinload(SubCategory.category))
        .filter_by(subcategory_slug=slug)
    )
    sub = result.scalars().first()

    if not sub:
        return api_response(status.HTTP_404_NOT_FOUND, "Subcategory not found")

    data = {
        "subcategory_id": sub.subcategory_id,
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
        "parent_category": (
            {
                "category_id": sub.category.category_id,
                "category_name": sub.category.category_name,
                "category_slug": sub.category.category_slug,
            }
            if sub.category
            else None
        ),
    }

    return api_response(
        status.HTTP_200_OK, "Subcategory fetched successfully", data=data
    )


@router.put("/update/slug/{slug}")
@exception_handler
async def update_subcategory_by_slug(
    slug: str,
    name: Optional[str] = Form(None),
    new_slug: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    meta_title: Optional[str] = Form(None),
    meta_description: Optional[str] = Form(None),
    featured: Optional[bool] = Form(None),
    show_in_menu: Optional[bool] = Form(None),
    file: UploadFile = File(None),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    # Fetch subcategory by slug
    result = await db.execute(
        select(SubCategory).filter_by(subcategory_slug=slug)
    )
    subcategory = result.scalars().first()

    if not subcategory:
        return api_response(status.HTTP_404_NOT_FOUND, "Subcategory not found")



    #  Apply fallback for unchanged fields
    name_updated = name is not None and name.strip() != ""
    input_name = name or subcategory.subcategory_name
    # If name is updated but no slug provided, use the updated name for slug
    if name_updated and not new_slug:
        input_slug = input_name
    else:
        input_slug = new_slug or subcategory.subcategory_slug
    input_description = description or subcategory.subcategory_description
    input_meta_title = meta_title or subcategory.subcategory_meta_title
    input_meta_description = (
        meta_description or subcategory.subcategory_meta_description
    )

    #  Validate fields
    (
        cleaned_name,
        cleaned_slug,
        cleaned_description,
        cleaned_meta_title,
        cleaned_meta_description,
    ) = validate_subcategory_fields(
        name=input_name,
        slug=input_slug,
        description=input_description,
        meta_title=input_meta_title,
        meta_description=input_meta_description,
    )

    final_slug = slugify(cleaned_slug)

    #  Check for subcategory conflicts
    conflict_error = await check_subcategory_conflicts(
        db=db,
        name=cleaned_name,
        slug=final_slug,
        description=cleaned_description,
        meta_title=cleaned_meta_title,
        meta_description=cleaned_meta_description,
        subcategory_id_to_exclude=subcategory.subcategory_id,
    )
    if conflict_error:
        return api_response(status.HTTP_400_BAD_REQUEST, conflict_error)

    #  Check for category conflicts
    conflict_error = await check_subcategory_vs_category_conflicts(
        db=db,
        name=cleaned_name,
        slug=final_slug,
        description=cleaned_description,
        meta_title=cleaned_meta_title,
        meta_description=cleaned_meta_description,
    )
    if conflict_error:
        return api_response(status.HTTP_400_BAD_REQUEST, conflict_error)

    #  Update fields
    if name:
        subcategory.subcategory_name = cleaned_name.upper()
    # Update slug if explicitly provided OR if name was updated
    if new_slug or name_updated:
        subcategory.subcategory_slug = final_slug
    if description:
        subcategory.subcategory_description = cleaned_description
    if meta_title:
        subcategory.subcategory_meta_title = cleaned_meta_title
    if meta_description:
        subcategory.subcategory_meta_description = cleaned_meta_description
    if featured is not None:
        subcategory.featured_subcategory = featured
    if show_in_menu is not None:
        subcategory.show_in_menu = show_in_menu

    #  Handle file upload
    if file and file.filename:
        if not is_valid_filename(file.filename):
            return api_response(
                status.HTTP_400_BAD_REQUEST, "Invalid file name."
            )

        sub_path = settings.SUBCATEGORY_IMAGE_PATH.format(
            category_id=subcategory.category_id, slug_name=final_slug
        )

        try:
            uploaded_url = await save_uploaded_file(file, sub_path)
            subcategory.subcategory_img_thumbnail = uploaded_url
        except ValueError as ve:
            return api_response(status.HTTP_400_BAD_REQUEST, str(ve))
        except Exception as e:
            return api_response(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Failed to save uploaded file: {str(e)}",
                log_error=True,
            )

    #  Commit changes
    await db.commit()
    await db.refresh(subcategory)

    return api_response(
        status.HTTP_200_OK,
        "Subcategory updated successfully",
        data={
            "subcategory_id": subcategory.subcategory_id,
            "subcategory_slug": subcategory.subcategory_slug,
            "subcategory_name": subcategory.subcategory_name,
        },
    )


@router.delete("/soft-delete/slug/{slug}")
@exception_handler
async def soft_delete_subcategory_by_slug(
    slug: str, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    result = await db.execute(
        select(SubCategory).filter_by(subcategory_slug=slug)
    )
    subcategory = result.scalars().first()

    if not subcategory:
        return api_response(status.HTTP_404_NOT_FOUND, "Subcategory not found")

    if subcategory.subcategory_status:
        return api_response(
            status.HTTP_400_BAD_REQUEST, "Subcategory already inactive"
        )

    subcategory.subcategory_status = True
    await db.commit()

    return api_response(
        status.HTTP_200_OK, "Subcategory soft deleted successfully"
    )


@router.put("/restore/slug/{slug}")
@exception_handler
async def restore_subcategory_by_slug(
    slug: str, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    result = await db.execute(
        select(SubCategory).filter_by(subcategory_slug=slug)
    )
    subcategory = result.scalars().first()

    if not subcategory:
        return api_response(status.HTTP_404_NOT_FOUND, "Subcategory not found")

    if not subcategory.subcategory_status:
        return api_response(
            status.HTTP_400_BAD_REQUEST, "Subcategory is already active"
        )

    subcategory.subcategory_status = False
    await db.commit()

    return api_response(status.HTTP_200_OK, "Subcategory restored successfully")


@router.delete("/hard-delete/slug/{slug}")
@exception_handler
async def hard_delete_subcategory_by_slug(
    slug: str, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    result = await db.execute(
        select(SubCategory).filter_by(subcategory_slug=slug)
    )
    subcategory = result.scalars().first()

    if not subcategory:
        return api_response(status.HTTP_404_NOT_FOUND, "Subcategory not found")

    await db.delete(subcategory)
    await db.commit()

    return api_response(status.HTTP_200_OK, "Subcategory permanently deleted")
