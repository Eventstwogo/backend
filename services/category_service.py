import re
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.superadmin import Category, SubCategory
from utils.security_validators import (
    contains_sql_injection,
    contains_xss,
    sanitize_input,
)
from utils.validators import (
    is_single_reserved_word,
    is_valid_category_name,
    is_valid_subcategory_name,
    normalize_whitespace,
    validate_length,
)

def validate_category_data(
    name: str,
    slug: Optional[str],
    description: Optional[str],
    meta_title: Optional[str],
    meta_description: Optional[str],
    is_subcategory: bool = False,
) -> tuple[str, str, Optional[str], Optional[str], Optional[str]]:
    # Security validation for name
    if contains_xss(name) or contains_sql_injection(name):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, 
            detail="Name contains potentially malicious content."
        )
    
    name = sanitize_input(name)
    name = normalize_whitespace(name)
    
    if is_subcategory:
        if not is_valid_subcategory_name(name):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, detail="Invalid subcategory name."
            )
        if is_single_reserved_word(name):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Python reserved words are not allowed in subcategory names.",
            )
    else:
        if not is_valid_category_name(name):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, detail="Invalid category name."
            )
        if is_single_reserved_word(name):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Python reserved words are not allowed in category names.",
            )

    slug = sanitize_input(slug or name)
    if contains_xss(slug) or contains_sql_injection(slug):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid slug.")
    if is_single_reserved_word(slug):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Python reserved words are not allowed in slugs.",
        )

    if description:
        # Security validation for description
        if contains_xss(description) or contains_sql_injection(description):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Description contains potentially malicious content.",
            )
        
        description = sanitize_input(description).strip()
        description = normalize_whitespace(description)
        # Allow more characters in description: letters, numbers, spaces, periods, commas, hyphens, parentheses, etc.
        if not re.fullmatch(r"[A-Za-z0-9\s.,()&'’\"!?:;-–]+", description):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Description contains invalid characters.",
            )
        if is_single_reserved_word(description):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Python reserved words are not allowed in descriptions.",
            )
        if not validate_length(description, 0, 500):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Description too long. Max 500 characters allowed.",
            )

    if meta_title:
        # Security validation for meta title
        if contains_xss(meta_title) or contains_sql_injection(meta_title):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Meta title contains potentially malicious content.",
            )
        
        meta_title = sanitize_input(meta_title).strip()
        meta_title = normalize_whitespace(meta_title)
        # Allow more characters in meta title: letters, numbers, spaces, periods, commas, hyphens, pipes, etc.
        if not re.fullmatch(r"[A-Za-z0-9\s.,’()&'\"!?:;|-–]+", meta_title):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Meta title contains invalid characters.",
            )
        if is_single_reserved_word(meta_title):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Python reserved words are not allowed in meta titles.",
            )
        if not validate_length(meta_title, 0, 70):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Meta title too long. Max 70 characters allowed.",
            )

    if meta_description:
        # Security validation for meta description
        if contains_xss(meta_description) or contains_sql_injection(meta_description):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Meta description contains potentially malicious content.",
            )
        
        meta_description = sanitize_input(meta_description).strip()
        meta_description = normalize_whitespace(meta_description)
        # Allow more characters in meta description: letters, numbers, spaces, periods, commas, hyphens, etc.
        if not re.fullmatch(r"[A-Za-z0-9\s.,()&'’\"!?:;\-–—]+", meta_description):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Meta description contains invalid characters.",
            )
        if is_single_reserved_word(meta_description):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Python reserved words are not allowed in meta descriptions.",
            )
        if not validate_length(meta_description, 0, 160):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Meta description too long. Max 160 characters allowed.",
            )

    # Preserve empty strings instead of converting to None
    # Only convert None to empty string to ensure consistency
    description = description if description is not None else ""
    meta_title = meta_title if meta_title is not None else ""
    meta_description = meta_description if meta_description is not None else ""
    
    return name.upper(), slug.lower(), description, meta_title, meta_description


# === Category Checking ===
async def check_category_name_exists(db: AsyncSession, name: str) -> bool:
    result = await db.execute(
        select(Category).where(
            func.lower(Category.category_name) == name.strip().lower()
        )
    )
    if result.scalars().first():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Category name cannot be same as an existing category name.",
        )
    return False


async def check_category_slug_exists(db: AsyncSession, slug: str) -> bool:
    result = await db.execute(
        select(Category).where(
            func.lower(Category.category_slug) == slug.strip().lower()
        )
    )
    if result.scalars().first():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Category slug cannot be same as an existing category slug.",
        )
    return False


async def check_category_description_exists(
    db: AsyncSession, description: str
) -> bool:
    # Skip validation if description is None or empty
    if not description or not description.strip():
        return False
        
    result = await db.execute(
        select(Category).where(
            func.lower(Category.category_description)
            == description.strip().lower()
        )
    )
    if result.scalars().first():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Category description cannot be same as an existing category description.",
        )
    return False


async def check_category_meta_title_exists(
    db: AsyncSession, meta_title: str
) -> bool:
    # Skip validation if meta_title is None or empty
    if not meta_title or not meta_title.strip():
        return False
        
    result = await db.execute(
        select(Category).where(
            func.lower(Category.category_meta_title)
            == meta_title.strip().lower()
        )
    )
    if result.scalars().first():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Category meta title cannot be same as an existing category meta title.",
        )
    return False


async def check_category_meta_description_exists(
    db: AsyncSession, meta_description: str
) -> bool:
    # Skip validation if meta_description is None or empty
    if not meta_description or not meta_description.strip():
        return False
        
    result = await db.execute(
        select(Category).where(
            func.lower(Category.category_meta_description)
            == meta_description.strip().lower()
        )
    )
    if result.scalars().first():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=(
                "Category meta description cannot be same as an "
                "existing category meta description."
            ),
        )
    return False


# === Subcategory Checking ===
async def check_subcategory_name_exists(db: AsyncSession, name: str) -> bool:
    result = await db.execute(
        select(SubCategory).where(
            func.lower(SubCategory.subcategory_name) == name.strip().lower()
        )
    )
    if result.scalars().first():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Subcategory name cannot be same as an existing subcategory name.",
        )
    return False


async def check_subcategory_slug_exists(db: AsyncSession, slug: str) -> bool:
    result = await db.execute(
        select(SubCategory).where(
            func.lower(SubCategory.subcategory_slug) == slug.strip().lower()
        )
    )
    if result.scalars().first():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Subcategory slug cannot be same as an existing subcategory slug.",
        )
    return False


async def check_subcategory_description_exists(
    db: AsyncSession, description: str
) -> bool:
    # Skip validation if description is None or empty
    if not description or not description.strip():
        return False
        
    result = await db.execute(
        select(SubCategory).where(
            func.lower(SubCategory.subcategory_description)
            == description.strip().lower()
        )
    )
    if result.scalars().first():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Subcategory description cannot be same as an existing subcategory description.",
        )
    return False


async def check_subcategory_meta_title_exists(
    db: AsyncSession, meta_title: str
) -> bool:
    # Skip validation if meta_title is None or empty
    if not meta_title or not meta_title.strip():
        return False
        
    result = await db.execute(
        select(SubCategory).where(
            func.lower(SubCategory.subcategory_meta_title)
            == meta_title.strip().lower()
        )
    )
    if result.scalars().first():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Subcategory meta title cannot be same as an existing subcategory meta title.",
        )
    return False


async def check_subcategory_meta_description_exists(
    db: AsyncSession, meta_description: str
) -> bool:
    # Skip validation if meta_description is None or empty
    if not meta_description or not meta_description.strip():
        return False
        
    result = await db.execute(
        select(SubCategory).where(
            func.lower(SubCategory.subcategory_meta_description)
            == meta_description.strip().lower()
        )
    )
    if result.scalars().first():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=(
                "Subcategory meta description cannot be same as"
                "an existing subcategory meta description."
            ),
        )
    return False


async def validate_category_conflicts(
    db: AsyncSession,
    name: str,
    slug: str,
    description: Optional[str] = None,
    meta_title: Optional[str] = None,
    meta_description: Optional[str] = None,
    category_id_to_exclude: Optional[str] = None,
) -> str | None:
    # Fetch all categories
    result = await db.execute(select(Category))
    categories = result.scalars().all()

    for cat in categories:
        # Skip the current category (important for update scenarios)
        if category_id_to_exclude and str(cat.category_id) == str(
            category_id_to_exclude
        ):
            continue

        if cat.category_name.strip().lower() == name.strip().lower():
            return "Category name already exists."
        if cat.category_slug.strip().lower() == slug.strip().lower():
            return "Category slug already exists."
        if (
            description
            and (cat.category_description or "").strip().lower()
            == description.strip().lower()
        ):
            return "Category description already exists."
        if (
            meta_title
            and (cat.category_meta_title or "").strip().lower()
            == meta_title.strip().lower()
        ):
            return "Category meta title already exists."
        if (
            meta_description
            and (cat.category_meta_description or "").strip().lower()
            == meta_description.strip().lower()
        ):
            return "Category meta description already exists."

    # Check against subcategories (don't exclude any)
    result = await db.execute(select(SubCategory))
    subcategories = result.scalars().all()

    for sub in subcategories:
        if sub.subcategory_name.strip().lower() == name.strip().lower():
            return (
                "Category name cannot be same as an existing subcategory name."
            )
        if sub.subcategory_slug.strip().lower() == slug.strip().lower():
            return (
                "Category slug cannot be same as an existing subcategory slug."
            )
        if (
            description
            and sub.subcategory_description
            and sub.subcategory_description.strip().lower()
            == description.strip().lower()
        ):
            return "Category description cannot be same as an existing subcategory description."
        if (
            meta_title
            and sub.subcategory_meta_title
            and sub.subcategory_meta_title.strip().lower()
            == meta_title.strip().lower()
        ):
            return "Category meta title cannot be same as an existing subcategory meta title."
        if (
            meta_description
            and sub.subcategory_meta_description
            and sub.subcategory_meta_description.strip().lower()
            == meta_description.strip().lower()
        ):
            return (
                "Category meta description cannot be same as "
                "an existing subcategory meta description."
            )

    return None


async def validate_subcategory_conflicts(
    db: AsyncSession,
    name: str,
    slug: str,
    description: Optional[str] = None,
    meta_title: Optional[str] = None,
    meta_description: Optional[str] = None,
) -> str | None:
    # Check if it conflicts with categories
    result = await db.execute(select(Category))
    categories = result.scalars().all()
    for cat in categories:
        if cat.category_name.strip().lower() == name.strip().lower():
            return (
                "Subcategory name cannot be same as an existing category name."
            )
        if cat.category_slug.strip().lower() == slug.strip().lower():
            return (
                "Subcategory slug cannot be same as an existing category slug."
            )
        if (
            description
            and cat.category_description
            and cat.category_description.strip().lower()
            == description.strip().lower()
        ):
            return "Subcategory description cannot be same as an existing category description."
        if (
            meta_title
            and cat.category_meta_title
            and cat.category_meta_title.strip().lower()
            == meta_title.strip().lower()
        ):
            return "Subcategory meta title cannot be same as an existing category meta title."
        if (
            meta_description
            and cat.category_meta_description
            and cat.category_meta_description.strip().lower()
            == meta_description.strip().lower()
        ):
            return (
                "Subcategory meta description cannot be same as "
                "an existing category meta description."
            )

    # Check if it conflicts with subcategories
    if await check_subcategory_name_exists(db, name):
        return None
    if await check_subcategory_slug_exists(db, slug):
        return None
    if description and await check_subcategory_description_exists(
        db, description
    ):
        return None
    if meta_title and await check_subcategory_meta_title_exists(db, meta_title):
        return None
    if meta_description and await check_subcategory_meta_description_exists(
        db, meta_description
    ):
        return None

    return None


def validate_subcategory_fields(
    name: str,
    slug: str,
    description: Optional[str],
    meta_title: Optional[str],
    meta_description: Optional[str],
) -> tuple[str, str, str, str, str]:
    """Sanitize and validate subcategory inputs."""
    # Security validation for name
    if contains_xss(name) or contains_sql_injection(name):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, 
            detail="Name contains potentially malicious content."
        )
    
    name = normalize_whitespace(sanitize_input(name))
    slug = normalize_whitespace(sanitize_input(slug))
    description = (
        normalize_whitespace(sanitize_input(description)) if description else ""
    )
    meta_title = (
        normalize_whitespace(sanitize_input(meta_title)) if meta_title else ""
    )
    meta_description = (
        normalize_whitespace(sanitize_input(meta_description))
        if meta_description
        else ""
    )

    if not is_valid_subcategory_name(name):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Invalid subcategory name."
        )
    if is_single_reserved_word(name):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Python reserved words are not allowed in subcategory names.",
        )

    if contains_xss(slug) or contains_sql_injection(slug):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Invalid slug provided."
        )
    if is_single_reserved_word(slug):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Python reserved words are not allowed in slugs.",
        )

    if description:
        # Security validation for description
        if contains_xss(description) or contains_sql_injection(description):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Description contains potentially malicious content.",
            )
        
        if not validate_length(description, 0, 500):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Description too long. Max 500 characters.",
            )
        # Allow more characters in description: letters, numbers, spaces, periods, commas, hyphens, parentheses, etc.
        if not re.fullmatch(r"[A-Za-z0-9\s.,()&'’\"!?:;\-–—]+", description):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Description contains invalid characters.",
            )
        if is_single_reserved_word(description):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Python reserved words are not allowed in descriptions.",
            )

    if meta_title:
        # Security validation for meta title
        if contains_xss(meta_title) or contains_sql_injection(meta_title):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Meta title contains potentially malicious content.",
            )
        
        if not validate_length(meta_title, 0, 70):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Meta title too long. Max 70 characters.",
            )
        # Allow more characters in meta title: letters, numbers, spaces, periods, commas, hyphens, pipes, etc.
        if not re.fullmatch(r"[A-Za-z0-9\s.,()&'’\"!?:;\-–—]+", meta_title):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Meta title contains invalid characters.",
            )
        if is_single_reserved_word(meta_title):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Python reserved words are not allowed in meta titles.",
            )

    if meta_description:
        # Security validation for meta description
        if contains_xss(meta_description) or contains_sql_injection(meta_description):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Meta description contains potentially malicious content.",
            )
        
        if not validate_length(meta_description, 0, 160):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Meta description too long. Max 160 characters.",
            )
        # Allow more characters in meta description: letters, numbers, spaces, periods, commas, hyphens, etc.
        if not re.fullmatch(r"[A-Za-z0-9\s.,()&'’\"!?:;\-–—]+", meta_description):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Meta description contains invalid characters.",
            )
        if is_single_reserved_word(meta_description):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Python reserved words are not allowed in meta descriptions.",
            )

    return name, slug, description, meta_title, meta_description


async def check_subcategory_conflicts(
    db: AsyncSession,
    name: str,
    slug: str,
    description: Optional[str] = None,
    meta_title: Optional[str] = None,
    meta_description: Optional[str] = None,
    subcategory_id_to_exclude: Optional[str] = None,
) -> Optional[str]:
    """Check if subcategory data conflicts with existing subcategories."""
    result = await db.execute(select(SubCategory))
    subcategories = result.scalars().all()

    for sub in subcategories:
        if subcategory_id_to_exclude and str(sub.subcategory_id) == str(
            subcategory_id_to_exclude
        ):
            continue

        if sub.subcategory_name.strip().lower() == name.strip().lower():
            return "Subcategory name already exists."
        if sub.subcategory_slug.strip().lower() == slug.strip().lower():
            return "Subcategory slug already exists."
        if (
            description
            and sub.subcategory_description
            and sub.subcategory_description.strip().lower()
            == description.strip().lower()
        ):
            return "Subcategory description already exists."
        if (
            meta_title
            and sub.subcategory_meta_title
            and sub.subcategory_meta_title.strip().lower()
            == meta_title.strip().lower()
        ):
            return "Subcategory meta title already exists."
        if (
            meta_description
            and sub.subcategory_meta_description
            and sub.subcategory_meta_description.strip().lower()
            == meta_description.strip().lower()
        ):
            return "Subcategory meta description already exists."

    return None


async def check_subcategory_vs_category_conflicts(
    db: AsyncSession,
    name: str,
    slug: str,
    description: Optional[str] = None,
    meta_title: Optional[str] = None,
    meta_description: Optional[str] = None,
) -> Optional[str]:
    """Ensure subcategory fields don't conflict with category fields."""
    result = await db.execute(select(Category))
    categories = result.scalars().all()

    for cat in categories:
        if cat.category_name.strip().lower() == name.strip().lower():
            return "Subcategory name cannot match existing category name."
        if cat.category_slug.strip().lower() == slug.strip().lower():
            return "Subcategory slug cannot match existing category slug."
        if (
            description
            and cat.category_description
            and cat.category_description.strip().lower()
            == description.strip().lower()
        ):
            return "Subcategory description cannot match category description."
        if (
            meta_title
            and cat.category_meta_title
            and cat.category_meta_title.strip().lower()
            == meta_title.strip().lower()
        ):
            return "Subcategory meta title cannot match category meta title."
        if (
            meta_description
            and cat.category_meta_description
            and cat.category_meta_description.strip().lower()
            == meta_description.strip().lower()
        ):
            return "Subcategory meta description cannot match category meta description."

    return None


# === Category-Subcategory Status Management ===

async def activate_category_with_subcategories(
    db: AsyncSession, category: Category
) -> None:
    """
    Activate a category and all its subcategories.
    
    Args:
        db: Database session
        category: Category instance to activate
    """
    # Activate the category (False = active, True = inactive)
    category.category_status = False
    
    # Activate all subcategories under this category
    for subcategory in category.subcategories:
        subcategory.subcategory_status = False


async def deactivate_category_with_subcategories(
    db: AsyncSession, category: Category
) -> None:
    """
    Deactivate a category and all its subcategories.
    
    Args:
        db: Database session
        category: Category instance to deactivate
    """
    # Deactivate the category (True = inactive, False = active)
    category.category_status = True
    
    # Deactivate all subcategories under this category
    for subcategory in category.subcategories:
        subcategory.subcategory_status = True


async def validate_subcategory_activation(
    db: AsyncSession, subcategory: SubCategory
) -> None:
    """
    Validate that a subcategory can be activated by checking if its parent category is active.
    
    Args:
        db: Database session
        subcategory: Subcategory instance to validate
        
    Raises:
        HTTPException: If parent category is inactive
    """
    # Get the parent category
    result = await db.execute(
        select(Category).filter_by(category_id=subcategory.category_id)
    )
    parent_category = result.scalars().first()
    
    if not parent_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent category not found"
        )
    
    # Check if parent category is inactive (True = inactive)
    if parent_category.category_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot activate subcategory because its parent category is inactive. Please activate the parent category first."
        )


async def activate_subcategory(
    db: AsyncSession, subcategory: SubCategory
) -> None:
    """
    Activate a subcategory after validating its parent category is active.
    
    Args:
        db: Database session
        subcategory: Subcategory instance to activate
        
    Raises:
        HTTPException: If parent category is inactive
    """
    # Validate that parent category is active
    await validate_subcategory_activation(db, subcategory)
    
    # Activate the subcategory (False = active)
    subcategory.subcategory_status = False


async def deactivate_subcategory(
    db: AsyncSession, subcategory: SubCategory
) -> None:
    """
    Deactivate a subcategory (no parent validation needed).
    
    Args:
        db: Database session
        subcategory: Subcategory instance to deactivate
    """
    # Deactivate the subcategory (True = inactive)
    subcategory.subcategory_status = True
