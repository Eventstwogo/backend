"""
user_service.py

Service functions for regular user operations.
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Tuple

from fastapi import status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.api_response import api_response
from db.models.general import User
from utils.id_generators import decrypt_data


async def validate_unique_user(
    db: AsyncSession, username_hash: str, email_hash: str, phone_number_hash: str = None
) -> JSONResponse | None:
    """
    Validate that username, email, and phone number are unique.
    
    Args:
        db: Database session
        username_hash: Hashed username to check
        email_hash: Hashed email to check
        phone_number_hash: Hashed phone number to check (optional)
        
    Returns:
        JSONResponse if user exists, None if unique
    """
    # Check username hash
    username_query = await db.execute(
        select(User).where(User.username_hash == username_hash)
    )
    if username_query.scalar_one_or_none():
        return api_response(
            status_code=status.HTTP_409_CONFLICT,
            message="Username already exists. Please choose a different username.",
            log_error=True,
        )
    
    # Check email hash
    email_query = await db.execute(
        select(User).where(User.email_hash == email_hash)
    )
    if email_query.scalar_one_or_none():
        return api_response(
            status_code=status.HTTP_409_CONFLICT,
            message="User with this email already exists.",
            log_error=True,
        )
    
    # Check phone number hash if provided
    if phone_number_hash:
        phone_query = await db.execute(
            select(User).where(User.phone_number_hash == phone_number_hash)
        )
        if phone_query.scalar_one_or_none():
            return api_response(
                status_code=status.HTTP_409_CONFLICT,
                message="User with this phone number already exists.",
                log_error=True,
            )
    
    return None


def generate_verification_tokens(expires_in_minutes: int = 60) -> Tuple[str, datetime]:
    """
    Generate a secure verification token with expiration.
    
    Args:
        expires_in_minutes: Token expiration time in minutes
        
    Returns:
        Tuple of (token, expiration_datetime)
    """
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)
    return token, expires_at


async def get_user_by_id(db: AsyncSession, user_id: str) -> User | None:
    """
    Get user by user_id.
    
    Args:
        db: Database session
        user_id: User ID to search for
        
    Returns:
        User object if found, None otherwise
    """
    result = await db.execute(
        select(User).where(User.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_user_by_username_hash(db: AsyncSession, username_hash: str) -> User | None:
    """
    Get user by username hash.
    
    Args:
        db: Database session
        username_hash: Hashed username to search for
        
    Returns:
        User object if found, None otherwise
    """
    result = await db.execute(
        select(User).where(User.username_hash == username_hash)
    )
    return result.scalar_one_or_none()


async def get_user_by_email_hash(db: AsyncSession, email_hash: str) -> User | None:
    """
    Get user by email hash.
    
    Args:
        db: Database session
        email_hash: Hashed email to search for
        
    Returns:
        User object if found, None otherwise
    """
    result = await db.execute(
        select(User).where(User.email_hash == email_hash)
    )
    return result.scalar_one_or_none()


async def get_user_by_phone_hash(db: AsyncSession, phone_number_hash: str) -> User | None:
    """
    Get user by phone number hash.
    
    Args:
        db: Database session
        phone_number_hash: Hashed phone number to search for
        
    Returns:
        User object if found, None otherwise
    """
    result = await db.execute(
        select(User).where(User.phone_number_hash == phone_number_hash)
    )
    return result.scalar_one_or_none()


def decrypt_user_data(user: User, original_username: str = None, original_email: str = None, original_phone: str = None) -> dict:
    """
    Decrypt user sensitive data for display purposes.
    
    Args:
        user: User object with encrypted data
        original_username: Original username (since username_hash is one-way hash)
        original_email: Original email (since email_hash is one-way hash)
        original_phone: Original phone (since phone_number_hash is one-way hash)
        
    Returns:
        Dictionary with decrypted user data
    """
    return {
        "user_id": user.user_id,
        "username": original_username,  # Username hash is one-way, need original
        "first_name": decrypt_data(user.first_name_hash),
        "last_name": decrypt_data(user.last_name_hash),
        "email": original_email,  # Email hash is one-way, need original
        "phone_number": original_phone,  # Phone hash is one-way, need original
        "login_status": user.login_status,
        "successful_logins": user.successful_logins,
        "failed_logins": user.failed_logins,
        "last_login": user.last_login,
        "account_locked_at": user.account_locked_at,
        "created_at": user.created_at,
        "is_active": user.is_active,
    }