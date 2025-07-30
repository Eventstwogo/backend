"""
Vendor password reset service functions.
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from fastapi import status
from fastapi.responses import JSONResponse
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from core.api_response import api_response
from db.models.superadmin import VendorLogin, VendorPasswordReset
from utils.id_generators import hash_data


async def get_vendor_by_email(db: AsyncSession, email: str) -> Optional[VendorLogin]:
    """Get vendor by email address."""
    # Hash the email to match the stored hash (same as user system)
    email_hash = hash_data(email.lower().strip())
    
    result = await db.execute(
        select(VendorLogin).where(VendorLogin.email_hash == email_hash)
    )
    return result.scalar_one_or_none()


def generate_password_reset_token(expires_in_minutes: int = 60) -> Tuple[str, datetime]:
    """Generate a secure password reset token with expiration."""
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)
    return token, expires_at


async def create_password_reset_record(
    db: AsyncSession,
    user_id: str,
    token: str,
    expires_at: datetime,
) -> None:
    """Create a password reset record in the database."""
    # First, invalidate any existing tokens for this user
    await db.execute(
        select(VendorPasswordReset)
        .where(
            and_(
                VendorPasswordReset.user_id == user_id,
                VendorPasswordReset.is_used == False,
                VendorPasswordReset.expires_at > datetime.now(timezone.utc)
            )
        )
    )
    
    # Mark existing tokens as used
    existing_tokens = await db.execute(
        select(VendorPasswordReset).where(VendorPasswordReset.user_id == user_id)
    )
    for existing_token in existing_tokens.scalars():
        existing_token.is_used = True
    
    # Create new password reset record
    password_reset = VendorPasswordReset(
        user_id=user_id,
        token=token,
        expires_at=expires_at,
        is_used=False,
        created_at=datetime.now(timezone.utc)
    )
    
    db.add(password_reset)
    await db.commit()


async def validate_reset_token(
    db: AsyncSession, 
    token: str, 
    email: str
) -> Tuple[bool, str, Optional[VendorLogin]]:
    """Validate password reset token and return user if valid."""
    
    # Step 1: Get vendor by email
    vendor = await get_vendor_by_email(db, email)
    if not vendor:
        return False, "Vendor with this email address not found.", None
    
    # Step 2: Check if vendor account is active (False = active, True = inactive)
    if vendor.is_active:  # True means account is inactive
        return False, "Vendor account is inactive.", None
    
    # Step 3: Check if vendor is verified
    if vendor.is_verified == 0:  # 0 = unverified, 1 = verified
        return False, "Vendor account is not verified. Please verify your email address first.", None
    
    # Step 4: Find the password reset record
    result = await db.execute(
        select(VendorPasswordReset).where(
            and_(
                VendorPasswordReset.user_id == vendor.user_id,
                VendorPasswordReset.token == token,
                VendorPasswordReset.is_used == False
            )
        )
    )
    reset_record = result.scalar_one_or_none()
    
    if not reset_record:
        return False, "Invalid reset token. Please request a new password reset.", None
    
    # Step 5: Check if token has expired
    if reset_record.expires_at < datetime.now(timezone.utc):
        return False, "Reset token has expired. Please request a new password reset.", None
    
    return True, "Token is valid.", vendor


async def mark_password_reset_used(db: AsyncSession, user_id: str) -> None:
    """Mark all password reset tokens for a user as used."""
    result = await db.execute(
        select(VendorPasswordReset).where(VendorPasswordReset.user_id == user_id)
    )
    
    for reset_record in result.scalars():
        reset_record.is_used = True
    
    await db.commit()


def vendor_not_found_response() -> JSONResponse:
    """Response for vendor not found - explicit error message to match user system."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "statusCode": status.HTTP_404_NOT_FOUND,
            "message": "Email address not found. Please check your email and try again.",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


def vendor_account_inactive() -> JSONResponse:
    """Response for inactive vendor accounts."""
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            "statusCode": status.HTTP_403_FORBIDDEN,
            "message": "Account is inactive. Please contact support to activate your account.",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


def vendor_account_not_verified() -> JSONResponse:
    """Response for unverified vendor accounts."""
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            "statusCode": status.HTTP_403_FORBIDDEN,
            "message": "Account is not verified. Please verify your email address first.",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )