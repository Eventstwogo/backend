from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from core.api_response import api_response
from core.config import settings
from db.models.superadmin import Config
from db.sessions.database import get_db
from schemas.config import ConfigOut
from utils.auth import hash_password
from utils.exception_handlers import exception_handler, handle_not_found
from utils.file_uploads import (
    get_media_url,
    remove_file_if_exists,
    save_uploaded_file,
)
from utils.format_validators import PasswordValidator

router = APIRouter()


@router.post(
    "/", response_model=ConfigOut, summary="Create a new configuration"
)
@exception_handler
async def create_config(
    default_password: str = Form(
        ...,
        title="Default Password",
        description=(
            "A strong password for new users. Must be at least 8 characters "
            "long and include uppercase, lowercase, digits, and special "
            "characters."
        ),
        example="Str0ngP@ss!",
    ),
    global_180_day_flag: bool = Form(
        ...,
        title="Global 180-Day Flag",
        description="Enable or disable the global 180-day rule for all users.",
        example=True,
    ),
    logo: UploadFile = File(
        ...,
        title="Company Logo",
        description=(
            "Upload a company logo image (PNG, JPG, GIF, WebP). Max 10MB."
        ),
    ),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    # Singleton config check
    result = await db.execute(select(Config))
    if result.scalars().first():
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Configuration already exists.",
            log_error=True,
        )

    # Validate password strength
    validation_result = PasswordValidator.validate(default_password)

    if validation_result["status_code"] != status.HTTP_200_OK:
        return api_response(
            status_code=int(
                validation_result["status_code"]
            ),  # ensure it's int
            message=str(validation_result["message"]),  # ensure it's str
            log_error=True,
        )

    # Upload logo via centralized utility
    uploaded_logo_url = await save_uploaded_file(
        logo, settings.CONFIG_LOGO_PATH
    )

    # Create config
    config = Config(
        id=1,  # Single config entry
        default_password=default_password,
        default_password_hash=hash_password(default_password),
        logo_url=uploaded_logo_url,
        global_180_day_flag=global_180_day_flag,
    )

    db.add(config)
    await db.commit()
    await db.refresh(config)

    config.logo_url = get_media_url(config.logo_url)
    return api_response(
        status_code=status.HTTP_201_CREATED,
        message="Configuration created successfully.",
        data=config,
    )


@router.get(
    "/", response_model=ConfigOut, summary="Get the current configuration"
)
@exception_handler
async def get_config(
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    result = await db.execute(select(Config))
    config = result.scalars().first()
    if not config:
        return handle_not_found("Configuration")

    config.logo_url = get_media_url(config.logo_url)

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Configuration retrieved successfully.",
        data=config,
    )


@router.put(
    "/", response_model=ConfigOut, summary="Update the existing configuration"
)
@exception_handler
async def update_config(
    default_password: str = Form(
        default=None,
        title="Default Password",
        description="A strong password that meets security criteria.",
        example="P@ssw0rd123",
    ),
    global_180_day_flag: bool = Form(
        default=None,
        title="Global 180-Day Flag",
        description="Indicates whether the global 180-day restriction is enabled.",
        example=True,
    ),
    logo: UploadFile = File(
        default=None,
        title="Company Logo",
        description="Upload a company logo file (jpg, png, gif, webp).",
    ),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    # Fetch existing config
    result = await db.execute(select(Config))
    config = result.scalars().first()

    if not config:
        return handle_not_found("Configuration")

    # === Password validation ===
    if default_password:
        validation = PasswordValidator.validate(default_password)
        if validation["status_code"] != status.HTTP_200_OK:
            return api_response(
                status_code=int(validation["status_code"]),
                message=str(validation["message"]),
                log_error=True,
            )

        config.default_password = default_password
        config.default_password_hash = hash_password(default_password)

    # === Update boolean flag ===
    if global_180_day_flag is not None:
        config.global_180_day_flag = global_180_day_flag

    # === Handle logo upload ===
    if logo and logo.filename:
        config.logo_url = await save_uploaded_file(
            logo, settings.CONFIG_LOGO_PATH
        )

    await db.commit()
    await db.refresh(config)

    # Convert internal path to public media URL
    config.logo_url = get_media_url(config.logo_url)

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Configuration updated successfully.",
        data=config,
    )


@router.patch(
    "/logo", response_model=ConfigOut, summary="Update the existing logo"
)
@exception_handler
async def update_logo(
    logo: UploadFile = File(
        ...,
        title="Company Logo",
        description="Upload a company logo file (jpg, png, gif, webp).",
    ),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    # Singleton config check
    result = await db.execute(select(Config))
    config = result.scalars().first()
    if not config:
        return handle_not_found("Configuration")

    # Handle Logo validation and upload
    if logo is None:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Logo file is required.",
            log_error=True,
        )
    if logo.content_type not in settings.ALLOWED_MEDIA_TYPES:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Invalid file type for Logo.",
            log_error=True,
        )

    # Upload new Logo
    uploaded_logo_url = await save_uploaded_file(
        logo, settings.CONFIG_LOGO_PATH
    )

    # Delete previous Logo using the utility function
    if config.logo_url:
        remove_file_if_exists(config.logo_url)

    # Update and save
    config.logo_url = uploaded_logo_url
    await db.commit()
    await db.refresh(config)

    config.logo_url = get_media_url(config.logo_url)
    return api_response(
        status_code=status.HTTP_200_OK,
        message="Logo updated successfully.",
        data=config,
    )
