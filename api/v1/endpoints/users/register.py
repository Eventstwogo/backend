"""
User registration endpoint.
"""

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from urllib.parse import unquote

from core.api_response import api_response
from db.models.general import User, UserVerification
from db.sessions.database import get_db
from schemas.register import UserRegisterRequest, UserRegisterResponse, UserVerificationRequest, UserVerificationResponse, ResendVerificationRequest, ResendVerificationResponse
from services.admin_user import get_config_or_404
from utils.email_utils import send_user_verification_email
from services.user_service import validate_unique_user, generate_verification_tokens
from utils.auth import hash_password
from utils.exception_handlers import exception_handler
from utils.id_generators import generate_lower_uppercase, encrypt_data, hash_data, decrypt_data
from datetime import datetime, timezone
from sqlalchemy import select

router = APIRouter()


@router.post(
    "/register",
    response_model=UserRegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
@exception_handler
async def register_user(
    background_tasks: BackgroundTasks,
    user_data: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:

    # Hash data for uniqueness checks
    username_hash = hash_data(user_data.username.lower())
    email_hash = hash_data(user_data.email.lower())
    phone_number_hash = hash_data(user_data.phone_number) if user_data.phone_number else None
    
    # Check if user already exists (username, email, or phone)
    unique_user_result = await validate_unique_user(db, username_hash, email_hash, phone_number_hash)
    if unique_user_result is not None:
        return unique_user_result

    # Validate first name and last name are not the same
    if (
        user_data.first_name.strip().lower()
        == user_data.last_name.strip().lower()
    ):
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="First name and last name cannot be the same.",
            log_error=True,
        )

    # Create new user
    user_id = generate_lower_uppercase(length=6)

    # Encrypt sensitive data for retrieval
    username_encrypted = encrypt_data(user_data.username.lower())
    first_name_encrypted = encrypt_data(user_data.first_name.title())
    last_name_encrypted = encrypt_data(user_data.last_name.title())
    email_encrypted = encrypt_data(user_data.email.lower())
    phone_encrypted = encrypt_data(user_data.phone_number) if user_data.phone_number else None
    
    # Hash the password
    password_hash = hash_password(user_data.password)

    # Get system configuration
    config = await get_config_or_404(db)
    if not config:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="System configuration not found.",
            log_error=True,
        )

    # Create new user with all required fields
    new_user = User(
        user_id=user_id,
        # Encrypted data for retrieval
        username=username_encrypted,
        first_name=first_name_encrypted,
        last_name=last_name_encrypted,
        email=email_encrypted,
        phone_number=phone_encrypted,
        # Hashed data for uniqueness checks
        username_hash=username_hash,
        email_hash=email_hash,
        phone_number_hash=phone_number_hash,
        password_hash=password_hash,
        login_status=-1,  # -1 = unverified, 0 = active, 1 = locked
        successful_logins=0,
        failed_logins=0,
        days_180_flag=config.global_180_day_flag,
        is_active=False,  # false = active, true = inactive
    )

    # Create verification record with expiration time
    verification_token, expiration_time = generate_verification_tokens(
        expires_in_minutes=60
    )
    
    # Debug: Print generated token details
    print(f"DEBUG - Generated token: '{verification_token}'")
    print(f"DEBUG - Generated token length: {len(verification_token)}")
    print(f"DEBUG - Generated token type: {type(verification_token)}")
    
    verification = UserVerification(
        user_id=user_id,
        email_verification_token=verification_token,
        email_token_expires_at=expiration_time,
        email_verified=False,
        phone_verified=False,
    )

    # Add to database
    db.add(new_user)
    db.add(verification)
    await db.commit()
    await db.refresh(new_user)

    # Send welcome email with verification link in background
    try:
        background_tasks.add_task(
            send_user_verification_email,
            email=user_data.email,
            username=user_data.username,  # Use username for email
            verification_token=verification_token,
            user_id=user_id,
            expires_in_minutes=60,  # Set expiration to 60 minutes
        )
        print(f"Email task added for user: {user_data.email}")
    except Exception as e:
        print(f"Error adding email task: {str(e)}")
        # Don't fail registration if email fails

    # Return success response
    return api_response(
        status_code=status.HTTP_201_CREATED,
        message="User registered successfully. Verification email sent to your email address.",
        data=UserRegisterResponse(
            user_id=user_id,
            email=user_data.email,
        ),
    )


@router.post(
    "/verify-email",
    response_model=UserVerificationResponse,
    status_code=status.HTTP_200_OK,
)
@exception_handler
async def verify_user_email(
    token: str = Query(..., description="Email verification token"),
    email: str = Query(..., description="User's email address"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Verify user email address using verification token.
    Changes login_status from -1 (unverified) to 0 (active).
    """
    
    # URL decode the token in case it was encoded
    decoded_token = unquote(token)
    
    # Debug: Print email details
    print(f"DEBUG - Received email: '{email}'")
    print(f"DEBUG - Email length: {len(email)}")
    
    # Hash email for lookup
    email_hash = hash_data(email.lower())
    
    # Find user by email hash
    user_result = await db.execute(
        select(User).where(User.email_hash == email_hash)
    )
    user = user_result.scalar_one_or_none()
    
    if not user:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found.",
            log_error=True,
        )
    
    # Check if user is already verified
    if user.login_status == 0:
        return api_response(
            status_code=status.HTTP_200_OK,
            message="Email already verified.",
            data=UserVerificationResponse(
                user_id=user.user_id,
            ),
        )
    
    # Find verification record
    verification_result = await db.execute(
        select(UserVerification).where(UserVerification.user_id == user.user_id)
    )
    verification = verification_result.scalar_one_or_none()
    
    if not verification:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Verification record not found.",
            log_error=True,
        )
    
    # Check if email is already verified
    if verification.email_verified:
        return api_response(
            status_code=status.HTTP_200_OK,
            message="Email already verified.",
            data=UserVerificationResponse(
                user_id=user.user_id,
            ),
        )
    
    # Debug: Print token comparison details
    print(f"DEBUG - Original token: '{token}'")
    print(f"DEBUG - Decoded token: '{decoded_token}'")
    print(f"DEBUG - Decoded token length: {len(decoded_token)}")
    print(f"DEBUG - Stored token: '{verification.email_verification_token}'")
    print(f"DEBUG - Stored token length: {len(verification.email_verification_token) if verification.email_verification_token else 0}")
    print(f"DEBUG - Tokens equal (original): {verification.email_verification_token == token}")
    print(f"DEBUG - Tokens equal (decoded): {verification.email_verification_token == decoded_token}")
    print(f"DEBUG - Tokens equal (stripped): {verification.email_verification_token.strip() == decoded_token.strip() if verification.email_verification_token else False}")
    
    # Check if token matches (use decoded token)
    if verification.email_verification_token != decoded_token:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Invalid verification token.",
            log_error=True,
        )
    
    # Check if token has expired
    if verification.email_token_expires_at and verification.email_token_expires_at < datetime.now(timezone.utc):
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Verification token has expired.",
            log_error=True,
        )
    
    # Mark email as verified and activate user
    verification.email_verified = True
    user.login_status = 0  # Change from -1 (unverified) to 0 (active)
    
    # Save changes
    db.add(verification)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    await db.refresh(verification)
    
    return api_response(
        status_code=status.HTTP_200_OK,
        message="Email verified successfully. You can now log in.",
        data=UserVerificationResponse(
            user_id=user.user_id,
        ),
    )


@router.post(
    "/resend-verification",
    response_model=ResendVerificationResponse,
    status_code=status.HTTP_200_OK,
)
@exception_handler
async def resend_verification_email(
    background_tasks: BackgroundTasks,
    request_data: ResendVerificationRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Resend verification email to user who hasn't verified their account yet.
    """
    
    # Hash email for lookup
    email_hash = hash_data(request_data.email.lower())
    
    # Find user by email hash
    user_result = await db.execute(
        select(User).where(User.email_hash == email_hash)
    )
    user = user_result.scalar_one_or_none()
    
    if not user:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found with this email address.",
            log_error=True,
        )
    
    # Check if user is already verified
    if user.login_status == 0:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="This email address is already verified.",
            log_error=False,
        )
    
    # Check if user is not in an unverified state (login_status should be -1)
    if user.login_status != -1:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="User account is not in a state that requires email verification.",
            log_error=False,
        )
    
    # Find verification record
    verification_result = await db.execute(
        select(UserVerification).where(UserVerification.user_id == user.user_id)
    )
    verification = verification_result.scalar_one_or_none()
    
    if not verification:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Verification record not found. Please contact support.",
            log_error=True,
        )
    
    # Check if email is already verified in verification record
    if verification.email_verified:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="This email address is already verified.",
            log_error=False,
        )
    
    # Generate new verification token and expiration time
    new_verification_token, new_expiration_time = generate_verification_tokens(
        expires_in_minutes=60
    )
    
    # Update verification record with new token and expiration
    verification.email_verification_token = new_verification_token
    verification.email_token_expires_at = new_expiration_time
    
    # Save changes
    db.add(verification)
    await db.commit()
    await db.refresh(verification)
    
    # Decrypt username for email (we need the original username for the email)
    username_decrypted = decrypt_data(user.username)
    
    # Send verification email in background
    try:
        background_tasks.add_task(
            send_user_verification_email,
            email=request_data.email,
            username=username_decrypted,
            verification_token=new_verification_token,
            user_id=user.user_id,
            expires_in_minutes=60,
        )
        print(f"Resend verification email task added for user: {request_data.email}")
    except Exception as e:
        print(f"Error adding resend verification email task: {str(e)}")
        # Don't fail the request if email fails, but log the error
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to send verification email. Please try again later.",
            log_error=True,
        )
    
    return api_response(
        status_code=status.HTTP_200_OK,
        message="Verification email resent successfully.",
        data=ResendVerificationResponse(
            email=request_data.email,
        ),
    )
