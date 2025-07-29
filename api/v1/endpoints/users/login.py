"""
User login endpoint.
"""

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone, timedelta

from core.api_response import api_response
from db.models.general import User
from db.sessions.database import get_db
from schemas.register import UserLoginRequest, UserLoginResponse, UserDetailResponse, UsersListResponse, BasicUserResponse, BasicUsersListResponse
from utils.auth import verify_password
from utils.exception_handlers import exception_handler
from utils.id_generators import hash_data, decrypt_data

router = APIRouter()

# Maximum failed login attempts before account lock
MAX_FAILED_ATTEMPTS = 5
# Account unlock time in hours
ACCOUNT_UNLOCK_HOURS = 24


@router.post(
    "/login",
    response_model=UserLoginResponse,
    status_code=status.HTTP_200_OK,
)
@exception_handler
async def login_user(
    login_data: UserLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    
    # Hash email for lookup
    email_hash = hash_data(login_data.email.lower())
    
    # Find user by email hash
    user_result = await db.execute(
        select(User).where(User.email_hash == email_hash)
    )
    user = user_result.scalar_one_or_none()
    
    if not user:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found. Please check your email address.",
            log_error=True,
        )
    
    # Verify password first
    if not verify_password(login_data.password, user.password_hash):
        # Only increment failed login attempts for verified users
        if user.login_status != -1:  # -1 means unverified
            user.failed_logins += 1
            
            # Check if we should lock the account
            if user.failed_logins >= MAX_FAILED_ATTEMPTS:
                user.login_status = 1  # Lock the account
                user.account_locked_at = datetime.now(timezone.utc)
                db.add(user)
                await db.commit()
                
                return api_response(
                    status_code=status.HTTP_423_LOCKED,
                    message="Account locked due to too many failed login attempts. Please contact support.",
                    log_error=True,
                )
            
            # Save failed attempt count
            db.add(user)
            await db.commit()
            
            remaining_attempts = MAX_FAILED_ATTEMPTS - user.failed_logins
            return api_response(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message=f"Invalid password. {remaining_attempts} attempts remaining before account lock.",
                log_error=True,
            )
        else:
            # For unverified users, don't count failed attempts
            return api_response(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="Invalid password.",
                log_error=True,
            )
    
    # Check if user is not verified (after password verification)
    if user.login_status == -1:
        return api_response(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Please verify your email address before logging in.",
            log_error=True,
        )
    
    # Check if account is locked and handle auto-unlock after 24 hours
    if user.login_status == 1:
        # Check if account has been locked for more than 24 hours
        if user.account_locked_at:
            time_since_lock = datetime.now(timezone.utc) - user.account_locked_at
            if time_since_lock >= timedelta(hours=ACCOUNT_UNLOCK_HOURS):
                # Automatically unlock the account
                user.login_status = 0  # Unlock account
                user.failed_logins = 0  # Reset failed attempts
                user.account_locked_at = None  # Clear lock timestamp
                db.add(user)
                await db.commit()
                await db.refresh(user)
                # Continue with login process (don't return here)
            else:
                # Account is still locked
                hours_remaining = ACCOUNT_UNLOCK_HOURS - (time_since_lock.total_seconds() / 3600)
                return api_response(
                    status_code=status.HTTP_423_LOCKED,
                    message=f"Account is locked due to too many failed login attempts. Account will be automatically unlocked in {hours_remaining:.1f} hours or contact support.",
                    log_error=True,
                )
        else:
            # No lock timestamp, unlock immediately (shouldn't happen but safety check)
            user.login_status = 0
            user.failed_logins = 0
            db.add(user)
            await db.commit()
            await db.refresh(user)
    
    # Check if account is inactive (true = inactive, false = active)
    if user.is_active:
        return api_response(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Account is inactive. Please contact support.",
            log_error=True,
        )
    
    # Successful login - update login tracking
    user.successful_logins += 1
    user.failed_logins = 0  # Reset failed attempts on successful login
    user.last_login = datetime.now(timezone.utc)
    
    # Save changes
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return api_response(
        status_code=status.HTTP_200_OK,
        message="Login successful.",
        data=UserLoginResponse(
            message="Login successful.",
            user_id=user.user_id,
        ),
    )


@router.get(
    "/user/{user_id}",
    response_model=BasicUserResponse,
    status_code=status.HTTP_200_OK,
)
@exception_handler
async def get_user_by_id(
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Get user details by user ID.
    
    - Returns decrypted user information
    - Includes login statistics and status
    """
    
    # Find user by user_id
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
    
    # Decrypt sensitive data
    try:
        # Helper function to safely decrypt data
        def safe_decrypt(encrypted_data):
            if not encrypted_data or not isinstance(encrypted_data, str):
                return ""
            try:
                return decrypt_data(encrypted_data)
            except Exception as decrypt_error:
                print(f"Failed to decrypt individual field: {str(decrypt_error)}")
                return "DECRYPTION_ERROR"
        
        # Decrypt the encrypted fields for display
        decrypted_username = safe_decrypt(user.username)
        decrypted_first_name = safe_decrypt(user.first_name)
        decrypted_last_name = safe_decrypt(user.last_name)
        decrypted_email = safe_decrypt(user.email)
        decrypted_phone = safe_decrypt(user.phone_number) if user.phone_number else None
        
        # No need to mask email since we now have the decrypted version
        # masked_email = decrypted_email  # Show full email or mask as needed
        
    except Exception as e:
        print(f"Error decrypting user data for user_id {user_id}: {str(e)}")
        print(f"User data - username exists: {bool(user.username)}")
        print(f"User data - first_name exists: {bool(user.first_name)}")
        print(f"User data - last_name exists: {bool(user.last_name)}")
        print(f"User data - email exists: {bool(user.email)}")
        print(f"User data - phone_number exists: {bool(user.phone_number)}")
        
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Error decrypting user data: {str(e)}",
            log_error=True,
        )
    
    user_data = BasicUserResponse(
        user_id=user.user_id,
        username=decrypted_username,
        first_name=decrypted_first_name,
        last_name=decrypted_last_name,
        email=decrypted_email,
        phone_number=decrypted_phone,
    )
    
    return api_response(
        status_code=status.HTTP_200_OK,
        message="User retrieved successfully.",
        data=user_data,
    )


@router.get(
    "/users",
    response_model=BasicUsersListResponse,
    status_code=status.HTTP_200_OK,
)
@exception_handler
async def get_all_users(
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Get all users.
    
    - Returns list of users with decrypted information
    - Includes total count
    """
    
    # Get total count
    count_result = await db.execute(
        select(func.count(User.user_id))
    )
    total_count = count_result.scalar()
    
    # Get all users
    users_result = await db.execute(
        select(User)
        .order_by(User.created_at.desc())
    )
    users = users_result.scalars().all()
    
    # Decrypt and format user data  
    users_list = []
    for user in users:
        try:
            # Helper function to safely decrypt data
            def safe_decrypt(encrypted_data):
                if not encrypted_data or not isinstance(encrypted_data, str):
                    return ""
                try:
                    return decrypt_data(encrypted_data)
                except Exception as decrypt_error:
                    print(f"Failed to decrypt field for user {user.user_id}: {str(decrypt_error)}")
                    return "DECRYPTION_ERROR"
            
            # Decrypt the encrypted fields for display
            decrypted_username = safe_decrypt(user.username)
            decrypted_first_name = safe_decrypt(user.first_name)
            decrypted_last_name = safe_decrypt(user.last_name)
            decrypted_email = safe_decrypt(user.email)
            decrypted_phone = safe_decrypt(user.phone_number) if user.phone_number else None
            
            user_data = BasicUserResponse(
                user_id=user.user_id,
                username=decrypted_username,
                first_name=decrypted_first_name,
                last_name=decrypted_last_name,
                email=decrypted_email,
                phone_number=decrypted_phone,
            )
            users_list.append(user_data)
            
        except Exception as e:
            # Log the error but continue with other users
            print(f"Error processing user {user.user_id}: {str(e)}")
            continue
    
    response_data = BasicUsersListResponse(
        users=users_list,
        total_count=total_count,
    )
    
    return api_response(
        status_code=status.HTTP_200_OK,
        message=f"Retrieved {len(users_list)} users successfully.",
        data=response_data,
    )