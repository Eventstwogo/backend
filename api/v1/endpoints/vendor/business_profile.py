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



@router.post("/business-profile", status_code=status.HTTP_201_CREATED)
async def business_profile(
    user_data: VendorBusinessProfileRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    abn_id = validate_abn_id(user_data.abn_id)

    # Lookup by hash
    if await business_profile_exists(db, abn_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Business profile with this ABN already exists."
        )

    abn_data = await fetch_abn_details(abn_id)

    encrypted_abn_id = encrypt_data(abn_id)
    abn_hash = hash_data(abn_id)

    # Encrypt values only
    encrypted_profile_dict = encrypt_dict_values(abn_data)
    encrypted_profile_json = json.dumps(encrypted_profile_dict)

    new_profile = BusinessProfile(
        profile_ref_id=user_data.business_profile_id,
        abn_id=encrypted_abn_id,
        abn_hash=abn_hash,
        profile_details=encrypted_profile_json,
        business_logo="",
        is_approved=False
    )

    db.add(new_profile)
    await db.commit()
    await db.refresh(new_profile)

    return api_response(
        status_code=status.HTTP_201_CREATED,
        message="User business profile saved successfully.",
    )



@router.get("/business-profile", status_code=200)
async def get_business_profile(
    abn_id: str = Query(..., min_length=11, max_length=11),
    db: AsyncSession = Depends(get_db)
):
    abn_id = validate_abn_id(abn_id)
    abn_hash = hash_data(abn_id)

    result = await db.execute(
        select(BusinessProfile).where(BusinessProfile.abn_hash == abn_hash)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Business profile not found"
        )

    encrypted_profile_dict = json.loads(profile.profile_details)
    decrypted_profile = decrypt_dict_values(encrypted_profile_dict)

    return {
        "abn_id": abn_id,
        "profile_ref_id": profile.profile_ref_id,
        "profile_details": decrypted_profile,
        "is_approved": profile.is_approved
    }
