from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from passlib.context import CryptContext

from utils.id_generators import hash_data
from db.models.superadmin import BusinessProfile, VendorLogin, Config
from schemas.admin_user import AdminLoginRequest, AdminLoginResponse, AdminUserInfo
from db.sessions.database import get_db
from utils.jwt import create_access_token

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
router = APIRouter()



MAX_LOGIN_ATTEMPTS = 5

@router.post("/login", response_model=AdminLoginResponse)
async def login_user(
    login_data: AdminLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    
    email_hash = hash_data(login_data.email)
    # Find user by username or email
    stmt = select(VendorLogin).where(
        VendorLogin.email_hash == email_hash
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if user.is_verified:
       raise HTTPException(status_code=402, detail="Your business profile is under verification, check again later.")

    if user.login_attempts >= MAX_LOGIN_ATTEMPTS:
        raise HTTPException(status_code=403, detail="Account locked due to too many failed login attempts.")

    # Compare password
    if not pwd_context.verify(login_data.password, user.password):
        user.login_attempts += 1
        await db.commit()
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if user.is_active:
        raise HTTPException(status_code=403, detail="Account is not active")

    # Get default password from config to compare
    config_stmt = select(Config)
    config_result = await db.execute(config_stmt)
    config = config_result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=500, detail="System configuration missing.")

    # Determine login status based on default password
    using_default_password = pwd_context.verify(login_data.password, config.default_password_hash)
    user.login_status = -1 if using_default_password else 1

    # Reset attempts, update login time
    user.login_attempts = 0
    user.last_login = datetime.utcnow()
    await db.commit()

    profile_stmt = select(
    BusinessProfile.is_approved,
    BusinessProfile.ref_number
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

