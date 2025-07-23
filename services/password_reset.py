import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from fastapi import status
from fastapi.responses import JSONResponse

from db.models.superadmin import AdminUser, PasswordReset
from utils.auth import verify_password


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[AdminUser]:
    """Get user by email address."""
    stmt = select(AdminUser).where(AdminUser.email == email.lower())
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
    """Create a password reset record in the database."""
    # First, mark any existing unused tokens as used
    await db.execute(
        update(PasswordReset)
        .where(PasswordReset.user_id == user_id, PasswordReset.is_used == False)
        .values(is_used=True, used_at=datetime.now(timezone.utc))
    )
    
    # Create new password reset record
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
    
    # Check if account is active
    if not user.is_active:
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
    """Mark all password reset tokens for a user as used."""
    await db.execute(
        update(PasswordReset)
        .where(PasswordReset.user_id == user_id, PasswordReset.is_used == False)
        .values(is_used=True, used_at=datetime.now(timezone.utc))
    )


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