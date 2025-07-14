from datetime import datetime, timedelta, timezone
from typing import Any, Sequence, Tuple

from fastapi import status
from sqlalchemy import case, func, select
from sqlalchemy.engine.row import Row
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from core.api_response import api_response
from db.models.superadmin import AdminUser, Config, Role

async def get_admin_user_analytics(
    db: AsyncSession,
) -> Row[Tuple[int, Any, Any, Any, Any, Any, Any, datetime, datetime]]:
    now = datetime.now(timezone.utc)
    threshold_180 = now - timedelta(days=180)

    results = await db.execute(
        select(
            func.count().label("total_users"),
            func.sum(case((AdminUser.is_active.is_(False), 1), else_=0)).label(
                "active_users"
            ),
            func.sum(case((AdminUser.is_active.is_(True), 1), else_=0)).label(
                "inactive_users"
            ),
            func.sum(case((AdminUser.login_status == 1, 1), else_=0)).label(
                "locked_users"
            ),
            func.sum(
                case((AdminUser.days_180_flag.is_(True), 1), else_=0)
            ).label("with_expiry_flag"),
            func.sum(
                case(
                    (
                        AdminUser.days_180_flag.is_(True),
                        case(
                            (AdminUser.days_180_timestamp < threshold_180, 1),
                            else_=0,
                        ),
                    ),
                    else_=0,
                )
            ).label("expired_passwords"),
            func.sum(case((AdminUser.login_attempts >= 3, 1), else_=0)).label(
                "high_failed_attempts"
            ),
            func.min(AdminUser.created_at).label("earliest_user"),
            func.max(AdminUser.created_at).label("latest_user"),
        )
    )
    return results.one()


async def get_daily_registrations(
    db: AsyncSession, days: int = 30
) -> Sequence[Row[Tuple[Any, int]]]:
    start = datetime.now(timezone.utc) - timedelta(days=days)
    results = await db.execute(
        select(
            func.date(AdminUser.created_at).label("date"),
            func.count().label("count"),
        )
        .where(AdminUser.created_at >= start)
        .group_by(func.date(AdminUser.created_at))
        .order_by(func.date(AdminUser.created_at))
    )
    return results.all()


async def validate_unique_user(
    db: AsyncSession, email_hash: str
) -> JSONResponse | None:
    user_query = await db.execute(
        select(AdminUser).where(AdminUser.email_hash == email_hash)
        
    )
    if user_query.scalar_one_or_none():
        return api_response(
            status_code=status.HTTP_409_CONFLICT,
            message="User with the given email already exists.",
            log_error=True,
        )
    return None


async def validate_role(db: AsyncSession, role_id: str) -> JSONResponse | Role:
    role_query = await db.execute(select(Role).where(Role.role_id == role_id))
    role = role_query.scalar_one_or_none()
    if not role:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Role not found.",
            log_error=True,
        )
    if role.role_status:
        return api_response(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Role is inactive.",
            log_error=True,
        )
    return role




async def validate_superadmin_uniqueness(
    db: AsyncSession, role: Role
) -> JSONResponse | None:
    if role.role_name.lower() in {"superadmin", "super admin"}:
        superadmin_query = await db.execute(
            select(AdminUser).where(AdminUser.role_id == role.role_id)
        )
        if superadmin_query.scalar_one_or_none():
            return api_response(
                status_code=status.HTTP_409_CONFLICT,
                message=(
                    "Super Admin already exists. Only one Super Admin is allowed. "
                    "Please register with a different role."
                ),
                log_error=True,
            )
    return None


async def get_config_or_404(
    db: AsyncSession,
) -> JSONResponse | Config:
    config_result = await db.execute(select(Config).limit(1))
    config = config_result.scalar_one_or_none()
    if not config:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Configuration not found.",
            log_error=True,
        )
    if not config.default_password_hash:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Default password hash not set in configuration.",
            log_error=True,
        )
    return config


async def get_user_by_id(
    db: AsyncSession, user_id: str
) -> JSONResponse | AdminUser:
    """Find a user by ID and return either the user or an error response"""
    result = await db.execute(
        select(AdminUser).where(AdminUser.user_id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found.",
            log_error=True,
        )
    return user


async def get_user_by_email(
    db: AsyncSession, email: str
) -> JSONResponse | AdminUser:
    """Find a user by email and return either the user or an error response"""
    result = await db.execute(select(AdminUser).where(AdminUser.email == email))
    user = result.scalar_one_or_none()
    if not user:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found.",
            log_error=True,
        )
    return user
