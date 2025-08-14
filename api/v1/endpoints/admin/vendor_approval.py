from datetime import datetime
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import math

from db.models.superadmin import BusinessProfile, VendorLogin, Product, Category, SubCategory, Industries
from db.sessions.database import get_db
from schemas.vendor_management import RejectRequest, VendorActionRequest, VendorActionResponse, VendorStatusResponse
from schemas.products import AllProductsListResponse, AllProductsResponse
from utils.file_uploads import get_media_url
from utils.id_generators import decrypt_data
from utils.email_utils.vendor_emails import send_vendor_approval_email, send_vendor_rejection_email


router = APIRouter()


@router.post("/vendor/approve", response_model=dict)
async def approve_vendor(
    user_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    # Fetch vendor
    stmt = select(VendorLogin).where(VendorLogin.user_id == user_id)
    result = await db.execute(stmt)
    vendor = result.scalar_one_or_none()

    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    # Fetch business profile
    profile_stmt = select(BusinessProfile).where(
        BusinessProfile.profile_ref_id == vendor.business_profile_id
    )
    profile_result = await db.execute(profile_stmt)
    business_profile = profile_result.scalar_one_or_none()

    if not business_profile:
        raise HTTPException(status_code=404, detail="Business profile not found")

    # Update values
    vendor.is_verified = 1
    business_profile.is_approved = 2
    business_profile.approved_date = datetime.utcnow() 

    db.add(vendor)
    db.add(business_profile)
    await db.commit()
    await db.refresh(vendor)
    
    # Send approval email in background
    try:
        vendor_email = decrypt_data(vendor.email)
        vendor_name = business_profile.store_name or "Vendor"
        business_name = business_profile.store_name or "Your Business"
        reference_id = business_profile.ref_number
        
        background_tasks.add_task(
            send_vendor_approval_email,
            email=vendor_email,
            vendor_name=vendor_name,
            business_name=business_name,
            reference_id=reference_id,
        )
    except Exception as email_error:
        # Log the error but don't fail the approval process
        print(f"Warning: Failed to send approval email: {str(email_error)}")
    
    return {"message": f"Vendor approved successfully. Approval email sent."}




@router.post("/vendor/reject", response_model=dict)
async def reject_vendor(
    user_id: str,
    data: RejectRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    # Fetch vendor
    stmt = select(VendorLogin).where(VendorLogin.user_id == user_id)
    result = await db.execute(stmt)
    vendor = result.scalar_one_or_none()

    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    # Fetch business profile
    profile_stmt = select(BusinessProfile).where(
        BusinessProfile.profile_ref_id == vendor.business_profile_id
    )
    profile_result = await db.execute(profile_stmt)
    business_profile = profile_result.scalar_one_or_none()

    if not business_profile:
        raise HTTPException(status_code=404, detail="Business profile not found")

    # Update values
    vendor.is_verified = 0
    business_profile.is_approved = -1
    business_profile.reviewer_comment = data.comment

    db.add_all([vendor, business_profile])
    await db.commit()

    # Send rejection email in background
    try:
        vendor_email = decrypt_data(vendor.email)
        vendor_name = business_profile.store_name or "Vendor"
        business_name = business_profile.store_name or "Your Business"
        reference_id = business_profile.ref_number
        
        background_tasks.add_task(
            send_vendor_rejection_email,
            email=vendor_email,
            vendor_name=vendor_name,
            business_name=business_name,
            reference_id=reference_id,
            reviewer_comment=data.comment,
        )
    except Exception as email_error:
        # Log the error but don't fail the rejection process
        print(f"Warning: Failed to send rejection email: {str(email_error)}")

    return {"message": f"Vendor rejected successfully. Rejection email sent."}


@router.post("/vendor/onhold", response_model=dict)
async def reject_onhold(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    # Fetch vendor
    stmt = select(VendorLogin).where(VendorLogin.user_id == user_id)
    result = await db.execute(stmt)
    vendor = result.scalar_one_or_none()

    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    # Fetch business profile
    profile_stmt = select(BusinessProfile).where(
        BusinessProfile.profile_ref_id == vendor.business_profile_id
    )
    profile_result = await db.execute(profile_stmt)
    business_profile = profile_result.scalar_one_or_none()

    if not business_profile:
        raise HTTPException(status_code=404, detail="Business profile not found")

    # Update values
    vendor.is_verified = 0
    business_profile.is_approved = 1
   

    db.add_all([vendor, business_profile])
    await db.commit()

    return {"message": f"Vendor onholded successfully"}



@router.put("/vendor/soft-delete", response_model=VendorActionResponse)
async def soft_delete_vendor(
    request: VendorActionRequest,
    db: AsyncSession = Depends(get_db),
):

    stmt = select(VendorLogin).where(VendorLogin.user_id == request.user_id)
    result = await db.execute(stmt)
    vendor = result.scalar_one_or_none()

    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    if vendor.is_active:
        return VendorActionResponse(
            message=f"Vendor '{request.user_id}' is already inactive.",
            user_id=request.user_id,
            status="inactive"
        )

    vendor.is_active = True
    db.add(vendor)
    await db.commit()

    return VendorActionResponse(
        message=f"Vendor '{request.user_id}' has been soft deleted (deactivated) successfully.",
        user_id=request.user_id,
        status="inactive"
    )


@router.put("/vendor/restore", response_model=VendorActionResponse)
async def restore_vendor(
    request: VendorActionRequest,
    db: AsyncSession = Depends(get_db),
):

    stmt = select(VendorLogin).where(VendorLogin.user_id == request.user_id)
    result = await db.execute(stmt)
    vendor = result.scalar_one_or_none()

    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    if not vendor.is_active:
        return VendorActionResponse(
            message=f"Vendor '{request.user_id}' is already active.",
            user_id=request.user_id,
            status="active"
        )

    vendor.is_active = False
    db.add(vendor)
    await db.commit()

    return VendorActionResponse(
        message=f"Vendor '{request.user_id}' has been restored (activated) successfully.",
        user_id=request.user_id,
        status="active"
    )


@router.get("/vendor/status/{user_id}", response_model=VendorStatusResponse)
async def get_vendor_status(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):

    stmt = select(VendorLogin).where(VendorLogin.user_id == user_id)
    result = await db.execute(stmt)
    vendor = result.scalar_one_or_none()

    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    # Fetch business profile to get store name
    profile_stmt = select(BusinessProfile).where(
        BusinessProfile.profile_ref_id == vendor.business_profile_id
    )
    profile_result = await db.execute(profile_stmt)
    business_profile = profile_result.scalar_one_or_none()

    # Get store name from business profile, fallback to username if not found
    store_name = business_profile.store_name if business_profile else vendor.username

    # Decrypt email before returning
    decrypted_email = decrypt_data(vendor.email)

    return VendorStatusResponse(
        user_id=vendor.user_id,
        username=store_name,
        email=decrypted_email,
        is_active=vendor.is_active,
        is_verified=vendor.is_verified,
        last_login=vendor.last_login.isoformat() if vendor.last_login else None,
        created_at=vendor.created_at.isoformat()
    )


@router.get("/products/all", response_model=AllProductsListResponse)
async def get_all_products(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    # Get total count first
    count_stmt = (
        select(func.count(Product.product_id))
        .join(Category, Product.category_id == Category.category_id)
        .outerjoin(SubCategory, Product.subcategory_id == SubCategory.subcategory_id)
        .outerjoin(VendorLogin, Product.vendor_id == VendorLogin.user_id)
        .outerjoin(BusinessProfile, VendorLogin.business_profile_id == BusinessProfile.profile_ref_id)
        .outerjoin(Industries, Category.industry_id == Industries.industry_id)
    )
    
    total_result = await db.execute(count_stmt)
    total_count = total_result.scalar()
    
    # Calculate pagination
    total_pages = math.ceil(total_count / per_page)
    offset = (page - 1) * per_page
    
    # Query to get paginated products with their related data using proper joins
    stmt = (
        select(Product, Category, SubCategory, VendorLogin, BusinessProfile, Industries)
        .join(Category, Product.category_id == Category.category_id)
        .outerjoin(SubCategory, Product.subcategory_id == SubCategory.subcategory_id)
        .outerjoin(VendorLogin, Product.vendor_id == VendorLogin.user_id)
        .outerjoin(BusinessProfile, VendorLogin.business_profile_id == BusinessProfile.profile_ref_id)
        .outerjoin(Industries, Category.industry_id == Industries.industry_id)
        .offset(offset)
        .limit(per_page)
        .order_by(Product.timestamp.desc())  # Order by timestamp for consistent pagination
    )
    
    result = await db.execute(stmt)
    products_data = result.all()
    
    products_list = []
    for product, category, subcategory, vendor_login, business_profile, industry in products_data:
        # Extract product name from identification JSONB field
        product_name = product.identification.get('product_name', '') if product.identification else ''
        
        # Extract product image from images JSONB field (get first available image from urls array)
        product_image = None
        if product.images and "urls" in product.images and product.images["urls"]:
            # Get the first image URL and convert it to full media URL
            product_image = get_media_url(product.images["urls"][0])
        
        # Get store name from business profile
        store_name = business_profile.store_name if business_profile else None
        
        product_response = AllProductsResponse(
            vendor_id=product.vendor_id,
            store_name=store_name,
            product_id=product.product_id,
            product_name=product_name,
            product_image=product_image,
            product_slug=product.slug,
            category_id=category.category_id,
            category_name=category.category_name,
            subcategory_id=subcategory.subcategory_id if subcategory else None,
            subcategory_name=subcategory.subcategory_name if subcategory else None,
            industry_id=industry.industry_id if industry else None,
            industry_name=industry.industry_name if industry else None
        )
        products_list.append(product_response)
    
    return AllProductsListResponse(
        products=products_list,
        total_count=total_count,
        page=page,
        per_page=per_page,
        total_pages=total_pages
    )
