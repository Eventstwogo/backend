"""
User login endpoint.
"""

from fastapi import APIRouter, Depends, status, Request, Form
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_
from datetime import datetime, timezone, timedelta
from user_agents import parse as parse_user_agent
from typing import List, Optional
import uuid
import jwt
import httpx
import asyncio

from core.api_response import api_response
from db.models.general import User
from db.models.superadmin import SessionLog
from db.sessions.database import get_db
from utils.id_generators import random_token
from schemas.register import UserLoginRequest, UserLoginResponse, UserDetailResponse, UsersListResponse, BasicUserResponse, BasicUsersListResponse
from utils.auth import verify_password
from utils.exception_handlers import exception_handler
from utils.id_generators import hash_data, decrypt_data
from utils.jwt import create_access_token, decode_access_token

router = APIRouter()

# Maximum failed login attempts before account lock
MAX_FAILED_ATTEMPTS = 5
# Account unlock time in hours
ACCOUNT_UNLOCK_HOURS = 24

# Session response schemas
from pydantic import BaseModel

class SessionLogResponse(BaseModel):
    id: int
    session_id: str
    user_id: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    browser_name: Optional[str] = None
    browser_version: Optional[str] = None
    os: Optional[str] = None
    device_type: Optional[str] = None
    login_time: datetime
    logout_time: Optional[datetime] = None
    login_success: bool
    failure_reason: Optional[str] = None
    location: Optional[str] = None

class SessionHistoryResponse(BaseModel):
    sessions: List[SessionLogResponse]
    total_count: int

async def get_location_from_ip(ip_address: str) -> str:
    """
    Get location from IP address using free IP geolocation API
    """
    try:
        # Skip location lookup for local/private IPs
        if ip_address in ["127.0.0.1", "localhost", "unknown"] or ip_address.startswith("192.168.") or ip_address.startswith("10.") or ip_address.startswith("172."):
            return "Local Network"
        
        # Use a free IP geolocation service
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"http://ip-api.com/json/{ip_address}")
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    city = data.get("city", "")
                    region = data.get("regionName", "")
                    country = data.get("country", "")
                    
                    # Build location string
                    location_parts = []
                    if city:
                        location_parts.append(city)
                    if region and region != city:
                        location_parts.append(region)
                    if country:
                        location_parts.append(country)
                    
                    return ", ".join(location_parts) if location_parts else "Unknown Location"
        
        return "Location unavailable"
    except Exception as e:
        print(f"Error getting location for IP {ip_address}: {str(e)}")
        return "Location unavailable"

async def generate_secure_session_id(db: AsyncSession) -> str:
    """
    Generate secure random session ID in format like PGfq-zJQ-EQbQ-97Y4J.
    """
    # Generate a secure random token using the existing utility function
    return random_token()

async def log_user_session(
    db: AsyncSession,
    user_id: str,
    request: Request,
    login_success: bool = True,
    failure_reason: Optional[str] = None
) -> SessionLog:
    """
    Log user session with detailed information
    """
    # Get IP and User-Agent
    client_ip = request.client.host or "unknown"
    user_agent_str = request.headers.get("user-agent", "unknown")
    parsed_ua = parse_user_agent(user_agent_str)

    # Parse browser and device info
    browser_name = parsed_ua.browser.family
    browser_version = parsed_ua.browser.version_string
    os = parsed_ua.os.family
    device_type = "Mobile" if parsed_ua.is_mobile else "Tablet" if parsed_ua.is_tablet else "Desktop"

    # Generate secure random session ID
    session_id = await generate_secure_session_id(db)

    # Get location from IP address
    location = await get_location_from_ip(client_ip)

    # Create session log entry
    session_log = SessionLog(
        session_id=session_id,
        user_id=user_id,
        ip_address=client_ip,
        user_agent=user_agent_str,
        browser_name=browser_name,
        browser_version=browser_version,
        os=os,
        device_type=device_type,
        login_success=login_success,
        failure_reason=failure_reason,
        location=location,
        login_time=datetime.utcnow()
    )

    db.add(session_log)
    await db.commit()
    await db.refresh(session_log)
    
    return session_log


@router.post(
    "/login",
    response_model=UserLoginResponse,
    status_code=status.HTTP_200_OK,
)
@exception_handler
async def login_user(
    login_data: UserLoginRequest,
    request: Request,
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
        # Log failed login attempt - user not found
        # We can't log with user_id since user doesn't exist, so we'll use email hash
        await log_user_session(
            db=db,
            user_id=f"UNK{email_hash[:3]}",  # Use 6-char tracking ID for failed logins
            request=request,
            login_success=False,
            failure_reason="User not found"
        )
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
                
                # Log failed login attempt - account locked
                await log_user_session(
                    db=db,
                    user_id=user.user_id,
                    request=request,
                    login_success=False,
                    failure_reason="Account locked due to maximum failed attempts"
                )
                
                return api_response(
                    status_code=status.HTTP_423_LOCKED,
                    message="Account locked due to too many failed login attempts. Please contact support.",
                    log_error=True,
                )
            
            # Save failed attempt count
            db.add(user)
            await db.commit()
            
            # Log failed login attempt - incorrect password
            await log_user_session(
                db=db,
                user_id=user.user_id,
                request=request,
                login_success=False,
                failure_reason="Incorrect password"
            )
            
            remaining_attempts = MAX_FAILED_ATTEMPTS - user.failed_logins
            return api_response(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message=f"Invalid password. {remaining_attempts} attempts remaining before account lock.",
                log_error=True,
            )
        else:
            # For unverified users, don't count failed attempts
            # Log failed login attempt - unverified user with wrong password
            await log_user_session(
                db=db,
                user_id=user.user_id,
                request=request,
                login_success=False,
                failure_reason="Invalid password for unverified user"
            )
            return api_response(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="Invalid password.",
                log_error=True,
            )
    
    # Check if user is not verified (after password verification)
    if user.login_status == -1:
        # Log failed login attempt - user not verified
        await log_user_session(
            db=db,
            user_id=user.user_id,
            request=request,
            login_success=False,
            failure_reason="User not verified"
        )
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
                # Log failed login attempt - account still locked
                await log_user_session(
                    db=db,
                    user_id=user.user_id,
                    request=request,
                    login_success=False,
                    failure_reason="Account is locked"
                )
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
        # Log failed login attempt - account inactive
        await log_user_session(
            db=db,
            user_id=user.user_id,
            request=request,
            login_success=False,
            failure_reason="Account is inactive"
        )
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
    
    # Log successful login session
    session_log = await log_user_session(
        db=db,
        user_id=user.user_id,
        request=request,
        login_success=True
    )
    
    # Generate access token with user ID and session information
    token_data = {
        "user_id": user.user_id,
        "session_id": session_log.session_id,
        "login_time": session_log.login_time.isoformat()
    }
    access_token = create_access_token(data=token_data)
    
    # Log successful login with access token generation
    print(f"Access token generated for user_id: {user.user_id} with session_id: {session_log.session_id} at {datetime.now(timezone.utc)}")
    
    return api_response(
        status_code=status.HTTP_200_OK,
        message="Login successful.",
        data=UserLoginResponse(
            message="Login successful.",
            user_id=user.user_id,
            access_token=access_token,
        ),
    )


@router.post("/logout")
@exception_handler
async def logout_user(
    request: Request,
    token: str = Form(...),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Logout endpoint to update session logout time
    """
    try:
        # Try to get token from form data first, then from authorization header
        if not token:
            auth_header = request.headers.get("authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return api_response(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    message="No valid token provided",
                    log_error=True,
                )
            token = auth_header.split(" ")[1]
        
        # Extract and decode token to get user info
        try:
            payload = decode_access_token(token)
            user_id = payload.get("user_id")
            session_id = payload.get("session_id")
        except jwt.ExpiredSignatureError:
            return api_response(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="Token has expired",
                log_error=True,
            )
        except jwt.InvalidTokenError:
            return api_response(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="Invalid token",
                log_error=True,
            )
        
        if not user_id:
            return api_response(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="Invalid token payload",
                log_error=True,
            )
        
        # Find and update the session using session_id if available, otherwise fallback to user_id/IP
        if session_id:
            # Use specific session_id from token for accurate tracking
            stmt = select(SessionLog).where(
                and_(
                    SessionLog.session_id == session_id,
                    SessionLog.user_id == user_id,
                    SessionLog.logout_time.is_(None)
                )
            )
        else:
            # Fallback to user_id and IP matching
            client_ip = request.client.host or "unknown"
            stmt = select(SessionLog).where(
                and_(
                    SessionLog.user_id == user_id,
                    SessionLog.ip_address == client_ip,
                    SessionLog.login_success == True,
                    SessionLog.logout_time.is_(None)
                )
            ).order_by(desc(SessionLog.login_time)).limit(1)
        
        result = await db.execute(stmt)
        session_log = result.scalar_one_or_none()
        
        if session_log:
            session_log.logout_time = datetime.utcnow()
            db.add(session_log)
            await db.commit()
            
            return api_response(
                status_code=status.HTTP_200_OK,
                message="Logout successful",
                data={
                    "session_id": session_log.session_id,
                    "logout_time": session_log.logout_time.isoformat()
                }
            )
        else:
            return api_response(
                status_code=status.HTTP_200_OK,
                message="No active session found, but logout processed",
            )
        
    except Exception as e:
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Logout failed: {str(e)}",
            log_error=True,
        )


@router.post("/logout-by-user")
@exception_handler
async def logout_user_by_id(
    request: Request,
    user_id: str = Form(...),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Alternative logout endpoint using user_id (for cases where token is expired/invalid)
    """
    try:
        # Get client IP for session matching
        client_ip = request.client.host or "unknown"
        
        # Find the most recent active session for this user and IP
        stmt = select(SessionLog).where(
            and_(
                SessionLog.user_id == user_id,
                SessionLog.ip_address == client_ip,
                SessionLog.login_success == True,
                SessionLog.logout_time.is_(None)
            )
        ).order_by(desc(SessionLog.login_time)).limit(1)
        
        result = await db.execute(stmt)
        session_log = result.scalar_one_or_none()
        
        if session_log:
            session_log.logout_time = datetime.utcnow()
            db.add(session_log)
            await db.commit()
            
            return api_response(
                status_code=status.HTTP_200_OK,
                message="Logout successful",
                data={
                    "session_id": session_log.session_id,
                    "user_id": user_id,
                    "logout_time": session_log.logout_time.isoformat()
                }
            )
        else:
            return api_response(
                status_code=status.HTTP_200_OK,
                message="No active session found for this user and IP, but logout processed",
                data={"user_id": user_id}
            )
        
    except Exception as e:
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Logout failed: {str(e)}",
            log_error=True,
        )


@router.post("/session-info")
@exception_handler
async def get_session_info(
    request: Request,
    token: str = Form(...),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Get current session information from JWT token
    """
    try:
        # Try to get token from form data first, then from authorization header
        if not token:
            auth_header = request.headers.get("authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return api_response(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    message="No valid token provided",
                    log_error=True,
                )
            token = auth_header.split(" ")[1]
        
        # Extract and decode token
        try:
            payload = decode_access_token(token)
            user_id = payload.get("user_id")
            session_id = payload.get("session_id")
            login_time = payload.get("login_time")
        except jwt.ExpiredSignatureError:
            return api_response(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="Token has expired",
                log_error=True,
            )
        except jwt.InvalidTokenError:
            return api_response(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="Invalid token",
                log_error=True,
            )
        
        # Get session details from database
        if session_id:
            stmt = select(SessionLog).where(SessionLog.session_id == session_id)
            result = await db.execute(stmt)
            session_log = result.scalar_one_or_none()
            
            if session_log:
                return api_response(
                    status_code=status.HTTP_200_OK,
                    message="Session info retrieved successfully",
                    data={
                        "session_id": session_log.session_id,
                        "user_id": session_log.user_id,
                        "ip_address": session_log.ip_address,
                        "browser_name": session_log.browser_name,
                        "device_type": session_log.device_type,
                        "login_time": session_log.login_time.isoformat(),
                        "logout_time": session_log.logout_time.isoformat() if session_log.logout_time else None,
                        "is_active": session_log.logout_time is None
                    }
                )
        
        # Return basic info from token if session not found in DB
        return api_response(
            status_code=status.HTTP_200_OK,
            message="Session info from token only",
            data={
                "user_id": user_id,
                "session_id": session_id,
                "login_time": login_time,
                "source": "token_only"
            }
        )
        
    except Exception as e:
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to get session info: {str(e)}",
            log_error=True,
        )


@router.get("/session-history/{user_id}", response_model=SessionHistoryResponse)
@exception_handler
async def get_session_history(
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Get complete session history for a specific user
    """
    try:
        # Get total count
        count_stmt = select(func.count(SessionLog.id)).where(SessionLog.user_id == user_id)
        count_result = await db.execute(count_stmt)
        total_count = count_result.scalar()
        
        # Get all session logs without pagination
        stmt = select(SessionLog).where(
            SessionLog.user_id == user_id
        ).order_by(desc(SessionLog.login_time))
        
        result = await db.execute(stmt)
        sessions = result.scalars().all()
        
        # Convert to response format
        session_responses = []
        for session in sessions:
            session_responses.append(SessionLogResponse(
                id=session.id,
                session_id=session.session_id,
                user_id=session.user_id,
                ip_address=session.ip_address,
                user_agent=session.user_agent,
                browser_name=session.browser_name,
                browser_version=session.browser_version,
                os=session.os,
                device_type=session.device_type,
                login_time=session.login_time,
                logout_time=session.logout_time,
                login_success=session.login_success,
                failure_reason=session.failure_reason,
                location=session.location
            ))
        
        return api_response(
            status_code=status.HTTP_200_OK,
            message=f"Retrieved {len(session_responses)} sessions successfully",
            data=SessionHistoryResponse(
                sessions=session_responses,
                total_count=total_count
            )
        )
        
    except Exception as e:
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to retrieve session history: {str(e)}",
            log_error=True,
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
                is_active=user.is_active,
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