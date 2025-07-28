import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from utils.id_generators import decrypt_data, decrypt_dict_values
from db.models.superadmin import BusinessProfile, VendorLogin
from db.sessions.database import get_db


router = APIRouter()


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