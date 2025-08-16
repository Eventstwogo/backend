import json
import re
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload
import httpx
from bs4 import BeautifulSoup

from utils.id_generators import decrypt_data, decrypt_dict_values
from utils.file_uploads import get_media_url
from db.models.superadmin import BusinessProfile, Role, VendorLogin, VendorCategoryManagement, Category, SubCategory, Product, Industries
from db.sessions.database import get_db
from schemas.vendor_details import AllVendorsResponse, VendorDetailsResponse, VendorProductsAndCategoriesResponse


router = APIRouter()

# Simple in-memory cache for ABN registration dates
# In production, consider using Redis or database caching
_abn_date_cache = {}

def clear_abn_cache():
    """Clear the ABN cache for debugging"""
    global _abn_date_cache
    _abn_date_cache = {}


def validate_abn_format(abn: str) -> bool:
    """
    Validate ABN format (11 digits)
    """
    return abn and len(abn) == 11 and abn.isdigit()


def parse_date_string(date_text: str) -> datetime:
    """
    Parse various date formats commonly found on ABR website
    """
    if not date_text:
        return None
    
    date_text = date_text.strip()
    
    # List of date formats to try
    formats = [
        "%d %b %Y",      # 01 Jan 2020
        "%d %B %Y",      # 01 January 2020
        "%d/%m/%Y",      # 01/01/2020
        "%m/%d/%Y",      # 01/01/2020 (US format)
        "%Y-%m-%d",      # 2020-01-01
        "%d-%m-%Y",      # 01-01-2020
        "%d.%m.%Y",      # 01.01.2020
        "%b %d, %Y",     # Jan 01, 2020
        "%B %d, %Y",     # January 01, 2020
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_text, fmt)
        except ValueError:
            continue
    
    return None


async def fetch_abn_registration_date(abn_id: str) -> datetime:
    """
    Fetch ABN registration date from ABR website with caching
    """
    # Validate ABN format first
    if not validate_abn_format(abn_id):
        return None
    
    # Check cache first
    if abn_id in _abn_date_cache:
        return _abn_date_cache[abn_id]
    
    try:
        url = f"https://abr.business.gov.au/ABN/View?id={abn_id}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
        
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Look for ABN registration date more specifically
        # The ABR website has specific sections for different dates
        
        registration_date = None
        
        # Method 1: Look for specific ABN registration information
        # Try to find the ABN status section which contains the registration date
        abn_status_section = soup.find("h2", string=re.compile("ABN details", re.IGNORECASE))
        if abn_status_section:
            # Look for date information in the following table
            next_table = abn_status_section.find_next("table")
            if next_table:
                rows = next_table.find_all("tr")
                for row in rows:
                    cells = row.find_all(["th", "td"])
                    if len(cells) >= 2:
                        header_text = cells[0].get_text(strip=True).lower()
                        if any(keyword in header_text for keyword in ["effective", "registered", "date"]):
                            date_text = cells[1].get_text(strip=True)
                            parsed_date = parse_date_string(date_text)
                            if parsed_date:
                                registration_date = parsed_date
                                break
        
        # Method 2: Look for specific table with "Date registered for GST" or similar
        if not registration_date:
            tables = soup.find_all("table")
            for table in tables:
                rows = table.find_all("tr")
                for row in rows:
                    cells = row.find_all(["th", "td"])
                    if len(cells) >= 2:
                        header_text = cells[0].get_text(strip=True)
                        # More specific patterns for actual registration dates
                        if re.search(r"Date registered for GST|ABN status.*from|Effective from", header_text, re.IGNORECASE):
                            date_text = cells[1].get_text(strip=True)
                            # Skip "Active" or status text, look for actual dates
                            if not re.search(r"^(Active|Inactive|Cancelled)$", date_text, re.IGNORECASE):
                                parsed_date = parse_date_string(date_text)
                                if parsed_date:
                                    registration_date = parsed_date
                                    break
                if registration_date:
                    break
        
        # Method 3: If still no date found, be more careful about which dates we accept
        if not registration_date:
            # Look for date patterns but be more selective
            text_content = soup.get_text()
            
            # Find all dates in format "1 Jan 2020" but exclude common system dates
            date_matches = re.findall(r'\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4})\b', text_content, re.IGNORECASE)
            
            # Filter out common system dates that appear on all pages
            excluded_dates = [
                "1 Nov 2014",  # This seems to be appearing on all pages - likely a system date
                "01 Nov 2014"
            ]
            
            for date_match in date_matches:
                if date_match not in excluded_dates:
                    parsed_date = parse_date_string(date_match)
                    if parsed_date and 2000 <= parsed_date.year <= 2024:  # Reasonable business registration year range
                        registration_date = parsed_date
                        break
        
        # Cache the result (even if None to avoid repeated failed lookups)
        _abn_date_cache[abn_id] = registration_date
        return registration_date
        
    except Exception as e:
        # Cache the None result to avoid repeated failed attempts
        _abn_date_cache[abn_id] = None
        return None


def calculate_years_in_business_from_abn(abn_registration_date: datetime) -> str:
    """
    Calculate years and months in business from ABN registration date.
    Returns format: "X years Y months"
    """
    if not abn_registration_date:
        return "0 years 0 months"
    
    now = datetime.now(abn_registration_date.tzinfo) if abn_registration_date.tzinfo else datetime.now()
    
    # Calculate the difference
    years = now.year - abn_registration_date.year
    months = now.month - abn_registration_date.month
    
    # Adjust if the current month/day is before the registration month/day
    if months < 0:
        years -= 1
        months += 12
    elif months == 0 and now.day < abn_registration_date.day:
        years -= 1
        months = 11
    elif now.day < abn_registration_date.day:
        months -= 1
        if months < 0:
            years -= 1
            months = 11
    
    # Format the response
    year_text = "year" if years == 1 else "years"
    month_text = "month" if months == 1 else "months"
    
    return f"{years} {year_text} {months} {month_text}"


def calculate_years_in_business(created_at: datetime) -> str:
    """
    Calculate years and months in business from created_at timestamp.
    Returns format: "X years Y months"
    """
    if not created_at:
        return "0 years 0 months"
    
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
    
    # Format the response
    year_text = "year" if years == 1 else "years"
    month_text = "month" if months == 1 else "months"
    
    return f"{years} {year_text} {months} {month_text}"


@router.get("/details", response_model=dict)
async def get_vendor_details(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
   
    # Fetch vendor login
    stmt = select(VendorLogin).where(
        VendorLogin.user_id == user_id,
        VendorLogin.username == "unknown"
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

    # Decrypt email
    decrypted_email = vendor.email
    try:
        decrypted_email = decrypt_data(vendor.email)
    except Exception as e:
        print(f"Failed to decrypt email for vendor {vendor.user_id}: {str(e)}")
        # Keep original email if decryption fails
        decrypted_email = vendor.email

    return {
        "vendor_login": {
            "user_id": vendor.user_id,
            "email": decrypted_email,
            "is_verified": vendor.is_verified,
            "is_active": vendor.is_active,
            "last_login": vendor.last_login,
            "created_at": vendor.created_at,
        },
        "business_profile": {
            "store_name": business_profile.store_name if business_profile else None,
            "store_slug": business_profile.store_slug if business_profile else None,
            "industry": business_profile.industry if business_profile else None,
            "location": business_profile.location if business_profile else None,
            "is_approved": business_profile.is_approved if business_profile else None,
            "profile_details": decrypted_profile_details,
            "purpose": business_profile.purpose if business_profile else {},
        },
    }



@router.get("/details/by-slug", response_model=dict)
async def get_vendor_details(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    # Step 1: Fetch the business profile by slug
    stmt = select(BusinessProfile).where(BusinessProfile.store_slug == slug)
    result = await db.execute(stmt)
    business_profile = result.scalar_one_or_none()
 
    if not business_profile:
        raise HTTPException(status_code=404, detail="Business profile not found")
 
    # Step 2: Get the vendor login using business_profile.profile_ref_id
    vendor_stmt = select(VendorLogin).where(
        VendorLogin.business_profile_id == business_profile.profile_ref_id
    )
    vendor_result = await db.execute(vendor_stmt)
    vendor = vendor_result.scalar_one_or_none()
 
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor login not found")
 
    # Step 3: Decrypt profile details if present
    decrypted_profile_details = {}
    if business_profile.profile_details:
        try:
            raw_data = business_profile.profile_details
            if isinstance(raw_data, str):
                raw_data = json.loads(raw_data)
            decrypted_profile_details = decrypt_dict_values(raw_data)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to decrypt profile details: {str(e)}")
   
    # Step 4: Decrypt email
    decrypted_email = vendor.email
    try:
        decrypted_email = decrypt_data(vendor.email)
    except Exception as e:
        print(f"Failed to decrypt email for vendor {vendor.user_id}: {str(e)}")
        # Keep original email if decryption fails
        decrypted_email = vendor.email

    # Calculate years in business from ABN registration date
    years_in_business = "0 years 0 months"  # Default value
   
    if business_profile and business_profile.abn_id:
        try:
            # Decrypt ABN ID to get the actual ABN number  
            decrypted_abn = decrypt_data(business_profile.abn_id)
            abn_registration_date = await fetch_abn_registration_date(decrypted_abn)
           
            if abn_registration_date:
                years_in_business = calculate_years_in_business_from_abn(abn_registration_date)
            else:
                # Fallback to account creation date if ABN date not available
                years_in_business = calculate_years_in_business(vendor.created_at)
        except Exception as e:
            print(f"Error calculating ABN-based years in business for vendor {vendor.user_id}: {e}")
            # Fallback to account creation date
            years_in_business = calculate_years_in_business(vendor.created_at)
    else:
        # No business profile or ABN, use account creation date
        years_in_business = calculate_years_in_business(vendor.created_at)
 
    return {
        "vendor_login": {
            "user_id": vendor.user_id,
            "email": decrypted_email,
            "is_verified": vendor.is_verified,
            "is_active": vendor.is_active,
            "last_login": vendor.last_login,
            "created_at": vendor.created_at,
        },
        "business_profile": {
            "store_name": business_profile.store_name,
            "banner_image": get_media_url(business_profile.business_logo),
            "industry": business_profile.industry,
            "location": business_profile.location,
            "is_approved": business_profile.is_approved,
            "profile_details": decrypted_profile_details,
            "purpose": business_profile.purpose,
            "years_in_bussiness":years_in_business,
        },
    }



# @router.get("/vendors/all", response_model=list[dict])
# async def get_all_vendors(db: AsyncSession = Depends(get_db)):
#     # Exclude vendors with username "unknown"
#     stmt = (
#         select(VendorLogin)
#         .where(VendorLogin.username == "unknown") 
#         .options(
#             joinedload(VendorLogin.business_profile).joinedload(BusinessProfile.industry_obj)
#         )
#     )
    
#     result = await db.execute(stmt)
#     vendors = result.scalars().all()

#     all_vendor_data = []

#     for vendor in vendors:
#         business_profile = vendor.business_profile

#         # Decrypt profile_details if present
#         decrypted_profile_details = {}
#         if business_profile and business_profile.profile_details:
#             try:
#                 raw_data = business_profile.profile_details
#                 if isinstance(raw_data, str):
#                     raw_data = json.loads(raw_data)
#                 decrypted_profile_details = decrypt_dict_values(raw_data)
#             except Exception as e:
#                 decrypted_profile_details = {"error": f"Decryption failed: {str(e)}"}

#         decrypted_email = decrypt_data(vendor.email)

#         industry_name = (
#             business_profile.industry_obj.industry_name
#             if business_profile and business_profile.industry_obj
#             else None
#         )

#         all_vendor_data.append({
#             "vendor_login": {
#                 "user_id": vendor.user_id,
#                 "email": decrypted_email,
#                 "is_verified": vendor.is_verified,
#                 "is_active": vendor.is_active,
#                 "last_login": vendor.last_login,
#                 "created_at": vendor.created_at,
#             },
#             "business_profile": {
#                 "store_name": business_profile.store_name if business_profile else None,
#                 "store_slug": business_profile.store_slug if business_profile else None,
#                 "industry_id": business_profile.industry if business_profile else None,
#                 "industry_name": industry_name,
#                 "location": business_profile.location if business_profile else None,
#                 "is_approved": business_profile.is_approved if business_profile else None,
#                 "profile_details": decrypted_profile_details,
#                 "purpose": business_profile.purpose if business_profile else {},
#                 "payment_preference": business_profile.payment_preference if business_profile else [],
#             },
#         })

#     return all_vendor_data

@router.get("/vendors/all", response_model=list[dict])
async def get_all_vendors(db: AsyncSession = Depends(get_db)):
    stmt = select(VendorLogin).options(
        joinedload(VendorLogin.business_profile).joinedload(BusinessProfile.industry_obj)
    ).where(VendorLogin.username == "unknown")
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
                "store_slug": business_profile.store_slug if business_profile else None,
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
    ).where(VendorLogin.username == "unknown")
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
        
        # Calculate years in business from ABN registration date
        years_in_business = "0 years 0 months"  # Default value
        
        if business_profile and business_profile.abn_id:
            try:
                # Decrypt ABN ID to get the actual ABN number  
                decrypted_abn = decrypt_data(business_profile.abn_id)
                abn_registration_date = await fetch_abn_registration_date(decrypted_abn)
                
                if abn_registration_date:
                    years_in_business = calculate_years_in_business_from_abn(abn_registration_date)
                else:
                    # Fallback to account creation date if ABN date not available
                    years_in_business = calculate_years_in_business(vendor.created_at)
            except Exception as e:
                print(f"Error calculating ABN-based years in business for vendor {vendor.user_id}: {e}")
                # Fallback to account creation date
                years_in_business = calculate_years_in_business(vendor.created_at)
        else:
            # No business profile or ABN, use account creation date
            years_in_business = calculate_years_in_business(vendor.created_at)
        
        vendor_details = VendorDetailsResponse(
            vendor_id=vendor.user_id,
            store_name=business_profile.store_name if business_profile else None,
            store_slug=business_profile.store_slug if business_profile else None,
            location=business_profile.location if business_profile else None,
            banner_image=get_media_url(business_profile.business_logo) if business_profile else None,
            # store_logo=business_profile.business_logo if business_profile else None,  # Using business_logo as store_logo
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
    store_slug: str,
    db: AsyncSession = Depends(get_db)
):

    # First, find the business profile using store_slug
    business_profile_stmt = select(BusinessProfile).where(
        BusinessProfile.store_slug == store_slug
    )
    business_profile_result = await db.execute(business_profile_stmt)
    business_profile = business_profile_result.scalar_one_or_none()
    
    if not business_profile:
        raise HTTPException(status_code=404, detail=f"Store not found with slug: {store_slug}")
    
    # Get the vendor using the business profile
    vendor_stmt = select(VendorLogin).options(
        joinedload(VendorLogin.business_profile)
    ).where(VendorLogin.business_profile_id == business_profile.profile_ref_id)
    vendor_result = await db.execute(vendor_stmt)
    vendor = vendor_result.scalar_one_or_none()
    
    if not vendor:
        raise HTTPException(status_code=404, detail=f"Vendor not found for store: {store_slug}")
    
    # Get vendor's products with category information
    products_stmt = select(Product, Category).join(
        Category, Product.category_id == Category.category_id
    ).where(Product.vendor_id == vendor.user_id)
    
    products_result = await db.execute(products_stmt)
    products_data = products_result.all()
    
    # Process products with all details
    products_info = []
    for product, category in products_data:
        # Process image URLs
        processed_images = product.images
        if product.images and "urls" in product.images:
            image_urls = [get_media_url(url) for url in product.images["urls"]]
            processed_images = {"urls": image_urls}
        
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
            "images": processed_images,
            "tags_and_relationships": product.tags_and_relationships,
            "status_flags": product.status_flags or {},
        })
    
    # Get vendor category management information
    category_management_stmt = select(
        VendorCategoryManagement,
        Category,
        SubCategory
    ).join(
        Category, VendorCategoryManagement.category_id == Category.category_id
    ).outerjoin(
        SubCategory, VendorCategoryManagement.subcategory_id == SubCategory.subcategory_id
    ).where(
        VendorCategoryManagement.vendor_ref_id == vendor.user_id,
        VendorCategoryManagement.is_active == False  # False means active
    )
    
    category_management_result = await db.execute(category_management_stmt)
    category_management_data = category_management_result.all()
    
    # Process category management information - group by category
    category_dict = {}
    for ven_cat_mgmt, category, subcategory in category_management_data:
        category_id = category.category_id
        
        # Initialize category if not exists
        if category_id not in category_dict:
            category_dict[category_id] = {
                "category_id": category.category_id,
                "category_name": category.category_name,
                "subcategories": []
            }
        
        # Add subcategory if it exists and not already added
        if subcategory:
            subcategory_info = {
                "subcategory_id": subcategory.subcategory_id,
                "subcategory_name": subcategory.subcategory_name
            }
            # Check if subcategory is already added to avoid duplicates
            if subcategory_info not in category_dict[category_id]["subcategories"]:
                category_dict[category_id]["subcategories"].append(subcategory_info)
    
    # Convert dictionary to list
    category_management_info = list(category_dict.values())
    
    # Get store name and slug from business profile
    store_name = business_profile.store_name
    store_slug_response = business_profile.store_slug
    
    return VendorProductsAndCategoriesResponse(
        vendor_id=vendor.user_id,
        store_name=store_name,
        store_slug=store_slug_response,
        banner_image=get_media_url(business_profile.business_logo) if business_profile else None,
        products=products_info,
        total_products=len(products_info),
        category_management=category_management_info
    )


@router.get("/all-vendors-and-employees", response_model=list[dict])
async def get_all_vendors_and_employees(db: AsyncSession = Depends(get_db)):
    """
    Get all vendors and employees with proper identification.
    - If username = "unknown", it's a vendor
    - If username != "unknown", it's a vendor employee
    """
    stmt = select(VendorLogin, Role.role_name).outerjoin(
        Role, VendorLogin.role == Role.role_id
    ).options(
        joinedload(VendorLogin.business_profile).joinedload(BusinessProfile.industry_obj)
    )
    result = await db.execute(stmt)
    all_users = result.all()

    all_users_data = []

    for user_data in all_users:
        vendor_login, role_name = user_data
        business_profile = vendor_login.business_profile

        # Decrypt email
        try:
            decrypted_email = decrypt_data(vendor_login.email)
        except Exception:
            decrypted_email = "encrypted_email"

        # Determine user type based on username
        if vendor_login.username == "unknown":
            user_type = "vendor"
            username_display = "N/A"  # Vendors don't have usernames
        else:
            user_type = "vendor_employee"
            # For employees, try to decrypt username
            try:
                username_display = decrypt_data(vendor_login.username)
            except Exception:
                username_display = "encrypted_username"

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

        industry_name = (
            business_profile.industry_obj.industry_name
            if business_profile and business_profile.industry_obj
            else None
        )

        user_data_dict = {
            "user_type": user_type,
            "vendor_login": {
                "user_id": vendor_login.user_id,
                "username": username_display,
                "email": decrypted_email,
                "is_verified": vendor_login.is_verified,
                "is_active": vendor_login.is_active,
                "last_login": vendor_login.last_login,
                "created_at": vendor_login.created_at,
                "role_id": vendor_login.role,
                "role_name": role_name,
                "vendor_ref_id": vendor_login.vendor_ref_id,
            },
            "business_profile": {
                "store_name": business_profile.store_name if business_profile else None,
                "store_slug": business_profile.store_slug if business_profile else None,
                "industry_id": business_profile.industry if business_profile else None,
                "industry_name": industry_name,
                "location": business_profile.location if business_profile else None,
                "is_approved": business_profile.is_approved if business_profile else None,
                "profile_details": decrypted_profile_details,
                "purpose": business_profile.purpose if business_profile else {},
                "payment_preference": business_profile.payment_preference if business_profile else [],
            },
        }

        all_users_data.append(user_data_dict)

    return all_users_data