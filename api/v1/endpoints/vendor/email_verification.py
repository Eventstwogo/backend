from sqlalchemy import select
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from db.models.superadmin import VendorLogin, VendorSignup
from utils.id_generators import  hash_data, generate_digits_letters, generate_digits_lowercase, generate_digits_uppercase
from utils.exception_handlers import exception_handler
from fastapi import APIRouter, Depends, status
from db.sessions.database import get_db
from core.api_response import api_response

router = APIRouter()

async def copy_data(db: AsyncSession, user_email: str, encrypted_email: str):
    try:
        email_hash = hash_data(user_email)

        result = await db.execute(
            select(VendorSignup).where(VendorSignup.email_hash == email_hash)
        )
        existing_user = result.scalar_one_or_none()

        if not existing_user:
            return {"message": "User not found with the provided email"}

        user_id = generate_digits_letters(length=6)
        business_profile_id = generate_digits_lowercase(length=6)
        user_profile_id = generate_digits_uppercase(length=6)

        new_user_login = VendorLogin(
            user_id=user_id,
            email=encrypted_email,
            email_hash=existing_user.email_hash,
            password=existing_user.password,
            business_profile_id=business_profile_id,
            user_profile_id=user_profile_id,
        )

        db.add(new_user_login)
        await db.commit()
        return {"message": "Data copied successfully"}

    except Exception as e:
        await db.rollback()
        raise


@router.post(
    "/verify-email",
    status_code=status.HTTP_200_OK,
)
@exception_handler
async def verify_email(
    email: str,
    token: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:

    # Hash the email for lookup
    email_hash = hash_data(email)

    # Look up the user by email hash
    result = await db.execute(
        select(VendorSignup).where(VendorSignup.email_hash == email_hash)
    )
    user = result.scalar_one_or_none()

    if not user:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found.",
            log_error= True
        )

    if user.email_flag:
        return api_response(
            status_code=status.HTTP_200_OK,
            message="Email already verified.",
        )

    if user.email_token != token:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Invalid verification token.",
            log_error= True
        )

    # Mark email as verified
    user.email_flag = True
    await db.commit()
    await db.refresh(user)

    # Use original email and encrypted version for downstream logic
    encrypted_email = user.email
    await copy_data(db, email, encrypted_email)

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Email verified and user login created.",
        
    )
