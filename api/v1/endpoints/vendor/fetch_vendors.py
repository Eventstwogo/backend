import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload

from utils.id_generators import decrypt_data, decrypt_dict_values
from db.models.superadmin import BusinessProfile, VendorLogin, VendorCategoryManagement, Category, Product, Industries
from db.sessions.database import get_db
from schemas.vendor_details import AllVendorsResponse, VendorDetailsResponse, VendorProductsAndCategoriesResponse


router = APIRouter()


def calculate_years_in_business(created_at: datetime) -> str:
    """
    Calculate years and months in business from created_at timestamp.
    Returns format: yyyy:mm
    """
    if not created_at:
        return "0:00"
    
    now = datetime.now(created_at.tzinfo) if created_at.tzinfo else datetime.now()
    
    # Calculate the difference
    years = now.year - created_at.year
    months = now.month - created_at.month
    
    # Adjust if the current month/day is before the created month/day
    if months < 0:
        years -= 1
        months += 12
    elif months == 0 and now.day < created_at.day:
        years -= 1
        months = 11
    elif now.day < created_at.day:
        months -= 1
        if months < 0:
            years -= 1
            months = 11
    
    return f"{years}:{months:02d}"


@router.get("/details", response_model=dict)
async def get_vendor_details(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
   
    # Fetch vendor login
    stmt = select(VendorLogin).where(
        VendorLogin.user_id == user_id
    )
    result = await db.execute(stmt)
    vendor = result.scalar_one_or_none()

    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    # Fetch business profile
    business_stmt = select(BusinessProfile).where(
        BusinessProfile.profile_ref_id == vendor.business_profile_id
    )
    business_result = await db.execute(business_stmt)
    business_profile = business_result.scalar_one_or_none()

    # Decrypt profile_details if available
    decrypted_profile_details = {}
    if business_profile and business_profile.profile_details:
        try:
            # Ensure profile_details is a dict before decrypting
            raw_data = business_profile.profile_details
            if isinstance(raw_data, str):
                raw_data = json.loads(raw_data)
            decrypted_profile_details = decrypt_dict_values(raw_data)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to decrypt profile details: {str(e)}")

    return {
        "vendor_login": {
            "user_id": vendor.user_id,
            "email": vendor.email,
            "is_verified": vendor.is_verified,
            "is_active": vendor.is_active,
            "last_login": vendor.last_login,
            "created_at": vendor.created_at,
        },
        "business_profile": {
            "store_name": business_profile.store_name if business_profile else None,
            "industry": business_profile.industry if business_profile else None,
            "location": business_profile.location if business_profile else None,
            "is_approved": business_profile.is_approved if business_profile else None,
            "profile_details": decrypted_profile_details,
            "purpose": business_profile.purpose if business_profile else {},
        },
    }




@router.get("/vendors/all", response_model=list[dict])
async def get_all_vendors(db: AsyncSession = Depends(get_db)):
    stmt = select(VendorLogin).options(
        joinedload(VendorLogin.business_profile).joinedload(BusinessProfile.industry_obj)
    )
    result = await db.execute(stmt)
    vendors = result.scalars().all()

    all_vendor_data = []

    for vendor in vendors:
        business_profile = vendor.business_profile

        # Decrypt profile_details if present
        decrypted_profile_details = {}
        if business_profile and business_profile.profile_details:
            try:
                raw_data = business_profile.profile_details
                if isinstance(raw_data, str):
                    raw_data = json.loads(raw_data)
                decrypted_profile_details = decrypt_dict_values(raw_data)
            except Exception as e:
                decrypted_profile_details = {"error": f"Decryption failed: {str(e)}"}


        decrypted_email = decrypt_data(vendor.email)    

        industry_name = (
            business_profile.industry_obj.industry_name
            if business_profile and business_profile.industry_obj
            else None
        )    

        all_vendor_data.append({
            "vendor_login": {
                "user_id": vendor.user_id,
                "email":decrypted_email,
                "is_verified": vendor.is_verified,
                "is_active": vendor.is_active,
                "last_login": vendor.last_login,
                "created_at": vendor.created_at,
            },
            "business_profile": {
                "store_name": business_profile.store_name if business_profile else None,
                "industry_id": business_profile.industry if business_profile else None,
                "industry_name": industry_name,
                "location": business_profile.location if business_profile else None,
                "is_approved": business_profile.is_approved if business_profile else None,
                "profile_details": decrypted_profile_details,
                "purpose": business_profile.purpose if business_profile else {},
                "payment_preference": business_profile.payment_preference if business_profile else [],
            },
        })

    return all_vendor_data


@router.get("/all-vendor-details", response_model=AllVendorsResponse)
async def get_all_vendor_details(db: AsyncSession = Depends(get_db)):

    # Fetch all vendors with their business profiles
    stmt = select(VendorLogin).options(
        joinedload(VendorLogin.business_profile).joinedload(BusinessProfile.industry_obj)
    )
    result = await db.execute(stmt)
    vendors = result.scalars().all()
    
    vendor_details_list = []
    
    for vendor in vendors:
        business_profile = vendor.business_profile
        
        # Get categories by industry_id from business profile
        categories_info = []
        if business_profile and business_profile.industry:
            # Fetch categories that belong to this vendor's industry
            categories_stmt = select(Category).where(
                Category.industry_id == business_profile.industry
            )
            categories_result = await db.execute(categories_stmt)
            categories = categories_result.scalars().all()
            
            for category in categories:
                categories_info.append({
                    "category_id": category.category_id,
                    "category_name": category.category_name,
                    "industry_id": category.industry_id
                })
        
        # Count total products for this vendor
        product_count_stmt = select(func.count(Product.product_id)).where(
            Product.vendor_id == vendor.user_id
        )
        product_count_result = await db.execute(product_count_stmt)
        total_products = product_count_result.scalar() or 0
        
        # Calculate years in business from created_at
        years_in_business = calculate_years_in_business(vendor.created_at)
        
        vendor_details = VendorDetailsResponse(
            vendor_id=vendor.user_id,
            store_name=business_profile.store_name if business_profile else None,
            location=business_profile.location if business_profile else None,
            business_logo=business_profile.business_logo if business_profile else None,
            store_logo=business_profile.business_logo if business_profile else None,  # Using business_logo as store_logo
            categories=categories_info,
            total_products=total_products,
            years_in_business=years_in_business
        )
        
        vendor_details_list.append(vendor_details)
    
    return AllVendorsResponse(
        vendors=vendor_details_list,
        total_vendors=len(vendor_details_list)
    )


@router.get("/vendor-products-categories", response_model=VendorProductsAndCategoriesResponse)
async def get_vendor_products_and_categories(
    vendor_id: str,
    db: AsyncSession = Depends(get_db)
):

    # First, verify the vendor exists and get business profile
    vendor_stmt = select(VendorLogin).options(
        joinedload(VendorLogin.business_profile)
    ).where(VendorLogin.user_id == vendor_id)
    vendor_result = await db.execute(vendor_stmt)
    vendor = vendor_result.scalar_one_or_none()
    
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    # Get vendor's products with category information
    products_stmt = select(Product, Category).join(
        Category, Product.category_id == Category.category_id
    ).where(Product.vendor_id == vendor_id)
    
    products_result = await db.execute(products_stmt)
    products_data = products_result.all()
    
    # Process products with all details
    products_info = []
    for product, category in products_data:
        products_info.append({
            "product_id": product.product_id,
            "vendor_id": product.vendor_id,
            "category_id": category.category_id,
            "category_name": category.category_name,
            "subcategory_id": product.subcategory_id,
            "slug": product.slug,
            "identification": product.identification or {},
            "descriptions": product.descriptions,
            "pricing": product.pricing,
            "inventory": product.inventory,
            "physical_attributes": product.physical_attributes,
            "images": product.images,
            "tags_and_relationships": product.tags_and_relationships,
            "status_flags": product.status_flags or {},
        })
    
    # Get store name from business profile
    store_name = None
    if vendor.business_profile:
        store_name = vendor.business_profile.store_name
    
    return VendorProductsAndCategoriesResponse(
        vendor_id=vendor_id,
        store_name=store_name,
        products=products_info,
        total_products=len(products_info)
    )