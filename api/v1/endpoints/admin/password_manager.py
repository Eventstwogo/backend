from fastapi import APIRouter, Depends, HTTPException, Query, Request, status, Form
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from passlib.context import CryptContext

from utils.auth import hash_password, verify_password
from utils.validations import validate_password
from services.email_service import email_service
from utils.email_validators import EmailValidator
from utils.exception_handlers import exception_handler
from core.status_codes import APIResponse, StatusCode
from core.api_response import api_response
from core.config import settings
from db.models.superadmin import AdminUser
from schemas.admin_user import (
    AdminResetPassword, 
    UpdatePasswordBody, 
    UpdatePasswordResponse,
    ForgotPassword,
    ResetPasswordWithToken,
    ChangeInitialPasswordRequest,
    ChangeInitialPasswordResponse
)
from db.sessions.database import get_db
from services.password_reset import (
    get_user_by_email,
    generate_password_reset_token,
    create_password_reset_record,
    validate_reset_token,
    mark_password_reset_used,
    user_not_found_response,
    account_deactivated,
    account_not_found
)
from utils.id_generators import decrypt_data

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.post("/update-password", response_model=UpdatePasswordResponse)
async def update_password(
    user_id: str = Query(..., description="User ID"),
    body: UpdatePasswordBody = Depends(),
    db: AsyncSession = Depends(get_db),
)-> JSONResponse:
    # Fetch user by user_id
    stmt = select(AdminUser).where(AdminUser.user_id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    # Verify old password
    if not pwd_context.verify(body.old_password, user.password):
        raise HTTPException(status_code=401, detail="Old password is incorrect.")

    # Validate new password format
    validation_result = validate_password(body.new_password)
    if validation_result["status_code"] != 200:
        raise HTTPException(status_code=400, detail=validation_result["message"])

    # Check if new password is same as old password
    if pwd_context.verify(body.new_password, user.password):
        raise HTTPException(status_code=400, detail="New password cannot be the same as the old password.")

    # Hash and update password
    user.password = pwd_context.hash(body.new_password)
    user.login_status = 0
    user.login_attempts = 0
    user.updated_at = datetime.utcnow()
    user.days_180_timestamp = datetime.utcnow() 

    await db.commit()

    return UpdatePasswordResponse(message="Password updated successfully.")




# @router.put("/api/v1/forgot-password/")
# async def forgot_password(
#     email_token: str,
#     data: AdminResetPassword,
#     db: AsyncSession = Depends(get_db),
# )-> JSONResponse:
#     try:
#         new_password = data.new_password.strip()
#         confirm_new_password = data.confirm_new_password.strip()

#         if new_password != confirm_new_password:
#             return APIResponse.response(StatusCode.BAD_REQUEST, "Passwords do not match")

#         result = await db.execute(
#             select(AdminUser).where(AdminUser.email_hash == email_token)
#         )
#         user = result.scalar_one_or_none()

#         if not user:
#             return APIResponse.response(StatusCode.NOT_FOUND, "Invalid or expired token")

#         validate_password(new_password, user.days_180_flag)

#         hashed_password = hash_password(new_password)
#         user.password = hashed_password
#         user.updated_at = datetime.now(timezone.utc)
#         user.email_hash = None  # Clear token after use

#         await db.commit()

#         return APIResponse.response(StatusCode.SUCCESS, "Password reset successful")

#     except Exception as e:
#         return APIResponse.response(
#             StatusCode.SERVER_ERROR, f"Internal server error: {str(e)}", log_error=True
#         )




# @router.put("/api/v1/change-password/")
# async def change_password(
#     user_id: str,
#     data: AdminResetPassword,
#     db: AsyncSession = Depends(get_db),
# ):
#     try:
#         new_password = data.new_password.strip()
#         confirm_new_password = data.confirm_new_password.strip()

#         if new_password != confirm_new_password:
#             return APIResponse.response(StatusCode.BAD_REQUEST, "Passwords do not match")

#         result = await db.execute(
#             select(AdminUser).where(AdminUser.user_id == user_id)
#         )
#         user = result.scalar_one_or_none()

#         if not user:
#             return APIResponse.response(StatusCode.NOT_FOUND, "Invalid user")

#         validate_password(new_password, user.days_180_flag)

#         hashed_password = hash_password(new_password)
#         user.password = hashed_password
#         user.updated_at = datetime.now(timezone.utc)

#         await db.commit()

#         return APIResponse.response(StatusCode.SUCCESS, "Password updated successfully")

#     except Exception as e:
#         return APIResponse.response(
#             StatusCode.SERVER_ERROR, f"Internal server error: {str(e)}", log_error=True
#         )


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
    print(f"Password reset requested by user with IP: {ip_address}")

    # Step 1: Validate email format and normalize
    email = email.strip().lower()
    EmailValidator.validate(email)

    # Step 2: Check if user exists
    user = await get_user_by_email(db, email)
    if not user:
        return user_not_found_response()

    # Step 3: Check if user is active (False = active, True = deactivated)
    if user.is_active:  # True means account is deactivated
        return account_deactivated()

    # Step 4: Generate a secure 32-character reset token with 1 hour expiration
    reset_token, expires_at = generate_password_reset_token(
        expires_in_minutes=60
    )

    # Step 5: Save the token to the database
    await create_password_reset_record(
        db=db,
        user_id=user.user_id,
        token=reset_token,
        expires_at=expires_at,
    )

    # Step 6: Create the reset link
    reset_link = f"{settings.FRONTEND_URL}/reset-password?email={email}&token={reset_token}"

    # Step 7: Send the password reset email
    # Use the plain text email from the form input and decrypt the username
    decrypted_username = decrypt_data(user.username)
    
    email_service.send_password_reset_email(
        email=email,  # Use plain text email from form
        username=decrypted_username,  # Decrypt the username
        reset_link=reset_link,
        expiry_minutes=60,  # 1 hour expiry
        ip_address=ip_address,
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
        elif "deactivated" in error_message.lower():
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

    # Step 3: Prevent using the same password
    if verify_password(new_password, user.password):
        return api_response(
            status_code=status.HTTP_409_CONFLICT,
            message="New password cannot be the same as old password.",
        )

    # Step 4: Update the password
    user.password = hash_password(new_password)
    user.login_status = 0  # Normal login status
    user.login_attempts = 0  # Reset login attempts

    # Step 5: Mark the reset token as used
    await mark_password_reset_used(db=db, user_id=user.user_id)

    await db.commit()
    await db.refresh(user)

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Password has been reset successfully.",
    )


@router.post("/change-initial-password", response_model=ChangeInitialPasswordResponse)
@exception_handler
async def change_initial_password(
    password_data: ChangeInitialPasswordRequest,
    email: str = Query(..., description="User email address"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Change initial password for a user by email"""
    
    # Normalize email
    email = email.strip().lower()
    
    # Step 1: Check if user exists
    user = await get_user_by_email(db, email)
    if not user:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="User with this email address not found.",
        )
    
    # Step 2: Check if user account is active (False = active, True = deactivated)
    if user.is_active:  # True means account is deactivated
        return api_response(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Account is deactivated. Cannot change password.",
        )
    
    # Step 3: Validate new password format
    validation_result = validate_password(password_data.new_password)
    if validation_result["status_code"] != 200:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=validation_result["message"],
        )
    
    # Step 4: Prevent using the same password as current password
    if verify_password(password_data.new_password, user.password):
        return api_response(
            status_code=status.HTTP_409_CONFLICT,
            message="New password cannot be the same as current password.",
        )
    
    # Step 5: Update the password
    user.password = hash_password(password_data.new_password)
    user.login_status = 0  # Normal login status
    user.login_attempts = 0  # Reset login attempts
    user.updated_at = datetime.now(timezone.utc)
    user.days_180_timestamp = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(user)
    
    return api_response(
        status_code=status.HTTP_200_OK,
        message="Initial password has been changed successfully.",
    )