from datetime import datetime, timedelta, timezone

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from core.api_response import api_response
from core.config import PRIVATE_KEY, settings
from db.models.superadmin import AdminUser
from utils.auth import create_jwt_token, verify_password


async def fetch_user_by_email(db: AsyncSession, email: str) -> AdminUser | None:
    result = await db.execute(select(AdminUser).where(AdminUser.email == email))
    return result.scalar_one_or_none()


def account_not_found() -> JSONResponse:
    return api_response(
        status_code=status.HTTP_404_NOT_FOUND,
        message="Account not found.",
        log_error=True,
    )


def account_deactivated() -> JSONResponse:
    return api_response(
        status_code=status.HTTP_404_NOT_FOUND,
        message="Account is deactivated. Please contact support.",
        log_error=True,
    )


async def check_account_lock(
    user: AdminUser, db: AsyncSession
) -> JSONResponse | None:
    if user.login_status == 1:
        return api_response(
            status_code=status.HTTP_423_LOCKED,
            message="Account is locked. Try after 24 hours.",
            log_error=True,
        )
    return None


async def check_password(
    user: AdminUser, password: str, db: AsyncSession
) -> JSONResponse | None:
    if not verify_password(password, user.password_hash):
        user.login_attempts += 1
        if user.login_attempts >= 3:
            user.login_status = 1
            user.last_login = datetime.now(timezone.utc)
            await db.commit()
            return api_response(
                status_code=status.HTTP_423_LOCKED,
                message="Account locked after 3 failed login attempts. Try again after 24 hours.",
                log_error=True,
            )
        await db.commit()
        return api_response(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message="Invalid credentials.",
            log_error=True,
        )
    return None


def initial_login_response(user: AdminUser) -> JSONResponse:
    return api_response(
        status_code=status.HTTP_201_CREATED,
        message="Initial login detected. Please reset your password.",
        data={"user_id": user.user_id, "email": user.email},
    )


async def check_password_expiry(user: AdminUser, now: datetime) -> bool:
    if user.days_180_flag:
        if user.days_180_timestamp:
            if (now - user.days_180_timestamp).days >= 180:
                user.login_status = 1  # Lock account for password expiry
                return True
        else:
            user.days_180_timestamp = now
    return False


def generate_token(user: AdminUser) -> str:
    return create_jwt_token(
        data={"user_id": user.user_id, "role_id": user.role_id},
        private_key=PRIVATE_KEY.get_secret_value(),
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_SECONDS,
        issuer=settings.JWT_ISSUER,
        audience=settings.JWT_AUDIENCE,
    )


def password_expired_response(user: AdminUser, token: str) -> JSONResponse:
    return api_response(
        status_code=status.HTTP_409_CONFLICT,
        message="Password expired. Please update your password.",
        data={
            "user_id": user.user_id,
            "email": user.email,
            "access_token": token,
        },
    )


def login_success_response(user: AdminUser, token: str) -> JSONResponse:
    return api_response(
        status_code=status.HTTP_200_OK,
        message="Login successful.",
        data={
            "user_id": user.user_id,
            "email": user.email,
            "access_token": token,
        },
    )
