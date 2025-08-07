from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy import case, delete, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.api_response import api_response
from schemas.vendor_categories import CategoryOut
from utils.exception_handlers import exception_handler
from utils.file_uploads import get_media_url
from db.models.superadmin import Category, SubCategory, VendorCategoryManagement
from db.sessions.database import get_db
from schemas.industry import VendorCategoryRequest
from sqlalchemy.orm import selectinload

router = APIRouter()

# @router.post("/add")
# async def add_vendor_category_mapping(
#     payload: VendorCategoryRequest,
#     db: AsyncSession = Depends(get_db)
# ):
#     # 1. Check if category exists
#     cat_stmt = select(Category).where(Category.category_id == payload.category_id)
#     cat_result = await db.execute(cat_stmt)
#     category = cat_result.scalar_one_or_none()
#     if not category:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Category ID {payload.category_id} not found."
#         )

#     # 2. If subcategory is provided, check if it exists and belongs to the category
#     if payload.subcategory_id:
#         sub_stmt = select(SubCategory).where(
#             SubCategory.subcategory_id == payload.subcategory_id,
#             SubCategory.category_id == payload.category_id
#         )
#         sub_result = await db.execute(sub_stmt)
#         subcategory = sub_result.scalar_one_or_none()
#         if not subcategory:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail=(
#                     f"SubCategory ID {payload.subcategory_id} not found "
#                     f"or does not belong to Category ID {payload.category_id}."
#                 )
#             )

#     # 3. Check for existing (vendor, category, subcategory) combination
#     check_full_stmt = select(VendorCategoryManagement).where(
#         VendorCategoryManagement.vendor_ref_id == payload.vendor_ref_id,
#         VendorCategoryManagement.category_id == payload.category_id,
#         VendorCategoryManagement.subcategory_id == payload.subcategory_id
#     )
#     full_result = await db.execute(check_full_stmt)
#     if full_result.scalar_one_or_none():
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="This vendor-category-subcategory mapping already exists."
#         )

#     # 4. Check for existing (vendor, category) mapping regardless of subcategory
#     check_partial_stmt = select(VendorCategoryManagement).where(
#         VendorCategoryManagement.vendor_ref_id == payload.vendor_ref_id,
#         VendorCategoryManagement.category_id == payload.category_id,
#         VendorCategoryManagement.subcategory_id.is_(None)
#         if payload.subcategory_id is not None
#         else VendorCategoryManagement.subcategory_id.isnot(None)
#     )
#     partial_result = await db.execute(check_partial_stmt)
#     if partial_result.scalar_one_or_none():
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="A conflicting vendor-category mapping already exists."
#         )

#     # 5. Save to VendorCategoryManagement
#     new_entry = VendorCategoryManagement(
#         vendor_ref_id=payload.vendor_ref_id,
#         category_id=payload.category_id,
#         subcategory_id=payload.subcategory_id  # can be None
#     )

#     db.add(new_entry)
#     try:
#         await db.commit()
#     except Exception as e:
#         await db.rollback()
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Failed to add vendor-category mapping: " + str(e)
#         )

#     return {
#         "status": "success",
#         "message": "Vendor category mapping added successfully."
#     }

@router.post("/add")
async def add_vendor_category_mapping(
    payload: VendorCategoryRequest,
    db: AsyncSession = Depends(get_db)
):
    # 1. Check if category exists
    cat_stmt = select(Category).where(Category.category_id == payload.category_id)
    cat_result = await db.execute(cat_stmt)
    category = cat_result.scalar_one_or_none()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category ID {payload.category_id} not found."
        )

    # 2. If subcategory is provided, check if it exists and belongs to the category
    if payload.subcategory_id:
        sub_stmt = select(SubCategory).where(
            SubCategory.subcategory_id == payload.subcategory_id,
            SubCategory.category_id == payload.category_id
        )
        sub_result = await db.execute(sub_stmt)
        subcategory = sub_result.scalar_one_or_none()
        if not subcategory:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"SubCategory ID {payload.subcategory_id} not found "
                    f"or does not belong to Category ID {payload.category_id}."
                )
            )

    # 3. Check for existing (vendor, category, subcategory) combination
    check_full_stmt = select(VendorCategoryManagement).where(
        VendorCategoryManagement.vendor_ref_id == payload.vendor_ref_id,
        VendorCategoryManagement.category_id == payload.category_id,
        VendorCategoryManagement.subcategory_id == payload.subcategory_id
    )
    full_result = await db.execute(check_full_stmt)
    existing_mapping = full_result.scalar_one_or_none()

    if existing_mapping:
        if not existing_mapping.is_active:
            # Mapping already exists and is active (is_active = False means active)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This vendor-category-subcategory mapping already exists and is active."
            )
        else:
            # Mapping exists but is inactive (is_active = True means inactive), reactivate it
            existing_mapping.is_active = False  # Set to False to make it active
            try:
                await db.commit()
                return {
                    "status": "success",
                    "message": "Vendor category mapping reactivated successfully."
                }
            except Exception as e:
                await db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to reactivate vendor-category mapping: " + str(e)
                )

    # 4. Remove the conflicting mapping check to allow independent subcategory mappings
    # (Commenting out or removing the previous step 4 logic)

    # 5. Save to VendorCategoryManagement (create new mapping with is_active = False for active)
    new_entry = VendorCategoryManagement(
        vendor_ref_id=payload.vendor_ref_id,
        category_id=payload.category_id,
        subcategory_id=payload.subcategory_id,  # can be None
        is_active=False  # Set to False to make it active
    )

    db.add(new_entry)
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to add vendor-category mapping: " + str(e)
        )

    return {
        "status": "success",
        "message": "Vendor category mapping added successfully."
    }

@router.post("/remove")
async def remove_vendor_category_mapping(
    payload: VendorCategoryRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Removes a vendor's category or subcategory mapping.
    """
    if payload.subcategory_id:
        # Remove subcategory mapping
        delete_stmt = delete(VendorCategoryManagement).where(
            VendorCategoryManagement.vendor_ref_id == payload.vendor_ref_id,
            VendorCategoryManagement.category_id == payload.category_id,
            VendorCategoryManagement.subcategory_id == payload.subcategory_id
        )
    else:
        # Remove category-only mapping (NULL or empty string)
        delete_stmt = delete(VendorCategoryManagement).where(
            VendorCategoryManagement.vendor_ref_id == payload.vendor_ref_id,
            VendorCategoryManagement.category_id == payload.category_id,
            or_(
                VendorCategoryManagement.subcategory_id.is_(None),
                VendorCategoryManagement.subcategory_id == ""
            )
        )

    result = await db.execute(delete_stmt)
    await db.commit()

    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mapping not found or already removed."
        )

    return {
        "status": "success",
        "message": "Vendor category mapping removed successfully."
    }


@router.post("/unmap")
async def unmap_vendor_category_mapping(
    payload: VendorCategoryRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Unmaps a vendor's category or subcategory mapping by performing soft delete.
    Sets is_active to True (True means inactive) instead of physically deleting the record.
    - If subcategory_id is provided, unmaps the specific subcategory mapping.
    - If subcategory_id is not provided, unmaps the category mapping AND all subcategory mappings for that category.
    """
    if payload.subcategory_id:
        # Unmap specific subcategory mapping
        stmt = select(VendorCategoryManagement).where(
            VendorCategoryManagement.vendor_ref_id == payload.vendor_ref_id,
            VendorCategoryManagement.category_id == payload.category_id,
            VendorCategoryManagement.subcategory_id == payload.subcategory_id
        )
        
        result = await db.execute(stmt)
        mapping = result.scalar_one_or_none()

        if not mapping:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subcategory mapping not found."
            )

        # Perform soft delete by setting is_active to True (True means inactive)
        mapping.is_active = True
        
        try:
            await db.commit()
            return {
                "status": "success",
                "message": "Vendor subcategory mapping unmapped successfully."
            }
        except Exception as e:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to unmap vendor-subcategory mapping: " + str(e)
            )
    else:
        # Unmap category and all its subcategories
        # First, get all mappings for this vendor and category (including subcategories)
        stmt = select(VendorCategoryManagement).where(
            VendorCategoryManagement.vendor_ref_id == payload.vendor_ref_id,
            VendorCategoryManagement.category_id == payload.category_id
        )
        
        result = await db.execute(stmt)
        mappings = result.scalars().all()

        if not mappings:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No mappings found for this vendor and category."
            )

        # Count how many mappings will be unmapped
        unmapped_count = 0
        category_unmapped = False
        subcategories_unmapped = 0

        # Perform soft delete on all mappings (category and subcategories)
        for mapping in mappings:
            if mapping.is_active == False:  # Only unmap active mappings (False means active)
                mapping.is_active = True  # Set to True to make inactive
                unmapped_count += 1
                
                if mapping.subcategory_id is None or mapping.subcategory_id == "":
                    category_unmapped = True
                else:
                    subcategories_unmapped += 1

        if unmapped_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active mappings found to unmap for this vendor and category."
            )
        
        try:
            await db.commit()
            
            # Create detailed success message
            message_parts = []
            if category_unmapped:
                message_parts.append("category mapping")
            if subcategories_unmapped > 0:
                message_parts.append(f"{subcategories_unmapped} subcategory mapping(s)")
            
            message = f"Vendor {' and '.join(message_parts)} unmapped successfully."
            
            return {
                "status": "success",
                "message": message,
                "details": {
                    "total_unmapped": unmapped_count,
                    "category_unmapped": category_unmapped,
                    "subcategories_unmapped": subcategories_unmapped
                }
            }
        except Exception as e:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to unmap vendor-category mappings: " + str(e)
            )


@router.get("/")
@exception_handler
async def get_all_categories(
    vendor_ref_id: str = Query(..., description="Vendor reference ID"),
    status_filter: Optional[bool] = Query(
        None,
        description="Filter by vendor-category-management status (is_active): true, false, or omit for all",
    ),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    # Step 1: Get vendor-category mappings
    stmt = select(VendorCategoryManagement).where(
        VendorCategoryManagement.vendor_ref_id == vendor_ref_id
    )

    if status_filter is not None:
        stmt = stmt.where(VendorCategoryManagement.is_active == status_filter)

    result = await db.execute(stmt)
    vendor_mappings = result.scalars().all()

    if not vendor_mappings:
        return api_response(
            status_code=status.HTTP_200_OK,
            message="No categories found for vendor",
            data=[],
        )

    # Organize mappings: category_id -> list of subcategory_ids with mapping status
    from collections import defaultdict
    category_map = defaultdict(set)
    mapping_status = {}  # Store mapping status for each category-subcategory combination
    for entry in vendor_mappings:
        category_map[entry.category_id].add(entry.subcategory_id)
        # Create a unique key for category-subcategory combination
        key = f"{entry.category_id}_{entry.subcategory_id if entry.subcategory_id else 'none'}"
        mapping_status[key] = entry.is_active

    # Step 2: Fetch all required categories
    stmt = select(Category).where(Category.category_id.in_(category_map.keys()))
    stmt = stmt.options(selectinload(Category.subcategories))
    result = await db.execute(stmt)
    categories = result.scalars().unique().all()

    # Step 3: Construct response
    data = []
    for cat in categories:
        subcats = [
            sub for sub in cat.subcategories
            if sub.subcategory_id in category_map[cat.category_id]
        ]

        # Get category mapping status (for category-only mappings)
        category_only_key = f"{cat.category_id}_none"
        category_mapping_status = mapping_status.get(category_only_key, None)

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
                "category_tstamp": cat.category_tstamp.isoformat() if cat.category_tstamp else None,
                "vendor_category_mapping_status": category_mapping_status,  # Added mapping status
                "has_subcategories": len(subcats) > 0,
                "subcategory_count": len(subcats),
                "subcategories": [
                    {
                        "subcategory_id": sub.subcategory_id,
                        "subcategory_name": sub.subcategory_name.title(),
                        "subcategory_description": sub.subcategory_description,
                        "subcategory_status": sub.subcategory_status,
                        "vendor_subcategory_mapping_status": mapping_status.get(f"{cat.category_id}_{sub.subcategory_id}", None),  # Added mapping status
                    }
                    for sub in subcats
                ],
            }
        )

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Vendor-specific categories fetched successfully",
        data=data,
    )

@router.get(
    "/list-categories",
    response_model=List[CategoryOut],
    summary="Fetch vendor-specific categories and subcategories by status",
)
@exception_handler
async def get_categories_and_subcategories_by_status(
    vendor_ref_id: str = Query(..., description="Vendor reference ID"),
    status_value: Optional[bool] = Query(None, description="Filter by vendor-category-management status: true / false / none"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    # Step 1: Fetch VendorCategoryManagement mappings
    stmt = select(VendorCategoryManagement).where(
        VendorCategoryManagement.vendor_ref_id == vendor_ref_id
    )
    if status_value is not None:
        stmt = stmt.where(VendorCategoryManagement.is_active == status_value)

    result = await db.execute(stmt)
    vendor_mappings = result.scalars().all()

    if not vendor_mappings:
        return api_response(
            status_code=status.HTTP_200_OK,
            message="No categories found for vendor",
            data=[],
        )

    # Map category -> subcategory
    from collections import defaultdict
    category_map = defaultdict(set)
    for entry in vendor_mappings:
        category_map[entry.category_id].add(entry.subcategory_id)

    # Fetch the needed categories with subcategories
    stmt = select(Category).where(Category.category_id.in_(category_map.keys()))
    stmt = stmt.options(selectinload(Category.subcategories))
    result = await db.execute(stmt)
    categories = result.scalars().unique().all()

    # Format response
    formatted_categories = []
    for category in categories:
        filtered_subs = [
            sub for sub in category.subcategories
            if sub.subcategory_id in category_map[category.category_id]
        ]
        category.category_name = category.category_name.title()
        for sub in filtered_subs:
            sub.subcategory_name = sub.subcategory_name.title()

        category.subcategories = filtered_subs
        formatted_categories.append(category)

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Filtered vendor categories fetched successfully",
        data=formatted_categories,
    )

@router.get("/total_categories_count")
@exception_handler
async def total_categories_count(
    vendor_ref_id: str = Query(..., description="Vendor reference ID"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    # Step 1: Get all vendor mappings
    stmt = select(VendorCategoryManagement).where(
        VendorCategoryManagement.vendor_ref_id == vendor_ref_id
    )
    result = await db.execute(stmt)
    vendor_mappings = result.scalars().all()

    if not vendor_mappings:
        return api_response(
            status.HTTP_200_OK,
            "No vendor category mappings found",
            data={
                "totals": {
                    "total_categories": 0,
                    "active_categories": 0,
                    "inactive_categories": 0,
                },
                "subcategory_stats": {
                    "total_subcategories": 0,
                    "active_subcategories": 0,
                    "inactive_subcategories": 0,
                    "category_distribution": [],
                },
            },
        )

    # Map category -> subcategory + statuses
    from collections import defaultdict
    category_map = defaultdict(list)
    for entry in vendor_mappings:
        category_map[entry.category_id].append({
            "subcategory_id": entry.subcategory_id,
            "is_active": entry.is_active
        })

    total_categories = len(category_map)
    active_categories = sum(
        1 for subs in category_map.values()
        if any(item["is_active"] is False for item in subs)
    )
    inactive_categories = total_categories - active_categories

    total_subcategories = 0
    active_subcategories = 0
    inactive_subcategories = 0

    category_distribution = []

    # Step 2: Fetch category names
    stmt = select(Category).where(Category.category_id.in_(category_map.keys()))
    stmt = stmt.options(selectinload(Category.subcategories))
    result = await db.execute(stmt)
    categories = result.scalars().all()
    category_dict = {cat.category_id: cat for cat in categories}

    for cat_id, sub_entries in category_map.items():
        total = len(sub_entries)
        active = sum(1 for s in sub_entries if s["is_active"] is False)
        inactive = total - active

        total_subcategories += total
        active_subcategories += active
        inactive_subcategories += inactive

        category_distribution.append(
            {
                "category_name": category_dict.get(cat_id).category_name.title()
                if category_dict.get(cat_id) else f"Unknown-{cat_id}",
                "total_subcategories": total,
                "active_subcategories": active,
                "inactive_subcategories": inactive,
            }
        )

    return api_response(
        status.HTTP_200_OK,
        "Vendor-specific category stats fetched successfully",
        data={
            "totals": {
                "total_categories": total_categories,
                "active_categories": active_categories,
                "inactive_categories": inactive_categories,
            },
            "subcategory_stats": {
                "total_subcategories": total_subcategories,
                "active_subcategories": active_subcategories,
                "inactive_subcategories": inactive_subcategories,
                "category_distribution": category_distribution,
            },
        },
    )
