from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Sequence, Tuple
from datetime import datetime, timezone
from fastapi import status
from sqlalchemy import case, func, select, or_, and_, update
from sqlalchemy.engine.row import Row
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.responses import JSONResponse

from core.api_response import api_response
from db.models.superadmin import AdminUser, Config, Role
from schemas.admin_user import (
    AdminUser as AdminUserSchema,
    AdminUserDetailResponse, 
    PaginatedAdminListResponse,
    AdminListResponse,
    AdminUpdateRequest,
    AdminUpdateResponse,
    AdminDeleteResponse,
    AdminRestoreResponse
)
from utils.id_generators import decrypt_data, hash_data, encrypt_data
from fastapi import UploadFile
from schemas.admin_user import AdminProfilePictureUploadResponse
from utils.file_uploads import save_uploaded_file, remove_file_if_exists, get_media_url
from core.config import settings

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
        
        if role_id:
            conditions.append(AdminUser.role_id == role_id)
            
        if is_active is not None:
            conditions.append(AdminUser.is_active == is_active)
        
        # Apply conditions only if any exist
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))
        
        # If search is provided, we need to handle it differently due to encryption
        if search:
            # Get all matching users first (without pagination) for search
            search_query = query
            all_users_result = await db.execute(search_query)
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
            # Get total count first
            total_result = await db.execute(count_query)
            total = total_result.scalar()
            
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


async def get_all_admin_users_excluding_superadmin(
    db: AsyncSession,
) -> JSONResponse | AdminListResponse:
    """Get all admin users excluding superadmin users"""
    try:
        # Build query to get all admin users with their roles
        query = select(AdminUser).options(selectinload(AdminUser.role))
        
        # Execute query to get all users
        result = await db.execute(query)
        all_users = result.scalars().all()
        
        # Filter out superadmin users
        filtered_users = []
        for user in all_users:
            try:
                # Check if user's role is not superadmin
                if user.role and user.role.role_name.lower() not in {"superadmin", "super admin"}:
                    filtered_users.append(user)
            except Exception:
                # Skip users with issues
                continue
        
        # Convert to response schema
        admin_users = []
        for user in filtered_users:
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
        
        return AdminListResponse(admins=admin_users)
        
    except Exception as e:
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to retrieve admin users: {str(e)}",
            log_error=True,
        )


async def validate_unique_username_email_for_update(
    db: AsyncSession, 
    user_id: str, 
    username: Optional[str] = None, 
    email: Optional[str] = None
) -> JSONResponse | None:
    """Validate that username and email are unique when updating a user"""
    conditions = []
    
    if username:
        encrypted_username = encrypt_data(username)
        conditions.append(AdminUser.username == encrypted_username)
    
    if email:
        email_hash = hash_data(email.lower())
        conditions.append(AdminUser.email_hash == email_hash)
    
    if not conditions:
        return None
    
    # Check if any other user (excluding current user) has the same username or email
    query = select(AdminUser).where(
        and_(
            AdminUser.user_id != user_id,
            or_(*conditions)
        )
    )
    
    result = await db.execute(query)
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        if username and existing_user.username == encrypt_data(username):
            return api_response(
                status_code=status.HTTP_409_CONFLICT,
                message="Username already exists.",
                log_error=True,
            )
        if email and existing_user.email_hash == hash_data(email.lower()):
            return api_response(
                status_code=status.HTTP_409_CONFLICT,
                message="Email already exists.",
                log_error=True,
            )
    
    return None


async def validate_superadmin_role_change(
    db: AsyncSession, 
    user_id: str, 
    new_role_id: str
) -> JSONResponse | None:
    """Validate superadmin role changes to ensure only one superadmin exists"""
    # Get the new role
    role_result = await validate_role(db, new_role_id)
    if isinstance(role_result, JSONResponse):
        return role_result
    
    new_role = role_result
    
    # If changing to superadmin role, check if another superadmin exists
    if new_role.role_name.lower() in {"superadmin", "super admin"}:
        existing_superadmin_query = await db.execute(
            select(AdminUser).where(
                and_(
                    AdminUser.role_id == new_role_id,
                    AdminUser.user_id != user_id,
                    AdminUser.is_active == False  # is_active=False means active
                )
            )
        )
        if existing_superadmin_query.scalar_one_or_none():
            return api_response(
                status_code=status.HTTP_409_CONFLICT,
                message="Super Admin already exists. Only one Super Admin is allowed.",
                log_error=True,
            )
    
    # If changing from superadmin role, ensure there will still be at least one superadmin
    current_user_result = await get_user_by_id(db, user_id)
    if isinstance(current_user_result, JSONResponse):
        return current_user_result
    
    current_user = current_user_result
    current_role_query = await db.execute(
        select(Role).where(Role.role_id == current_user.role_id)
    )
    current_role = current_role_query.scalar_one_or_none()
    
    if (current_role and 
        current_role.role_name.lower() in {"superadmin", "super admin"} and
        new_role.role_name.lower() not in {"superadmin", "super admin"}):
        
        # Check if there are other active superadmins
        other_superadmins_query = await db.execute(
            select(AdminUser).where(
                and_(
                    AdminUser.role_id == current_role.role_id,
                    AdminUser.user_id != user_id,
                    AdminUser.is_active == False  # is_active=False means active
                )
            )
        )
        if not other_superadmins_query.scalar_one_or_none():
            return api_response(
                status_code=status.HTTP_409_CONFLICT,
                message="Cannot change role. At least one active Super Admin must exist.",
                log_error=True,
            )
    
    return None


async def update_admin_user(
    db: AsyncSession, 
    user_id: str, 
    update_data: AdminUpdateRequest
) -> JSONResponse | AdminUpdateResponse:
    """Update an admin user"""
    # Get the user
    user_result = await get_user_by_id(db, user_id)
    if isinstance(user_result, JSONResponse):
        return user_result
    
    user = user_result
    
    # Check if user is inactive (soft deleted)
    if user.is_active == True:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found or has been deleted.",
            log_error=True,
        )
    
    # Validate uniqueness for username and email
    uniqueness_error = await validate_unique_username_email_for_update(
        db, user_id, update_data.username, update_data.email
    )
    if uniqueness_error:
        return uniqueness_error
    
    # Validate role change if role_id is being updated
    if update_data.role_id:
        role_error = await validate_superadmin_role_change(db, user_id, update_data.role_id)
        if role_error:
            return role_error
    
    try:
        # Prepare update data
        update_values = {"updated_at": datetime.now(timezone.utc)}
        
        if update_data.username:
            # Capitalize first letter of username
            capitalized_username = update_data.username.strip().capitalize()
            update_values["username"] = encrypt_data(capitalized_username)
        
        if update_data.email:
            normalized_email = update_data.email.lower()
            update_values["email"] = encrypt_data(normalized_email)
            update_values["email_hash"] = hash_data(normalized_email)
        
        if update_data.role_id:
            update_values["role_id"] = update_data.role_id
        
        # Update the user
        await db.execute(
            update(AdminUser)
            .where(AdminUser.user_id == user_id)
            .values(**update_values)
        )
        await db.commit()
        
        # Get updated user data
        updated_user_result = await get_user_by_id(db, user_id)
        if isinstance(updated_user_result, JSONResponse):
            return updated_user_result
        
        updated_user = updated_user_result
        
        return AdminUpdateResponse(
            user_id=updated_user.user_id,
            username=decrypt_data(updated_user.username),
            email=decrypt_data(updated_user.email),
            role_id=updated_user.role_id,
            message="Admin user updated successfully."
        )
        
    except Exception as e:
        await db.rollback()
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to update admin user: {str(e)}",
            log_error=True,
        )


async def soft_delete_admin_user(
    db: AsyncSession, 
    user_id: str
) -> JSONResponse | AdminDeleteResponse:
    """Soft delete an admin user"""
    # Get the user
    user_result = await get_user_by_id(db, user_id)
    if isinstance(user_result, JSONResponse):
        return user_result
    
    user = user_result
    
    # Check if user is already inactive (soft deleted)
    if user.is_active == True:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found or has already been deleted.",
            log_error=True,
        )
    
    # Check if user is a superadmin and if there are other active superadmins
    role_query = await db.execute(
        select(Role).where(Role.role_id == user.role_id)
    )
    role = role_query.scalar_one_or_none()
    
    if role and role.role_name.lower() in {"superadmin", "super admin"}:
        # Check if there are other active superadmins
        other_superadmins_query = await db.execute(
            select(AdminUser).where(
                and_(
                    AdminUser.role_id == user.role_id,
                    AdminUser.user_id != user_id,
                    AdminUser.is_active == False  # is_active=False means active
                )
            )
        )
        if not other_superadmins_query.scalar_one_or_none():
            return api_response(
                status_code=status.HTTP_409_CONFLICT,
                message="Cannot delete the last active Super Admin.",
                log_error=True,
            )
    
    try:
        # Soft delete the user (set is_active to True, meaning inactive)
        await db.execute(
            update(AdminUser)
            .where(AdminUser.user_id == user_id)
            .values(
                is_active=True,
                updated_at=datetime.now(timezone.utc)
            )
        )
        await db.commit()
        
        return AdminDeleteResponse(
            user_id=user_id,
            message="Admin user deleted successfully."
        )
        
    except Exception as e:
        await db.rollback()
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to delete admin user: {str(e)}",
            log_error=True,
        )


async def restore_admin_user(
    db: AsyncSession, 
    user_id: str
) -> JSONResponse | AdminRestoreResponse:
    """Restore a soft deleted admin user"""
    # Get the user (including soft deleted ones)
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
    
    # Check if user is not inactive (not soft deleted)
    if user.is_active == False:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="User is not deleted and cannot be restored.",
            log_error=True,
        )
    
    # Check for username and email conflicts with active users
    decrypted_username = decrypt_data(user.username)
    decrypted_email = decrypt_data(user.email)
    
    conflict_error = await validate_unique_username_email_for_update(
        db, user_id, decrypted_username, decrypted_email
    )
    if conflict_error:
        return api_response(
            status_code=status.HTTP_409_CONFLICT,
            message="Cannot restore user. Username or email conflicts with existing active user.",
            log_error=True,
        )
    
    try:
        # Restore the user (set is_active to False, meaning active)
        await db.execute(
            update(AdminUser)
            .where(AdminUser.user_id == user_id)
            .values(
                is_active=False,
                updated_at=datetime.now(timezone.utc)
            )
        )
        await db.commit()
        
        return AdminRestoreResponse(
            user_id=user_id,
            message="Admin user restored successfully."
        )
        
    except Exception as e:
        await db.rollback()
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to restore admin user: {str(e)}",
            log_error=True,
        )


async def hard_delete_admin_user(
    db: AsyncSession, 
    user_id: str
) -> JSONResponse | AdminDeleteResponse:
    """Permanently delete an admin user"""
    # Get the user (including soft deleted ones)
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
    
    # Check if user is an active superadmin and if there are other active superadmins
    if user.is_active == False:  # User is active (is_active=False means active)
        role_query = await db.execute(
            select(Role).where(Role.role_id == user.role_id)
        )
        role = role_query.scalar_one_or_none()
        
        if role and role.role_name.lower() in {"superadmin", "super admin"}:
            # Check if there are other active superadmins
            other_superadmins_query = await db.execute(
                select(AdminUser).where(
                    and_(
                        AdminUser.role_id == user.role_id,
                        AdminUser.user_id != user_id,
                        AdminUser.is_active == False  # is_active=False means active
                    )
                )
            )
            if not other_superadmins_query.scalar_one_or_none():
                return api_response(
                    status_code=status.HTTP_409_CONFLICT,
                    message="Cannot delete the last active Super Admin.",
                    log_error=True,
                )
    
    try:
        # Hard delete the user
        await db.delete(user)
        await db.commit()
        
        return AdminDeleteResponse(
            user_id=user_id,
            message="Admin user permanently deleted."
        )
        
    except Exception as e:
        await db.rollback()
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to permanently delete admin user: {str(e)}",
            log_error=True,
        )


async def get_admin_user_details(
    db: AsyncSession, 
    user_id: str
) -> JSONResponse | AdminUserDetailResponse:
    """
    Get detailed information about an admin user by ID.
    
    Args:
        db: Database session
        user_id: Admin user ID
        
    Returns:
        AdminUserDetailResponse or JSONResponse with error
    """
    from schemas.admin_user import AdminUserDetailResponse
    from utils.file_uploads import get_media_url
    from utils.id_generators import decrypt_data
    
    # Get the user with role information
    result = await db.execute(
        select(AdminUser).options(selectinload(AdminUser.role)).where(AdminUser.user_id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found.",
            log_error=True,
        )
    
    try:
        # Decrypt sensitive data
        decrypted_username = decrypt_data(user.username)
        decrypted_email = decrypt_data(user.email)
        
        # Get profile picture URL if exists
        profile_picture_url = get_media_url(user.profile_picture) if user.profile_picture else None
        
        # Format dates as dd-mm-yyyy
        # Get join date - use created_at if available, otherwise try updated_at, or use current date as fallback
        
        join_date_raw = user.created_at if user.created_at else user.updated_at
        if not join_date_raw:
            # If both are None, use current date as fallback (this shouldn't happen for new users)
            print("DEBUG: Both created_at and updated_at are None, using current date")
            join_date_raw = datetime.now(timezone.utc)
        
        join_date = join_date_raw.strftime("%d-%m-%Y") if join_date_raw else None
        print(f"DEBUG: final join_date = {join_date}")

        return AdminUserDetailResponse(
            user_id=user.user_id,
            username=decrypted_username,
            email=decrypted_email,
            role_id=user.role_id,
            role_name=user.role.role_name if user.role else "Unknown",
            profile_picture_url=profile_picture_url,
            is_active=user.is_active,
            join_date=join_date,
        )
        
    except Exception as e:
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to retrieve user details: {str(e)}",
            log_error=True,
        )


async def upload_admin_profile_picture(
    db: AsyncSession, 
    user_id: str, 
    file: "UploadFile"
) -> JSONResponse | AdminProfilePictureUploadResponse:
    """
    Upload profile picture for an admin user.
    
    Args:
        db: Database session
        user_id: Admin user ID
        file: Uploaded file
        
    Returns:
        AdminProfilePictureUploadResponse or JSONResponse with error
    """

    
    # Get the user
    user = await get_user_by_id(db, user_id)
    if isinstance(user, JSONResponse):
        return user
    
    try:
        # Remove old profile picture if exists
        if user.profile_picture:
            await remove_file_if_exists(user.profile_picture)
        
        # Upload new profile picture
        upload_path = settings.PROFILE_PICTURE_UPLOAD_PATH.format(username=user.username)
        relative_path = await save_uploaded_file(file, upload_path)
        
        # Update user's profile picture in database
        user.profile_picture = relative_path
        await db.commit()
        
        # Get the full URL for response
        profile_picture_url = get_media_url(relative_path)
        
        return AdminProfilePictureUploadResponse(
            user_id=user_id,
            profile_picture_url=profile_picture_url,
            message="Profile picture uploaded successfully."
        )
        
    except Exception as e:
        await db.rollback()
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to upload profile picture: {str(e)}",
            log_error=True,
        )
