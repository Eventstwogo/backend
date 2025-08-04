"""
User password management endpoints.
"""

from fastapi import APIRouter, Depends, status, Form, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from core.api_response import api_response
from core.config import settings
from db.sessions.database import get_db
from schemas.register import (
    UserForgotPasswordRequest,
    UserForgotPasswordResponse,
    UserResetPasswordRequest,
    UserResetPasswordResponse,
)
from services.user_password_reset import (
    get_user_by_email,
    generate_password_reset_token,
    create_password_reset_record,
    validate_reset_token,
    mark_password_reset_used,
    user_not_found_response,
    account_inactive,
    account_not_verified,
)
from utils.auth import hash_password, verify_password
from utils.email import send_user_password_reset_email
from utils.email_validators import EmailValidator
from utils.exception_handlers import exception_handler
from utils.id_generators import decrypt_data
from utils.validations import validate_password

router = APIRouter()


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
@exception_handler
async def forgot_password(
    request: Request,
    email: str = Form(...),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Send a password reset link to the user's email if the account exists and is active."""
    # Get the client's IP address
    client_host = request.client.host if request.client else "unknown"

    # Or check headers (especially if behind a reverse proxy/load balancer)
    x_forwarded_for = request.headers.get("x-forwarded-for")
    if x_forwarded_for:
        ip_address = x_forwarded_for.split(",")[0].strip()
    else:
        ip_address = client_host

    # Log or use the IP address
    print(f"User password reset requested by user with IP: {ip_address}")

    # Step 1: Validate email format and normalize
    email = email.strip().lower()
    EmailValidator.validate(email)

    # Step 2: Check if user exists
    user = await get_user_by_email(db, email)
    if not user:
        return user_not_found_response()

    # Step 3: Check if user account is active (False = active, True = inactive)
    if user.is_active:  # True means account is inactive
        return account_inactive()
    
    # Step 4: Check if user is verified (login_status: -1 = unverified, 0 = normal, 1 = locked)
    if user.login_status == -1:
        return account_not_verified()

    # Step 5: Generate a secure 32-character reset token with 1 hour expiration
    reset_token, expires_at = generate_password_reset_token(
        expires_in_minutes=60
    )

    # Step 6: Save the token to the database
    await create_password_reset_record(
        db=db,
        user_id=user.user_id,
        token=reset_token,
        expires_at=expires_at,
    )

    # Step 7: Create the reset link
    reset_link = f"{settings.FRONTEND_URL}/reset-password/{reset_token}?email={email}"

    # Step 8: Send the password reset email
    # Use the plain text email from the form input and decrypt the username
    decrypted_username = decrypt_data(user.username)
    
    send_user_password_reset_email(
        email=email,  # Use plain text email from form
        username=decrypted_username,  # Decrypt the username
        reset_link=reset_link,
        expiry_minutes=60,  # 1 hour expiry
        ip_address=ip_address,
        request_time=datetime.now(timezone.utc).isoformat(),
    )

    # Return success message (don't include token in response for security)
    return api_response(
        status_code=status.HTTP_200_OK,
        message="Password reset link sent to registered email address.",
    )


@router.post("/reset-password/token", status_code=status.HTTP_200_OK)
@exception_handler
async def reset_password_with_token(
    email: str = Form(...),
    token: str = Form(...),
    new_password: str = Form(...),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Reset password using the token received via email"""
    # Step 1: Validate the reset token
    is_valid, error_message, user = await validate_reset_token(
        db=db, token=token, email=email
    )

    if not is_valid or user is None:
        # Determine appropriate status code based on error message
        if "not found" in error_message.lower():
            status_code = status.HTTP_404_NOT_FOUND
        elif "inactive" in error_message.lower() or "not verified" in error_message.lower():
            status_code = status.HTTP_403_FORBIDDEN
        elif "expired" in error_message.lower():
            status_code = status.HTTP_410_GONE
        else:
            status_code = status.HTTP_400_BAD_REQUEST
            
        return api_response(
            status_code=status_code,
            message=error_message or "Invalid or expired reset token.",
        )

    # Step 2: Validate new password format
    validation_result = validate_password(new_password)
    if validation_result["status_code"] != 200:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=validation_result["message"],
        )

    # Step 3: Prevent using the same password as current password
    if verify_password(new_password, user.password_hash):
        return api_response(
            status_code=status.HTTP_409_CONFLICT,
            message="New password cannot be the same as old password.",
        )

    # Step 4: Update the password
    user.password_hash = hash_password(new_password)
    user.login_status = 0  # Normal login status (reset if locked)
    user.failed_logins = 0  # Reset failed login attempts
    user.account_locked_at = None  # Clear lock timestamp if any

    # Step 5: Mark the reset token as used
    await mark_password_reset_used(db=db, user_id=user.user_id)

    await db.commit()
    await db.refresh(user)

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Password has been reset successfully.",
    )


@router.post("/change-password", status_code=status.HTTP_200_OK)
@exception_handler
async def change_password(
    user_id: str = Form(...),
    current_password: str = Form(...),
    new_password: str = Form(...),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Change password for an authenticated user (requires current password)"""
    
    # Step 1: Get user by user_id
    from sqlalchemy import select
    from db.models.superadmin import User
    
    user_result = await db.execute(
        select(User).where(User.user_id == user_id)
    )
    user = user_result.scalar_one_or_none()
    
    if not user:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found.",
            log_error=True,
        )
    
    # Step 2: Check if user account is active (False = active, True = inactive)
    if user.is_active:
        return api_response(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Account is inactive. Cannot change password.",
            log_error=True,
        )
    
    # Step 3: Check if user is verified
    if user.login_status == -1:
        return api_response(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Account is not verified. Please verify your email address first.",
            log_error=True,
        )
    
    # Step 4: Verify current password
    if not verify_password(current_password, user.password_hash):
        return api_response(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message="Current password is incorrect.",
            log_error=True,
        )
    
    # Step 5: Validate new password format
    validation_result = validate_password(new_password)
    if validation_result["status_code"] != 200:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=validation_result["message"],
        )
    
    # Step 6: Prevent using the same password
    if verify_password(new_password, user.password_hash):
        return api_response(
            status_code=status.HTTP_409_CONFLICT,
            message="New password cannot be the same as current password.",
        )
    
    # Step 7: Update the password
    user.password_hash = hash_password(new_password)
    user.failed_logins = 0  # Reset failed login attempts
    user.account_locked_at = None  # Clear lock timestamp if any
    
    await db.commit()
    await db.refresh(user)
    
    return api_response(
        status_code=status.HTTP_200_OK,
        message="Password has been changed successfully.",
    )