from sqlalchemy import select
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from db.models.superadmin import VendorLogin, VendorSignup, Role
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

        # Check if user already exists in VendorLogin
        login_check = await db.execute(
            select(VendorLogin).where(VendorLogin.email_hash == email_hash)
        )
        existing_login = login_check.scalar_one_or_none()
        
        if existing_login:
            return {"message": "User already exists in login table"}

        user_id = generate_digits_letters(length=6)
        business_profile_id = generate_digits_lowercase(length=6)
        user_profile_id = generate_digits_uppercase(length=6)
        
        # Fetch "SUPERADMIN" role_id for new vendor
        role_stmt = select(Role).where(Role.role_name == "SUPERADMIN")
        role_result = await db.execute(role_stmt)
        super_admin_role = role_result.scalar_one_or_none()
        
        if super_admin_role:
            role_id = super_admin_role.role_id
            print(f"Found SUPERADMIN role with ID: {role_id}")
        else:
            role_id = None
            print("SUPERADMIN role not found in database")
            # Let's check what roles exist
            all_roles_stmt = select(Role)
            all_roles_result = await db.execute(all_roles_stmt)
            all_roles = all_roles_result.scalars().all()
            print(f"Available roles: {[role.role_name for role in all_roles]}")

        username = "unknown"
        username_hash = hash_data(username)
        
        new_user_login = VendorLogin(
            user_id=user_id,
            username=username,
            username_hash=username_hash,
            email=encrypted_email,
            email_hash=existing_user.email_hash,
            password=existing_user.password,
            business_profile_id=business_profile_id,
            user_profile_id=user_profile_id,
            role=role_id,
        )

        db.add(new_user_login)
        await db.commit()
        return {"message": "Data copied successfully"}

    except Exception as e:
        await db.rollback()
        print(f"Error in copy_data: {str(e)}")  # Add logging
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


@router.post(
    "/fix-account",
    status_code=status.HTTP_200_OK,
)
@exception_handler
async def fix_stuck_account(
    email: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Utility endpoint to fix accounts stuck between signup and login tables.
    Use this if a user completed email verification but can't log in.
    """
    
    email_hash = hash_data(email)
    
    # Check signup table
    signup_result = await db.execute(
        select(VendorSignup).where(VendorSignup.email_hash == email_hash)
    )
    signup_user = signup_result.scalar_one_or_none()
    
    if not signup_user:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found in signup table.",
        )
    
    if not signup_user.email_flag:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Email not verified yet. Please verify email first.",
        )
    
    # Check if already exists in login table
    login_result = await db.execute(
        select(VendorLogin).where(VendorLogin.email_hash == email_hash)
    )
    login_user = login_result.scalar_one_or_none()
    
    if login_user:
        return api_response(
            status_code=status.HTTP_200_OK,
            message="Account already exists in login table. Login should work.",
        )
    
    # Copy from signup to login
    copy_result = await copy_data(db, email, signup_user.email)
    
    return api_response(
        status_code=status.HTTP_200_OK,
        message="Account successfully moved to login table. You can now log in.",
        data=copy_result
    )
