from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse
import json
from sqlalchemy import select

from schemas.business_profile import VendorBusinessProfileRequest
from utils.id_generators import decrypt_dict_values, encrypt_data, encrypt_dict_values, hash_data
from services.business_profile import business_profile_exists, fetch_abn_details, validate_abn_id
from core.api_response import api_response
from db.models.superadmin import BusinessProfile
from db.sessions.database import get_db

router = APIRouter()



# @router.post("/business-profile", status_code=status.HTTP_201_CREATED)
# async def business_profile(
#     user_data: VendorBusinessProfileRequest,
#     db: AsyncSession = Depends(get_db),
# ) -> JSONResponse:
#     abn_id = validate_abn_id(user_data.abn_id)

#     # Lookup by hash
#     if await business_profile_exists(db, abn_id):
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Business profile with this ABN already exists."
#         )

#     abn_data = await fetch_abn_details(abn_id)

#     encrypted_abn_id = encrypt_data(abn_id)
#     abn_hash = hash_data(abn_id)

#     # Encrypt values only
#     encrypted_profile_dict = encrypt_dict_values(abn_data)
#     encrypted_profile_json = json.dumps(encrypted_profile_dict)

#     new_profile = BusinessProfile(
#         profile_ref_id=user_data.business_profile_id,
#         abn_id=encrypted_abn_id,
#         abn_hash=abn_hash,
#         profile_details=encrypted_profile_json,
#         business_logo="",
#         is_approved=0
#     )

#     db.add(new_profile)
#     await db.commit()
#     await db.refresh(new_profile)

#     return api_response(
#         status_code=status.HTTP_201_CREATED,
#         message="User business profile saved successfully.",
#     )


@router.get("/business-profile", status_code=200)
async def get_business_profile(
    profile_ref_id: str = Query(..., min_length=6, max_length=12),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(BusinessProfile).where(BusinessProfile.profile_ref_id == profile_ref_id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Business profile not found"
        )

    # Decrypt and deserialize profile_details
    encrypted_profile_dict = json.loads(profile.profile_details)
    decrypted_profile = decrypt_dict_values(encrypted_profile_dict)

    # Deserialize purpose if it's JSON
    try:
        purpose_list = json.loads(profile.purpose)
    except Exception:
        purpose_list = profile.purpose  # fallback if not a JSON string

    return {
        "profile_ref_id": profile.profile_ref_id,
        "profile_details": decrypted_profile,
        "business_logo": profile.business_logo,
        "location": profile.location,
        "payment_preference": profile.payment_preference,
        "store_name": profile.store_name,
        "store_slug": profile.store_slug,
        "store_url": profile.store_url,
        "industry": profile.industry,
        "ref_number": profile.ref_number,
        "purpose": purpose_list,
        "is_approved": profile.is_approved,
        "timestamp": profile.timestamp
    }
