import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from fastapi import status
from fastapi.responses import JSONResponse
from utils.id_generators import hash_data
from db.models.superadmin import AdminUser, PasswordReset
from utils.auth import verify_password


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[AdminUser]:
    """Get user by email address."""
    
    # Hash the email for lookup since emails are stored encrypted
    # and email_hash is used for searches
    email_hash = hash_data(email.lower().strip())
    stmt = select(AdminUser).where(AdminUser.email_hash == email_hash)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


def generate_password_reset_token(expires_in_minutes: int = 60) -> Tuple[str, datetime]:
    """Generate a secure password reset token with expiration."""
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)
    return token, expires_at


async def create_password_reset_record(
    db: AsyncSession, user_id: str, token: str, expires_at: datetime
) -> None:
    """Create or update password reset record in the database - no duplicates allowed."""
    
    # Check if user already has a password reset record
    stmt = select(PasswordReset).where(PasswordReset.user_id == user_id)
    result = await db.execute(stmt)
    existing_record = result.scalar_one_or_none()
    
    if existing_record:
        # Update existing record with new token and reset status
        existing_record.token = token
        existing_record.expires_at = expires_at
        existing_record.is_used = False
        existing_record.used_at = None
        existing_record.created_at = datetime.now(timezone.utc)
    else:
        # Create new password reset record only if none exists
        password_reset = PasswordReset(
            user_id=user_id,
            token=token,
            expires_at=expires_at,
            is_used=False
        )
        db.add(password_reset)
    
    await db.commit()


async def validate_reset_token(
    db: AsyncSession, token: str, email: str
) -> Tuple[bool, Optional[str], Optional[AdminUser]]:
    """Validate password reset token and return user if valid."""
    # Get user by email
    user = await get_user_by_email(db, email)
    if not user:
        return False, "Email address not found. Please check your email and try again.", None
    
    # Check if account is active (False = active, True = deactivated)
    if user.is_active:
        return False, "Account is deactivated. Please contact support to reactivate your account.", None
    
    # Get the password reset record
    stmt = select(PasswordReset).where(
        PasswordReset.token == token,
        PasswordReset.user_id == user.user_id,
        PasswordReset.is_used == False
    )
    result = await db.execute(stmt)
    reset_record = result.scalar_one_or_none()
    
    if not reset_record:
        return False, "Invalid reset token. Please request a new password reset.", None
    
    # Check if token has expired
    if datetime.now(timezone.utc) > reset_record.expires_at:
        return False, "Reset token has expired. Please request a new password reset.", None
    
    return True, None, user


async def mark_password_reset_used(db: AsyncSession, user_id: str) -> None:
    """Mark the password reset token for a user as used and nullify token."""
    await db.execute(
        update(PasswordReset)
        .where(PasswordReset.user_id == user_id)
        .values(is_used=True, used_at=datetime.now(timezone.utc), token=None)
    )
    await db.commit()


def user_not_found_response():
    """Response for user not found - explicit error message."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "statusCode": status.HTTP_404_NOT_FOUND,
            "message": "Email address not found. Please check your email and try again.",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


def account_deactivated():
    """Response for deactivated accounts."""
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            "statusCode": status.HTTP_403_FORBIDDEN,
            "message": "Account is deactivated. Please contact support to reactivate your account.",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


def account_not_found():
    """Response for when account doesn't exist."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "statusCode": status.HTTP_404_NOT_FOUND,
            "message": "Account not found. Please check your email address or contact support.",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )