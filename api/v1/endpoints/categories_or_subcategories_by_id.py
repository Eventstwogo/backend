from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    UploadFile,
    status,
)
from fastapi.responses import JSONResponse
from slugify import slugify
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from core.api_response import api_response
from core.config import settings
from db.models.superadmin import Category, SubCategory, Industries
from db.sessions.database import get_db
from utils.exception_handlers import exception_handler
from utils.file_uploads import get_media_url, save_uploaded_file
from utils.format_validators import is_valid_filename
from utils.security_validators import (
    contains_sql_injection,
    contains_xss,
    sanitize_input,
)
from utils.validators import (
    is_meaningful,
    is_valid_category_name,
    is_valid_subcategory_name,
    validate_length,
)

router = APIRouter()


@router.get("/details/{item_id}")
@exception_handler
async def get_category_or_subcategory_details(
    item_id: str, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    # Try to find category by ID
    category_result = await db.execute(
        select(Category)
        .options(selectinload(Category.subcategories))
        .filter_by(category_id=item_id)
    )
    category = category_result.scalars().first()

    if category:
        data = {
            "type": "category",
            "category_id": category.category_id,
            "industry_id": category.industry_id,
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

    # Try to find subcategory by ID
    subcat_result = await db.execute(
        select(SubCategory).filter_by(subcategory_id=item_id)
    )
    sub = subcat_result.scalars().first()

    if sub:
        data = {
            "type": "subcategory",
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
            "subcategory_tstamp": sub.subcategory_tstamp,
            "category_id": sub.category_id,
        }
        return api_response(
            status_code=status.HTTP_200_OK,
            message="Subcategory fetched successfully",
            data=data,
        )

    # Neither category nor subcategory found
    return api_response(
        status_code=status.HTTP_404_NOT_FOUND,
        message="Category or Subcategory not found",
    )


@router.put("/update/{item_id}")
@exception_handler
async def update_category_or_subcategory(
    item_id: str,
    industry_id: Optional[str] = Form(None),
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
    # Try fetching as Category
    result = await db.execute(select(Category).filter_by(category_id=item_id))
    category = result.scalars().first()

    if category:
        item = category
        model_type = "category"
        id_field = "category_id"
        slug_field = "category_slug"
        name_field = "category_name"
        desc_field = "category_description"
        meta_title_field = "category_meta_title"
        meta_desc_field = "category_meta_description"
        featured_field = "featured_category"
        img_field = "category_img_thumbnail"
        path_template = settings.CATEGORY_IMAGE_PATH
    else:
        # Try SubCategory
        result = await db.execute(
            select(SubCategory).filter_by(subcategory_id=item_id)
        )
        subcategory = result.scalars().first()

        if not subcategory:
            return api_response(status.HTTP_404_NOT_FOUND, "Item not found")

        item = subcategory
        model_type = "subcategory"
        id_field = "subcategory_id"
        slug_field = "subcategory_slug"
        name_field = "subcategory_name"
        desc_field = "subcategory_description"
        meta_title_field = "subcategory_meta_title"
        meta_desc_field = "subcategory_meta_description"
        featured_field = "featured_subcategory"
        img_field = "subcategory_img_thumbnail"
        path_template = settings.SUBCATEGORY_IMAGE_PATH

    # === Validate industry_id if provided (only for categories) ===
    if industry_id and industry_id.strip():
        if model_type == "category":
            # Check if industry_id exists
            industry_result = await db.execute(
                select(Industries).where(Industries.industry_id == industry_id.strip())
            )
            industry = industry_result.scalar_one_or_none()
            if not industry:
                return api_response(
                    status.HTTP_404_NOT_FOUND, "Industry ID not found"
                )
            # Check if industry is active (false means active, true means inactive)
            if industry.is_active:
                return api_response(
                    status.HTTP_400_BAD_REQUEST, "Industry is inactive"
                )
        # If it's a subcategory, ignore the industry_id parameter (no error, just ignore)

    updated = False
    final_slug = getattr(item, slug_field)

    # Name
    name_updated = False
    if is_meaningful(name):
        # Security validation for name
        if contains_xss(name) or contains_sql_injection(name):
            return api_response(
                status.HTTP_400_BAD_REQUEST,
                "Name contains potentially malicious content."
            )
        
        name = sanitize_input(name)
        if model_type == "category":
            if not is_valid_category_name(name):
                return api_response(
                    status.HTTP_400_BAD_REQUEST, f"Invalid {model_type} name."
                )
        else:
            if not is_valid_subcategory_name(name):
                return api_response(
                    status.HTTP_400_BAD_REQUEST, f"Invalid {model_type} name."
                )
        setattr(item, name_field, name.upper())
        updated = True
        name_updated = True

    # Industry ID (only for categories)
    if industry_id and industry_id.strip() and model_type == "category":
        item.industry_id = industry_id.strip()
        updated = True

    # Slug - Update slug when name is updated or when slug is explicitly provided
    if is_meaningful(slug) or name_updated:
        # Use slug if given, else generate from updated name
        if is_meaningful(slug):
            base_slug = slug
        else:
            # Generate slug from the updated name
            base_slug = name
        
        base_slug = sanitize_input(base_slug)
        if contains_xss(base_slug) or contains_sql_injection(base_slug):
            return api_response(
                status.HTTP_400_BAD_REQUEST, "Invalid slug provided."
            )
        final_slug = slugify(base_slug)

        # Check for duplicate slug
        existing_slug_check = await db.execute(
            select(type(item)).filter(
                getattr(type(item), slug_field) == final_slug,
                getattr(type(item), id_field) != item_id,
            )
        )
        if existing_slug_check.scalars().first():
            return api_response(
                status.HTTP_400_BAD_REQUEST,
                f"{model_type.capitalize()} slug already exists.",
            )

        setattr(item, slug_field, final_slug)
        updated = True

    # Description
    if is_meaningful(description):
        assert description is not None
        # Security validation for description
        if contains_xss(description) or contains_sql_injection(description):
            return api_response(
                status.HTTP_400_BAD_REQUEST,
                "Description contains potentially malicious content."
            )
        
        description = sanitize_input(description).strip()
        if not validate_length(description, 0, 500):
            return api_response(
                status.HTTP_400_BAD_REQUEST,
                "Description too long. Max 500 characters.",
            )
        setattr(item, desc_field, description)
        updated = True

    # Meta Title
    if is_meaningful(meta_title):
        assert meta_title is not None
        # Security validation for meta title
        if contains_xss(meta_title) or contains_sql_injection(meta_title):
            return api_response(
                status.HTTP_400_BAD_REQUEST,
                "Meta title contains potentially malicious content."
            )
        
        meta_title = sanitize_input(meta_title).strip()
        if not validate_length(meta_title, 0, 70):
            return api_response(
                status.HTTP_400_BAD_REQUEST,
                "Meta title too long. Max 70 characters.",
            )
        setattr(item, meta_title_field, meta_title)
        updated = True

    # Meta Description
    if is_meaningful(meta_description):
        assert meta_description is not None
        # Security validation for meta description
        if contains_xss(meta_description) or contains_sql_injection(meta_description):
            return api_response(
                status.HTTP_400_BAD_REQUEST,
                "Meta description contains potentially malicious content."
            )
        
        meta_description = sanitize_input(meta_description).strip()
        if not validate_length(meta_description, 0, 160):
            return api_response(
                status.HTTP_400_BAD_REQUEST,
                "Meta description too long. Max 160 characters.",
            )
        setattr(item, meta_desc_field, meta_description)
        updated = True

    # Booleans
    if featured is not None:
        setattr(item, featured_field, featured)
        updated = True

    if show_in_menu is not None:
        item.show_in_menu = show_in_menu
        updated = True

    # File Upload
    if file and file.filename:
        if not is_valid_filename(file.filename):
            return api_response(
                status.HTTP_400_BAD_REQUEST, "Invalid file name."
            )

        if model_type == "category":
            sub_path = path_template.format(slug_name=final_slug)
        else:
            sub_path = path_template.format(
                category_id=item.category_id, slug_name=final_slug
            )

        try:
            uploaded_url = await save_uploaded_file(file, sub_path)
            setattr(item, img_field, uploaded_url)
            updated = True
        except ValueError as ve:
            return api_response(status.HTTP_400_BAD_REQUEST, str(ve))
        except Exception as e:
            return api_response(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Failed to save uploaded file: {str(e)}",
                log_error=True,
            )

    if not updated:
        return api_response(
            status.HTTP_400_BAD_REQUEST,
            "At least one field must be provided.",
        )

    await db.commit()
    await db.refresh(item)

    return api_response(
        status.HTTP_200_OK,
        f"{model_type.capitalize()} updated successfully",
        data={f"{model_type}_id": item_id},
    )


@router.delete("/soft-delete/{item_id}")
@exception_handler
async def soft_delete_category_or_subcategory(
    item_id: str, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    # First: Try deleting as a category
    result = await db.execute(
        select(Category)
        .options(selectinload(Category.subcategories))
        .filter_by(category_id=item_id)
    )
    category = result.scalars().first()

    if category:
        if category.category_status:
            return api_response(
                status.HTTP_400_BAD_REQUEST, "Category already inactive"
            )

        category.category_status = True
        for sub in category.subcategories:
            sub.subcategory_status = True

        await db.commit()
        return api_response(
            status.HTTP_200_OK,
            "Category and subcategories soft deleted successfully",
        )

    # Next: Try deleting as a subcategory
    result = await db.execute(
        select(SubCategory).filter_by(subcategory_id=item_id)
    )
    subcategory = result.scalars().first()

    if subcategory:
        if subcategory.subcategory_status:
            return api_response(
                status.HTTP_400_BAD_REQUEST, "Subcategory already inactive"
            )

        subcategory.subcategory_status = True
        await db.commit()
        return api_response(
            status.HTTP_200_OK,
            "Subcategory soft deleted successfully",
        )

    # If not found at all
    return api_response(
        status.HTTP_404_NOT_FOUND,
        "Category or Subcategory not found",
    )


@router.put("/restore/{item_id}")
@exception_handler
async def restore_category_or_subcategory(
    item_id: str, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    # First try restoring as a category
    result = await db.execute(
        select(Category)
        .options(selectinload(Category.subcategories))
        .filter_by(category_id=item_id)
    )
    category = result.scalars().first()

    if category:
        if category.category_status is False:
            return api_response(
                status.HTTP_400_BAD_REQUEST, "Category is already active"
            )

        category.category_status = False
        for sub in category.subcategories:
            sub.subcategory_status = False

        await db.commit()
        return api_response(
            status.HTTP_200_OK,
            "Category and subcategories restored successfully",
        )

    # Try restoring as a subcategory
    result = await db.execute(
        select(SubCategory).filter_by(subcategory_id=item_id)
    )
    subcategory = result.scalars().first()

    if subcategory:
        if subcategory.subcategory_status is False:
            return api_response(
                status.HTTP_400_BAD_REQUEST, "Subcategory is already active"
            )

        subcategory.subcategory_status = False
        await db.commit()
        return api_response(
            status.HTTP_200_OK,
            "Subcategory restored successfully",
        )

    return api_response(
        status.HTTP_404_NOT_FOUND,
        "Category or Subcategory not found",
    )
