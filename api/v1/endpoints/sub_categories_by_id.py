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
from db.models.superadmin import SubCategory
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


@router.get("/{subcategory_id}")
@exception_handler
async def get_subcategory_by_id(
    subcategory_id: str, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    # Load subcategory with related parent category
    result = await db.execute(
        select(SubCategory)
        .options(
            selectinload(SubCategory.category)
        )  # Eager load parent category
        .filter_by(subcategory_id=subcategory_id)
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
            sub.subcategory_tstamp.isoformat()
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
        status_code=status.HTTP_200_OK,
        message="Subcategory fetched successfully",
        data=data,
    )


@router.put("/update/{subcategory_id}")
@exception_handler
async def update_subcategory(
    subcategory_id: str,
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
        select(SubCategory).filter_by(subcategory_id=subcategory_id)
    )
    subcategory = result.scalars().first()

    if not subcategory:
        return api_response(status.HTTP_404_NOT_FOUND, "Subcategory not found")



    # === Detect No Change ===
    no_change = (
        (name is None or name.strip() == "")
        and (slug is None or slug.strip() == "")
        and (description is None or description.strip() == "")
        and (meta_title is None or meta_title.strip() == "")
        and (meta_description is None or meta_description.strip() == "")
        and (featured is None or featured == subcategory.featured_subcategory)
        and (show_in_menu is None or show_in_menu == subcategory.show_in_menu)
        and not (file and file.filename)
    )
    if no_change:
        return api_response(status.HTTP_400_BAD_REQUEST, "No changes detected.")

    # === Prepare input values with fallback ===
    input_name = (
        subcategory.subcategory_name
        if (name is None or name.strip() == "")
        else name
    )
    input_slug = (
        subcategory.subcategory_slug
        if (slug is None or slug.strip() == "")
        else slug
    )
    input_description = (
        subcategory.subcategory_description
        if (description is None or description.strip() == "")
        else description
    )
    input_meta_title = (
        subcategory.subcategory_meta_title
        if (meta_title is None or meta_title.strip() == "")
        else meta_title
    )
    input_meta_description = (
        subcategory.subcategory_meta_description
        if (meta_description is None or meta_description.strip() == "")
        else meta_description
    )

    # === Validate fields using utility ===
    (
        input_name,
        input_slug,
        input_description,
        input_meta_title,
        input_meta_description,
    ) = validate_subcategory_fields(
        name=input_name,
        slug=input_slug,
        description=input_description,
        meta_title=input_meta_title,
        meta_description=input_meta_description,
    )
    final_slug = slugify(input_slug)

    # === Check for conflicts (subcategory vs subcategory) ===
    conflict_error = await check_subcategory_conflicts(
        db=db,
        name=input_name,
        slug=final_slug,
        description=input_description,
        meta_title=input_meta_title,
        meta_description=input_meta_description,
        subcategory_id_to_exclude=subcategory_id,
    )
    if conflict_error:
        return api_response(status.HTTP_400_BAD_REQUEST, conflict_error)

    # === Check for conflicts (subcategory vs category) ===
    conflict_error = await check_subcategory_vs_category_conflicts(
        db=db,
        name=input_name,
        slug=final_slug,
        description=input_description,
        meta_title=input_meta_title,
        meta_description=input_meta_description,
    )
    if conflict_error:
        return api_response(status.HTTP_400_BAD_REQUEST, conflict_error)

    # === Apply changes ===
    if name is not None and name.strip():
        subcategory.subcategory_name = input_name.upper()
    if slug is not None and slug.strip():
        subcategory.subcategory_slug = final_slug
    if description is not None and description.strip():
        subcategory.subcategory_description = input_description
    if meta_title is not None and meta_title.strip():
        subcategory.subcategory_meta_title = input_meta_title
    if meta_description is not None and meta_description.strip():
        subcategory.subcategory_meta_description = input_meta_description
    if featured is not None:
        subcategory.featured_subcategory = featured
    if show_in_menu is not None:
        subcategory.show_in_menu = show_in_menu

    # === Handle file upload ===
    if file and file.filename:
        if not is_valid_filename(file.filename):
            return api_response(
                status.HTTP_400_BAD_REQUEST, "Invalid file name."
            )
        sub_path = settings.SUBCATEGORY_IMAGE_PATH.format(
            category_id=subcategory.category_id, slug_name=final_slug
        )

        uploaded_url = await save_uploaded_file(file, sub_path)
        subcategory.subcategory_img_thumbnail = uploaded_url

        await db.commit()
        await db.refresh(subcategory)

    return api_response(
        status.HTTP_200_OK,
        "Subcategory updated successfully",
        data={"subcategory_id": subcategory.subcategory_id},
    )


@router.delete("/soft-delete/{subcategory_id}")
@exception_handler
async def soft_delete_subcategory(
    subcategory_id: str, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    result = await db.execute(
        select(SubCategory).filter_by(subcategory_id=subcategory_id)
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


@router.put("/restore/{subcategory_id}")
@exception_handler
async def restore_subcategory(
    subcategory_id: str, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    result = await db.execute(
        select(SubCategory).filter_by(subcategory_id=subcategory_id)
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


@router.delete("/hard-delete/{subcategory_id}")
@exception_handler
async def hard_delete_subcategory(
    subcategory_id: str, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    result = await db.execute(
        select(SubCategory).filter_by(subcategory_id=subcategory_id)
    )
    subcategory = result.scalars().first()

    if not subcategory:
        return api_response(status.HTTP_404_NOT_FOUND, "Subcategory not found")

    await db.delete(subcategory)
    await db.commit()

    return api_response(status.HTTP_200_OK, "Subcategory permanently deleted")
