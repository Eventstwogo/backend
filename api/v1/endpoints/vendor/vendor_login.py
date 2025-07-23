from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from passlib.context import CryptContext
from pydantic import BaseModel

from utils.id_generators import hash_data
from db.models.superadmin import BusinessProfile, VendorLogin, VendorSignup, Config
from schemas.admin_user import AdminLoginRequest, AdminLoginResponse, AdminUserInfo
from db.sessions.database import get_db
from utils.jwt import create_access_token

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
router = APIRouter()

# Schema for store name availability check
class StoreNameCheckRequest(BaseModel):
    store_name: str

class StoreNameCheckResponse(BaseModel):
    status_code: int
    message: str



MAX_LOGIN_ATTEMPTS = 5

@router.post("/login", response_model=AdminLoginResponse)
async def login_user(
    login_data: AdminLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    
    email_hash = hash_data(login_data.email)
    
    # First check if user exists in VendorSignup and email verification status
    signup_stmt = select(VendorSignup).where(VendorSignup.email_hash == email_hash)
    signup_result = await db.execute(signup_stmt)
    signup_user = signup_result.scalar_one_or_none()
    
    if signup_user and not signup_user.email_flag:
        raise HTTPException(status_code=403, detail="Please verify your email before logging in. Check your inbox for the verification link.")
    
    # Find user by email in VendorLogin table
    stmt = select(VendorLogin).where(
        VendorLogin.email_hash == email_hash
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="Account not found")

    # Check if account is locked
    if user.login_status == 1:
        raise HTTPException(status_code=423, detail="Account is locked. Try after 24 hours.")

    # Compare password
    if not pwd_context.verify(login_data.password, user.password):
        # Increment failed login attempts
        user.login_failed_attempts += 1
        
        # Check if we've reached the maximum failed attempts
        if user.login_failed_attempts >= MAX_LOGIN_ATTEMPTS:
            user.login_status = 1  # Lock the account
            user.locked_time = datetime.utcnow()
            db.add(user)
            await db.commit()
            raise HTTPException(status_code=423, detail="Account is locked. Try after 24 hours.")
        
        db.add(user)
        await db.commit()
        remaining_attempts = MAX_LOGIN_ATTEMPTS - user.login_failed_attempts
        raise HTTPException(
            status_code=401, 
            detail=f"Incorrect password. {remaining_attempts} attempts remaining before account lock."
        )

    if user.is_active:
        raise HTTPException(status_code=403, detail="User is inactive")

    if not user.is_verified:
       raise HTTPException(status_code=402, detail="Your business profile is under verification, check again later.")

    # Successful login - update login tracking
    user.login_attempts += 1  # Increment successful login attempts
    user.login_failed_attempts = 0  # Reset failed attempts on successful login
    user.last_login = datetime.utcnow()
    user.login_status = 0  # Set to active
    
    # Ensure the user object is added to the session and commit changes
    db.add(user)
    await db.commit()
    await db.refresh(user)

    profile_stmt = select(
    BusinessProfile.is_approved,
    BusinessProfile.ref_number,
    BusinessProfile.industry 
        ).where(
            BusinessProfile.profile_ref_id == user.business_profile_id
        )

    profile_result = await db.execute(profile_stmt)
    profile_data = profile_result.one_or_none()

    if profile_data:
        is_approved, ref_number, industry = profile_data
    else:
        is_approved, ref_number, industry = False, "", ""

    user_info = AdminUserInfo(
            is_approved=is_approved,
            ref_number=ref_number,
            industry=industry,
        )



    # Create JWT token
    token_data = {
        "userId": user.user_id,
        "bprofileId": user.business_profile_id,
    }

    access_token = create_access_token(data=token_data)

    return AdminLoginResponse(
        access_token=access_token,
        user=user_info,
        message="Login successful"
    )


@router.post("/check-store-name-availability", response_model=StoreNameCheckResponse)
async def check_store_name_availability(
    request: StoreNameCheckRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Check if store name is available for use.
    """
    # Query BusinessProfile table to check if store name already exists
    stmt = select(BusinessProfile).where(
        BusinessProfile.store_name == request.store_name.strip()
    )
    result = await db.execute(stmt)
    existing_store = result.scalar_one_or_none()
    
    if existing_store:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "status_code": status.HTTP_409_CONFLICT,
                "message": "Store name not available"
            }
        )
    
    return StoreNameCheckResponse(
        status_code=status.HTTP_200_OK,
        message="Store name available"
    )

