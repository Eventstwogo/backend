
import json
from fastapi import (
    APIRouter,
    Body,
    Depends,
    HTTPException,
)
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse
from sqlalchemy import select

from schemas.vendor_onboarding import OnboardingRequest
from utils.id_generators import encrypt_data, encrypt_dict_values, generate_digits_letters, hash_data
from db.models.superadmin import BusinessProfile, VendorLogin
from services.business_profile import fetch_abn_details, validate_abn_id
from db.sessions.database import get_db


router = APIRouter()


@router.get("/abn/verify/{abn_id}")
async def verify_abn(abn_id: str):
    try:
        abn_data = await fetch_abn_details(abn_id)
        return {
            "success": True,
            "data": abn_data
        }
    except HTTPException as he:
        return JSONResponse(status_code=he.status_code, content={"success": False, "message": he.detail})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})


@router.post("/onboarding")
async def vendor_onboarding(
    data: OnboardingRequest,
    abn_id: str = Depends(validate_abn_id),
    db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    try:
        # Validate profile_ref_id exists
        profile_check_stmt = select(VendorLogin).where(
            VendorLogin.business_profile_id == data.profile_ref_id
        )
        profile_result = await db.execute(profile_check_stmt)
        existing_profile = profile_result.scalar_one_or_none()

        if not existing_profile:
            return JSONResponse(status_code=404, content={"message": "Profile not found."})

        # Fetch and validate ABN details
        abn_data = await fetch_abn_details(abn_id)
        if not abn_data:
            return JSONResponse(status_code=404, content={"message": "Unable to fetch ABN details."})

        # Encrypt ABN and profile details
        encrypted_abn_id = encrypt_data(abn_id)
        abn_hash = hash_data(abn_id)
        encrypted_profile_dict = encrypt_dict_values(abn_data)
        encrypted_profile_json = json.dumps(encrypted_profile_dict)

        ref_number = generate_digits_letters()

        # Create new BusinessProfile instance
        new_profile = BusinessProfile(
            profile_ref_id=data.profile_ref_id,
            abn_id=encrypted_abn_id,
            abn_hash=abn_hash,
            profile_details=encrypted_profile_json,
            payment_preference=[p.value for p in data.payment_preference],
            store_name=data.store_name,
            store_url=str(data.store_url),
            location=data.location,
            industry=str(data.industry),
            purpose=json.dumps([p.value for p in data.purpose]),
            ref_number=ref_number
        )

        db.add(new_profile)
        await db.commit()
        await db.refresh(new_profile)

        return JSONResponse(
            status_code=201,
            content={
                "message": "Vendor onboarding completed successfully",
                "reference_number": ref_number,
                "profile_ref_id": data.profile_ref_id,
                "store_url": str(data.store_url)
            }
        )

    except HTTPException as he:
        raise he
    except Exception as e:
        await db.rollback()
        return JSONResponse(
            status_code=500,
            content={"message": f"An unexpected error occurred: {str(e)}"}
        )