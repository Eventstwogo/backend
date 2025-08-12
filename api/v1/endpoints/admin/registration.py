from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse
from passlib.context import CryptContext
from utils.email_utils import send_admin_welcome_email
from utils.validations import generate_random_password
from core.api_response import api_response
from db.models.superadmin import AdminUser, Config, Role
from db.sessions.database import get_db
from schemas.admin_user import (
    AdminCreateRequest,
    AdminCreateResponse,
    AdminRegisterRequest,
    AdminRegisterResponse,
)
from services.admin_user import (
    get_config_or_404,
    validate_role,
    validate_superadmin_uniqueness,
    validate_unique_user,
)
from services.admin_password_service import generate_and_send_admin_credentials
from utils.exception_handlers import exception_handler
from utils.file_uploads import get_media_url
from utils.id_generators import encrypt_data, generate_lower_uppercase, hash_data, decrypt_data


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


router = APIRouter()


@router.post("/admin/create", response_model=AdminCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_admin_user(
    admin_data: AdminCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        # Convert email to lowercase for case-insensitive storage and comparison
        normalized_email = admin_data.email.strip().lower()
        
        # Check if user with this email already exists
        email_hash = hash_data(normalized_email)
        existing_user_stmt = select(AdminUser).where(AdminUser.email_hash == email_hash)
        existing_user_result = await db.execute(existing_user_stmt)
        existing_user = existing_user_result.scalar_one_or_none()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists"
            )
        
        # Check if username already exists (need to check encrypted usernames)
        # Capitalize first letter of username
        capitalized_username = admin_data.username.strip().capitalize()
        encrypted_username = encrypt_data(capitalized_username)
        existing_username_stmt = select(AdminUser).where(AdminUser.username == encrypted_username)
        existing_username_result = await db.execute(existing_username_stmt)
        existing_username_user = existing_username_result.scalar_one_or_none()
        
        if existing_username_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this username already exists"
            )
        
        # Get SUPERADMIN role from roles table
        role_stmt = select(Role).where(Role.role_name == "SUPERADMIN")
        role_result = await db.execute(role_stmt)
        superadmin_role = role_result.scalar_one_or_none()
        
        if not superadmin_role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="SUPERADMIN role not found in database"
            )
        
        # Check superadmin uniqueness - only allow one superadmin
        superadmin_result = await validate_superadmin_uniqueness(db, superadmin_role)
        if superadmin_result is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Super Admin already exists. Only one Super Admin is allowed."
            )
        
        # Generate unique user ID
        user_id = generate_lower_uppercase(length=6)
        
        # Encrypt sensitive data (use normalized lowercase email)
        encrypted_email = encrypt_data(normalized_email)
        
        # Hash password
        hashed_password = pwd_context.hash(admin_data.password)
        
        # Create new admin user
        new_admin = AdminUser(
            user_id=user_id,
            role_id=superadmin_role.role_id,
            username=encrypted_username,
            email=encrypted_email,
            email_hash=email_hash,
            password=hashed_password,
            login_status=0,  # Default login status is 0 (no email verification required)
            is_active=False, 
        )
        
        # Add to database
        db.add(new_admin)
        await db.commit()
        await db.refresh(new_admin)
        
        # Send welcome email
        email_sent = False
        
        try:
            email_sent = send_admin_welcome_email(
                email=normalized_email,  # Use normalized email for sending
                username=capitalized_username,
                password=admin_data.password,  # Send the plain password in email
            )
        except Exception as e:
            # Log the error but don't fail the user creation
            print(f"Failed to send welcome email: {e}")
        
        return AdminCreateResponse(
            user_id=user_id,
            username=capitalized_username,
            email=normalized_email,  # Return normalized email
            role_id=superadmin_role.role_id,
            message="Admin user created successfully" + (" and welcome email sent" if email_sent else " but email sending failed"),
            email_sent=email_sent
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create admin user: {str(e)}"
        )

@router.post(
    "/register",
    response_model=AdminRegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
@exception_handler
async def register_user(
    background_tasks: BackgroundTasks,
    user_data: AdminRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    
    # Convert email to lowercase for case-insensitive storage and comparison
    normalized_email = user_data.email.strip().lower()
    
    # Capitalize first letter of username
    capitalized_username = user_data.username.strip().capitalize()
    encrypted_username = encrypt_data(capitalized_username)
    encrypted_email = encrypt_data(normalized_email)

    # Check if encrypted data length is within database limits
    if len(encrypted_username) > 500:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Username is too long for encryption storage.",
            log_error=True,
        )
    
    if len(encrypted_email) > 500:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Email is too long for encryption storage.",
            log_error=True,
        )

    email_hash = hash_data(normalized_email)

    # Check if user already exists
    existing_user_stmt = select(AdminUser).where(AdminUser.email_hash == email_hash)
    existing_user_result = await db.execute(existing_user_stmt)
    existing_user = existing_user_result.scalar_one_or_none()
    
    if existing_user:
        # If user exists and is inactive (is_active=True means inactive), reactivate them
        if existing_user.is_active:  # True means inactive
            # Simply reactivate the user
            existing_user.is_active = False  # False means active
            
            await db.commit()
            await db.refresh(existing_user)
            
            return api_response(
                status_code=status.HTTP_200_OK,
                message="User reactivated successfully.",
                data=AdminRegisterResponse(
                    user_id=existing_user.user_id,
                    email=normalized_email,
                    username=decrypt_data(existing_user.username),
                    password="",  # Don't expose existing password
                ),
            )
        else:
            # User exists and is active, return conflict error
            return api_response(
                status_code=status.HTTP_409_CONFLICT,
                message="User with the given email already exists and is active.",
                log_error=True,
            )

    # Validate role
    role_result = await validate_role(db, user_data.role_id)
    if not isinstance(role_result, Role):
        return role_result

    role = role_result

    # Check superadmin uniqueness
    superadmin_result = await validate_superadmin_uniqueness(db, role)
    if superadmin_result is not None:
        return superadmin_result

    # Get system configuration
    config_result = await get_config_or_404(db)
    if not isinstance(config_result, Config):
        return config_result

    config = config_result

    # Generate unique user ID and random password for new admin
    user_id = generate_lower_uppercase(length=6)
    logo_url = get_media_url(config.logo_url or "") or ""
    
    # Generate random password and send credentials via email
    plain_password, hashed_password, email_sent = generate_and_send_admin_credentials(
        email=normalized_email,  # Use normalized email
        username=capitalized_username,
        logo_url=logo_url
    )
    
    # Check if password generation was successful
    if not hashed_password:
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to generate admin password. Please try again.",
            log_error=True,
        )

    # Create new user
    new_user = AdminUser(
        user_id=user_id,
        role_id=user_data.role_id,
        username=encrypted_username,
        email=encrypted_email,
        email_hash=email_hash,
        password=hashed_password,
        login_status=-1,  # Default to -1 (not logged in)
        days_180_flag=config.global_180_day_flag,
    )

    # Add to database
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Return success response with email status
    email_status = "Credentials email sent successfully." if email_sent else "User created but email sending failed."
    message = f"User registered successfully. {email_status}"
    
    return api_response(
        status_code=status.HTTP_201_CREATED,
        message=message,
        data=AdminRegisterResponse(
            user_id=user_id,
            email=normalized_email,  # Return normalized email
            username=capitalized_username,
            password=plain_password,
        ),
    )