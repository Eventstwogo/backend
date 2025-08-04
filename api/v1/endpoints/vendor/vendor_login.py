from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from passlib.context import CryptContext

from utils.id_generators import hash_data
from db.models.superadmin import BusinessProfile, VendorLogin, VendorSignup
from schemas.admin_user import AdminLoginRequest, AdminLoginResponse, AdminUserInfo
from db.sessions.database import get_db
from utils.jwt import create_access_token
from schemas.vendor_onboarding import StoreNameCheckRequest, StoreNameCheckResponse

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
router = APIRouter()



MAX_LOGIN_ATTEMPTS = 5


@router.post("/login", response_model=AdminLoginResponse)
async def login_user(
    login_data: AdminLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    email_hash = hash_data(login_data.email)

    # Step 1: Check VendorSignup table
    signup_stmt = select(VendorSignup).where(VendorSignup.email_hash == email_hash)
    signup_result = await db.execute(signup_stmt)
    signup_user = signup_result.scalar_one_or_none()

    if signup_user and not signup_user.email_flag:
        raise HTTPException(
            status_code=401,
            detail="Please verify your email address before logging in."
        )

    # Step 2: VendorLogin lookup
    stmt = select(VendorLogin).where(VendorLogin.email_hash == email_hash)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        if signup_user:
            if not signup_user.email_flag:
                raise HTTPException(
                    status_code=401,
                    detail="Please verify your email first before logging in."
                )
            else:
                raise HTTPException(
                    status_code=422,
                    detail="Account verification incomplete. Please contact support."
                )
        else:
            raise HTTPException(
                status_code=404,
                detail="Account not found. Please register first."
            )

    # Step 3: Account lock
    if user.login_status == 1:
        raise HTTPException(
            status_code=423,
            detail="Account is locked. Try again after 24 hours."
        )

    # Step 4: Password check
    if not pwd_context.verify(login_data.password, user.password):
        user.login_failed_attempts += 1
        if user.login_failed_attempts >= MAX_LOGIN_ATTEMPTS:
            user.login_status = 1
            user.locked_time = datetime.utcnow()
        db.add(user)
        await db.commit()
        remaining = MAX_LOGIN_ATTEMPTS - user.login_failed_attempts
        raise HTTPException(
            status_code=401,
            detail=f"Incorrect password. {remaining} attempts remaining before account lock."
        )

    # Step 5: Inactive check
    if user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Your account is inactive. Please contact support."
        )

    # Step 6: Business profile
    profile_stmt = select(
        BusinessProfile.is_approved,
        BusinessProfile.ref_number,
        BusinessProfile.industry, 
        BusinessProfile.store_slug,
        BusinessProfile.reviewer_comment,
    ).where(BusinessProfile.profile_ref_id == user.business_profile_id)
    profile_result = await db.execute(profile_stmt)
    profile_data = profile_result.one_or_none()

    is_approved, ref_number, industry, store_slug, reviewer_comment = profile_data if profile_data else (-2, "", "", "")


    # Step 7: Determine onboarding_status
    if user.is_verified and is_approved == 2:
        onboarding_status = "approved"
    elif not user.is_verified and is_approved == -2:
        onboarding_status = "not_started"
    elif not user.is_verified and is_approved == -1 and ref_number:
        onboarding_status = "rejected"
    elif not user.is_verified and is_approved == 1 and ref_number:
        onboarding_status = "under_review"    
    elif not user.is_verified and is_approved == 0 and ref_number:
        onboarding_status = "submitted"
    else:
        onboarding_status = "unknown"

    # Step 8: Successful login
    user.login_attempts += 1
    user.login_failed_attempts = 0
    user.last_login = datetime.utcnow()
    user.login_status = 0

    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Step 9: Prepare response
    user_info = AdminUserInfo(
        is_approved=is_approved,
        ref_number=ref_number,
        industry=industry,
        vendor_store_slug= store_slug,
        onboarding_status=onboarding_status,
        reviewer_comment= reviewer_comment
    )

    token_data = {
        "userId": user.user_id,
       
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

