from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Sequence, Tuple

from fastapi import status
from sqlalchemy import case, func, select, or_, and_
from sqlalchemy.engine.row import Row
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.responses import JSONResponse

from core.api_response import api_response
from db.models.superadmin import AdminUser, Config, Role
from schemas.admin_user import AdminUser as AdminUserSchema, PaginatedAdminListResponse
from utils.id_generators import decrypt_data, hash_data

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
    # Note: Removed default_password_hash validation since admin users now use random passwords
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
    # Convert email to lowercase and hash it for lookup since emails are stored encrypted
    # and email_hash is used for searches
    normalized_email = email.strip().lower()
    email_hash = hash_data(normalized_email)
    result = await db.execute(select(AdminUser).where(AdminUser.email_hash == email_hash))
    user = result.scalar_one_or_none()
    if not user:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found.",
            log_error=True,
        )
    return user


async def get_all_admin_users(
    db: AsyncSession,
    page: int = 1,
    per_page: int = 10,
    search: Optional[str] = None,
    role_id: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> JSONResponse | PaginatedAdminListResponse:
    try:
        # Calculate offset
        offset = (page - 1) * per_page
        
        # Build base query
        query = select(AdminUser).options(selectinload(AdminUser.role))
        count_query = select(func.count(AdminUser.user_id))
        
        # Apply filters
        conditions = []
        
        if search:
            # Since username and email are encrypted, we need to search differently
            # For now, we'll get all users and filter in Python (not ideal for large datasets)
            # In production, you might want to add a searchable field or use full-text search
            pass  # We'll handle search after fetching
            
        if role_id:
            conditions.append(AdminUser.role_id == role_id)
            
        if is_active is not None:
            conditions.append(AdminUser.is_active == is_active)
        
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))
        
        # Get total count
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # If search is provided, we need to handle it differently due to encryption
        if search:
            # Get all matching users first (without pagination)
            all_users_result = await db.execute(query)
            all_users = all_users_result.scalars().all()
            
            # Filter by search term after decryption
            filtered_users = []
            search_lower = search.lower()
            
            for user in all_users:
                try:
                    decrypted_username = decrypt_data(user.username).lower()
                    decrypted_email = decrypt_data(user.email).lower()
                    
                    if search_lower in decrypted_username or search_lower in decrypted_email:
                        filtered_users.append(user)
                except Exception:
                    # Skip users with decryption issues
                    continue
            
            # Update total count for search results
            total = len(filtered_users)
            
            # Apply pagination to filtered results
            users = filtered_users[offset:offset + per_page]
        else:
            # Apply pagination to query
            query = query.offset(offset).limit(per_page).order_by(AdminUser.created_at.desc())
            
            # Execute query
            result = await db.execute(query)
            users = result.scalars().all()
        
        # Convert to response schema
        admin_users = []
        for user in users:
            try:
                # Decrypt sensitive data
                decrypted_username = decrypt_data(user.username)
                decrypted_email = decrypt_data(user.email)
                
                admin_user = AdminUserSchema(
                    user_id=user.user_id,
                    username=decrypted_username,
                    email=decrypted_email,
                    role_id=user.role_id,
                    created_at=user.created_at,
                    is_active=user.is_active,
                )
                admin_users.append(admin_user)
            except Exception as e:
                # Log the error but continue with other users
                print(f"Error decrypting user data for user_id {user.user_id}: {e}")
                continue
        
        return PaginatedAdminListResponse(
            total=total,
            page=page,
            per_page=per_page,
            admins=admin_users,
        )
        
    except Exception as e:
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to retrieve admin users: {str(e)}",
            log_error=True,
        )
