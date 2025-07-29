from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.models.superadmin import BusinessProfile, VendorLogin
from db.sessions.database import get_db


router = APIRouter()


@router.post("/vendor/approve", response_model=dict)
async def approve_vendor(
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
    vendor.is_verified = 1
    business_profile.is_approved = 1

    db.add_all([vendor, business_profile])
    await db.commit()

    return {"message": f"Vendor approved successfully"}




@router.post("/vendor/reject", response_model=dict)
async def approve_vendor(
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
    business_profile.is_approved = 2

    db.add_all([vendor, business_profile])
    await db.commit()

    return {"message": f"Vendor approved successfully"}






@router.put("/vendor/soft-delete", response_model=dict)
async def soft_delete_vendor(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(VendorLogin).where(VendorLogin.user_id == user_id)
    result = await db.execute(stmt)
    vendor = result.scalar_one_or_none()

    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    if vendor.is_active:
        return {"message": f"Vendor '{user_id}' is already inactive."}

    vendor.is_active = True
    db.add(vendor)
    await db.commit()

    return {"message": f"Vendor '{user_id}' has been soft deleted (deactivated) successfully."}