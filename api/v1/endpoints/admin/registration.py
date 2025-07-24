from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse
from passlib.context import CryptContext
from utils.validations import generate_random_password
from core.api_response import api_response
from db.models.superadmin import AdminUser, Config, Role
from db.sessions.database import get_db
from schemas.admin_user import (
    AdminRegisterRequest,
    AdminRegisterResponse,
)
from services.admin_user import (
    get_config_or_404,
    validate_role,
    validate_superadmin_uniqueness,
    validate_unique_user,
)
from utils.email import send_welcome_email
from utils.exception_handlers import exception_handler
from utils.file_uploads import get_media_url
from utils.id_generators import encrypt_data, generate_lower_uppercase, hash_data


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


router = APIRouter()

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
    
    encrypted_username = encrypt_data(user_data.username)
    encrypted_email = encrypt_data(user_data.email)

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

    email_hash = hash_data(user_data.email)

    # Check if user already exists
    unique_user_result = await validate_unique_user(db, email_hash)
    if unique_user_result is not None:
        return unique_user_result

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

    # Generate unique user ID and use default password for new admins
    user_id = generate_lower_uppercase(length=6)
    plain_password = config.default_password  # Use default password from config
    hashed_password = config.default_password_hash  # Use pre-hashed default password

    # Create new user
    new_user = AdminUser(
        user_id=user_id,
        role_id=user_data.role_id,
        username=encrypted_username,
        email=encrypted_email,
        email_hash=email_hash,
        password=hashed_password,
        days_180_flag=config.global_180_day_flag,
    )

    # Add to database
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Send welcome email in background
    logo_url = get_media_url(config.logo_url or "") or ""

    background_tasks.add_task(
        send_welcome_email,
        email=user_data.email,
        username=user_data.username,
        password=plain_password,  # Send the plain password in email
        logo_url=logo_url,
    )

    # Return success response
    return api_response(
        status_code=status.HTTP_201_CREATED,
        message="User registered successfully. Welcome email sent in background.",
        data=AdminRegisterResponse(
            user_id=user_id,
            email=user_data.email,
            username=user_data.username,
        ),
    )