
import json
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    Depends,
    HTTPException,
)
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse
from sqlalchemy import select

from schemas.vendor_onboarding import OnboardingRequest
from utils.id_generators import encrypt_data, encrypt_dict_values, generate_digits_letters, hash_data, decrypt_data
from db.models.superadmin import BusinessProfile, VendorLogin, Industries
from services.business_profile import fetch_abn_details, validate_abn_id
from services.email_service import email_service
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
    background_tasks: BackgroundTasks,
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
            return JSONResponse(status_code=404, content={"message": "Invalid profile reference ID. Profile not found."})

        # Validate industry_id exists
        industry_check_stmt = select(Industries).where(
            Industries.industry_id == data.industry_id
        )
        industry_result = await db.execute(industry_check_stmt)
        existing_industry = industry_result.scalar_one_or_none()

        if not existing_industry:
            return JSONResponse(status_code=404, content={"message": "Industry ID not found."})
        
        # Check if industry is active (is_active = true means inactive)
        if existing_industry.is_active == True:
            return JSONResponse(status_code=400, content={"message": "Industry is inactive."})

        # Clean and normalize store name
        store_name_cleaned = ' '.join(data.store_name.strip().split())  # Remove extra spaces between words
        
        # Validate store name uniqueness
        store_name_check_stmt = select(BusinessProfile).where(
            BusinessProfile.store_name.ilike(store_name_cleaned)
        )
        store_name_result = await db.execute(store_name_check_stmt)
        existing_store_name = store_name_result.scalar_one_or_none()

        if existing_store_name:
            return JSONResponse(status_code=409, content={"message": "Store name already exists. Please choose a different store name."})

        # Additional store name validations
        store_name_lower = store_name_cleaned.lower()
        reserved_names = ['admin', 'api', 'www', 'mail', 'support', 'help', 'info', 'test', 'demo', 'shop', 'store']
        if store_name_lower in reserved_names:
            return JSONResponse(status_code=400, content={"message": "Store name contains reserved words. Please choose a different name."})

        # Validate store name doesn't start or end with special characters (spaces auto-cleaned)
        if store_name_cleaned.startswith(('-', '_')) or store_name_cleaned.endswith(('-', '_')):
            return JSONResponse(status_code=400, content={"message": "Store name cannot start or end with special characters."})

        # Clean and normalize location - automatically handle all spacing and comma issues
        location_cleaned = data.location.strip()
        location_cleaned = ' '.join(location_cleaned.split())  # Remove extra spaces between words
        location_cleaned = ','.join([part.strip() for part in location_cleaned.split(',')])  # Clean spaces around commas
        
        # Remove any empty parts caused by consecutive commas
        location_parts = [part for part in location_cleaned.split(',') if part.strip()]
        location_cleaned = ', '.join(location_parts)
        
        # Auto-clean: Remove leading/trailing commas if present
        location_cleaned = location_cleaned.strip(', ')
        
        # Validate location format (only check meaningful limits)
        if len(location_parts) > 5:
            return JSONResponse(status_code=400, content={"message": "Location format invalid. Too many comma-separated values."})

        # Fetch and validate ABN details
        abn_data = await fetch_abn_details(abn_id)
        if not abn_data:
            return JSONResponse(status_code=404, content={"message": "Unable to fetch ABN details."})

        # Check if ABN already exists
        abn_hash = hash_data(abn_id)
        abn_check_stmt = select(BusinessProfile).where(
            BusinessProfile.abn_hash == abn_hash
        )
        abn_result = await db.execute(abn_check_stmt)
        existing_abn = abn_result.scalar_one_or_none()

        if existing_abn:
            return JSONResponse(status_code=409, content={"message": "ABN number already exists. This business is already registered."})

        # Encrypt ABN and profile details
        encrypted_abn_id = encrypt_data(abn_id)
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
            store_name=store_name_cleaned,
            store_url=str(data.store_url),
            location=location_cleaned,
            industry=data.industry_id,
            purpose=json.dumps([p.value for p in data.purpose]),
            ref_number=ref_number
        )

        db.add(new_profile)
        await db.commit()
        await db.refresh(new_profile)

        # Get vendor email for sending onboarding confirmation email
        try:
            vendor_email = decrypt_data(existing_profile.email)
            business_name = store_name_cleaned
            vendor_name = business_name  # Using business name as vendor name
            
            # Send onboarding confirmation email with reference number
            background_tasks.add_task(
                email_service.send_vendor_onboarding_email,
                email=vendor_email,
                vendor_name=vendor_name,
                business_name=business_name,
                reference_number=ref_number,  # Using reference number
                status="Active"
            )
        except Exception as email_error:
            # Log the error but don't fail the onboarding process
            print(f"Warning: Failed to send onboarding email: {str(email_error)}")

        return JSONResponse(
            status_code=201,
            content={
                "message": "Vendor onboarding completed successfully. Confirmation email sent.",
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