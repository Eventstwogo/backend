
from datetime import datetime
from sqlalchemy import select
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse
from passlib.context import CryptContext
from urllib.parse import quote

from core.api_response import api_response
from core.config import settings
from db.models.superadmin import Config, VendorLogin
from db.models.superadmin import VendorSignup
from db.sessions.database import get_db
from schemas.register import (
    VendorLoginResponse,
    VendorRegisterRequest,
    VendorRegisterResponse,
)

from services.admin_user import get_config_or_404
from services.vendor_user import validate_unique_user
from utils.email_utils import send_vendor_verification_email
from utils.file_uploads import (
    get_media_url,
)
from utils.id_generators import decrypt_data, encrypt_data, generate_lower_uppercase, hash_data, random_token

router = APIRouter()


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


@router.post(
    "/register",
    response_model=VendorRegisterResponse,
    status_code=status.HTTP_201_CREATED,
)

async def register_user(
    background_tasks: BackgroundTasks,
    user_data: VendorRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:

   
    encrypted_email = encrypt_data(user_data.email)


    email_hash = hash_data(user_data.email)

    # Check uniqueness using hashes
    unique_user_result = await validate_unique_user(db, email_hash)
    if unique_user_result is not None:
        return unique_user_result

    # Get system configuration
    config_result = await get_config_or_404(db)
    if not isinstance(config_result, Config):
        return config_result

    config = config_result

    signup_id = generate_lower_uppercase(length=6)
    email_token = random_token()
    hashed_password = hash_password(user_data.password)

    new_user = VendorSignup(
        signup_id=signup_id,
        password=hashed_password,
        email=encrypted_email,
        email_hash=email_hash,
        email_token=email_token,
        email_token_timestamp=datetime.utcnow(),
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # Send vendor verification email instead of welcome email
    background_tasks.add_task(
        send_vendor_verification_email,
        email=user_data.email,
        business_name="Your Business",  # You can modify this based on your vendor data
        verification_token=email_token,
        expires_in_minutes=30
    )

    return api_response(
        status_code=status.HTTP_201_CREATED,
        message="Vendor registered successfully. Verification email sent in background.",
        data=VendorRegisterResponse(
            signup_id=signup_id,
            email=user_data.email,
           
        ),
    )


@router.get(
    "/vendors",
    response_model=list[VendorRegisterResponse],
    status_code=status.HTTP_200_OK,
)
async def get_all_vendors(
    db: AsyncSession = Depends(get_db),
    
) -> JSONResponse:
    # Fetch vendors with pagination
    result = await db.execute(
        select(VendorSignup)
    )
    vendors = result.scalars().all()

    if not vendors:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No vendors found",
        )

    # Prepare response with decrypted emails
    vendor_list = [
        VendorRegisterResponse(
            signup_id=v.signup_id,
            email=decrypt_data(v.email),
        )
        for v in vendors
    ]

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Vendors retrieved successfully",
        data=vendor_list,
    )




@router.get(
    "/vendor-logins",
    response_model=list[VendorLoginResponse],
    status_code=status.HTTP_200_OK,
)
async def get_all_vendor_logins(
    db: AsyncSession = Depends(get_db),
   
) -> JSONResponse:
    # Fetch logins with pagination
    result = await db.execute(
        select(VendorLogin)
    )
    logins = result.scalars().all()

    if not logins:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No vendor logins found",
        )

    # Prepare safe response
    login_list = [
        VendorLoginResponse(
            user_id=l.user_id,
            username=l.username,
            email=decrypt_data(l.email),   # decrypt email if encrypted
            is_verified=l.is_verified,
            role=l.role,
            is_active=l.is_active,
            last_login=l.last_login,
        )
        for l in logins
    ]

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Vendor logins retrieved successfully",
        data=login_list,
    )