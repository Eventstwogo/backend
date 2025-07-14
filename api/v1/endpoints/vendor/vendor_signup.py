
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse
from passlib.context import CryptContext

from core.api_response import api_response
from db.models.superadmin import Config
from db.models.superadmin import VendorSignup
from db.sessions.database import get_db
from schemas.register import (
    VendorRegisterRequest,
    VendorRegisterResponse,
)

from services.admin_user import get_config_or_404
from services.vendor_user import validate_unique_user
from utils.email import send_welcome_email
from utils.exception_handlers import exception_handler
from utils.file_uploads import (
    get_media_url,
)
from utils.id_generators import encrypt_data, generate_lower_uppercase, hash_data, random_token

router = APIRouter()


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


@router.post(
    "/register",
    response_model=VendorRegisterResponse,
    status_code=status.HTTP_201_CREATED,
)

async def register_user(
    background_tasks: BackgroundTasks,
    user_data: VendorRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:

    # Encrypt data for storage
    encrypted_username = encrypt_data(user_data.username)
    encrypted_email = encrypt_data(user_data.email)


    email_hash = hash_data(user_data.email)

    # Check uniqueness using hashes
    unique_user_result = await validate_unique_user(db, email_hash)
    if unique_user_result is not None:
        return unique_user_result

    # Get system configuration
    config_result = await get_config_or_404(db)
    if not isinstance(config_result, Config):
        return config_result

    config = config_result

    signup_id = generate_lower_uppercase(length=6)
    email_token = random_token()
    hashed_password = hash_password(user_data.password)

    new_user = VendorSignup(
        signup_id=signup_id,
        name=encrypted_username,
       
        password=hashed_password,
        email=encrypted_email,
        email_hash=email_hash,
        category=user_data.category,
        email_token=email_token,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    logo_url = get_media_url(config.logo_url or "") or ""

    background_tasks.add_task(
        send_welcome_email,
        email=user_data.email,
        username=user_data.username,
        password=config.default_password,
        logo_url=logo_url,
    )

    return api_response(
        status_code=status.HTTP_201_CREATED,
        message="User registered successfully. Welcome email sent in background.",
        data=VendorRegisterResponse(
            signup_id=signup_id,
            email=user_data.email,
            username=user_data.username,
            category=user_data.category,
        ),
    )
