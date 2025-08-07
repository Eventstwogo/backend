
from fastapi import status, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.responses import JSONResponse

from core.api_response import api_response
from db.models.superadmin import Category, Config, VendorSignup, VendorLogin, BusinessProfile, Role
from schemas.vendor_details import VendorProfilePictureUploadResponse, VendorUserDetailResponse


async def validate_unique_user(db: AsyncSession, email_hash: str):
    # First check if email exists in ven_signup table
    signup_result = await db.execute(
        select(VendorSignup).where(VendorSignup.email_hash == email_hash)
    )
    existing_signup_user = signup_result.scalar_one_or_none()

    if existing_signup_user:
        return api_response(
            status_code=status.HTTP_409_CONFLICT,
            message="Vendor user with given email already exists.",
        )
    
    # Then check if email exists in ven_login table
    login_result = await db.execute(
        select(VendorLogin).where(VendorLogin.email_hash == email_hash)
    )
    existing_login_user = login_result.scalar_one_or_none()

    if existing_login_user:
        return api_response(
            status_code=status.HTTP_409_CONFLICT,
            message="Vendor employee already exists with given email.",
        )



async def validate_category(db: AsyncSession, category_id: str) -> JSONResponse | Category:
    category_query = await db.execute(select(Category).where(Category.category_id == category_id))
    category = category_query.scalar_one_or_none()
    if not category:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="ategory not found.",
            log_error=True,
        )
    if category.category_status:
        return api_response(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Category is inactive.",
            log_error=True,
        )
    return category


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


async def get_vendor_user_by_id(db: AsyncSession, user_id: str) -> JSONResponse | VendorLogin:
    """Get vendor user by ID"""
    result = await db.execute(
        select(VendorLogin).where(VendorLogin.user_id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Vendor user not found.",
            log_error=True,
        )
    
    return user


async def upload_vendor_profile_picture(
    db: AsyncSession, 
    user_id: str, 
    file: UploadFile
) -> JSONResponse | VendorProfilePictureUploadResponse:
    """
    Upload profile picture for a vendor user.
    
    Args:
        db: Database session
        user_id: Vendor user ID
        file: Uploaded file
        
    Returns:
        VendorProfilePictureUploadResponse or JSONResponse with error
    """
    from utils.file_uploads import save_uploaded_file, get_media_url, remove_file_if_exists
    from core.config import settings
    from utils.id_generators import decrypt_data
    
    # Get the user
    user = await get_vendor_user_by_id(db, user_id)
    if isinstance(user, JSONResponse):
        return user
    
    try:
        # Remove old profile picture if exists
        if user.profile_pic:
            await remove_file_if_exists(user.profile_pic)
        
        # Upload new profile picture
        upload_path = settings.PROFILE_PICTURE_UPLOAD_PATH.format(username=user.user_id)
        relative_path = await save_uploaded_file(file, upload_path)
        
        # Update user's profile picture in database
        user.profile_pic = relative_path
        await db.commit()
        
        # Get the full URL for response
        profile_picture_url = get_media_url(relative_path)
        
        return VendorProfilePictureUploadResponse(
            user_id=user_id,
            profile_picture_url=profile_picture_url,
            message="Profile picture uploaded successfully."
        )
        
    except Exception as e:
        await db.rollback()
        import traceback
        error_details = traceback.format_exc()
        print(f"Profile picture upload error: {error_details}")  # For debugging
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to upload profile picture: {str(e)}",
            log_error=True,
        )


async def get_vendor_user_details(
    db: AsyncSession, 
    user_id: str
) -> JSONResponse | VendorUserDetailResponse:
    """
    Get detailed information about a vendor user by ID.
    
    Args:
        db: Database session
        user_id: Vendor user ID
        
    Returns:
        VendorUserDetailResponse or JSONResponse with error
    """
    from utils.file_uploads import get_media_url
    from utils.id_generators import decrypt_data
    
    # Get the user first without relationships to test basic query
    result = await db.execute(
        select(VendorLogin).where(VendorLogin.user_id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Vendor user not found.",
            log_error=True,
        )
    
    try:
        # Decrypt sensitive data
        try:
            decrypted_username = decrypt_data(user.username) if user.username != "unknown" else "Unknown User"
        except Exception:
            decrypted_username = user.username  # Use as-is if decryption fails
            
        decrypted_email = decrypt_data(user.email)
        
        # Get store name from business profile (null for employees)
        store_name = None
        if user.business_profile_id:
            # Query business profile separately
            business_result = await db.execute(
                select(BusinessProfile).where(BusinessProfile.profile_ref_id == user.business_profile_id)
            )
            business_profile = business_result.scalar_one_or_none()
            if business_profile:
                store_name = business_profile.store_name
        
        # Get role name
        role_name = None
        role_id = user.role
        if user.role:
            # Query role separately
            role_result = await db.execute(
                select(Role).where(Role.role_id == user.role)
            )
            role = role_result.scalar_one_or_none()
            if role:
                role_name = role.role_name
        
        # Get profile picture URL if exists
        profile_picture_url = get_media_url(user.profile_pic) if user.profile_pic else None
        
        return VendorUserDetailResponse(
            user_id=user.user_id,
            username=decrypted_username,
            email=decrypted_email,
            store_name=store_name,
            role_id=role_id,
            role=role_name,
            profile_picture_url=profile_picture_url
        )
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Get vendor user details error: {error_details}")  # For debugging
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to retrieve vendor user details: {str(e)}",
            log_error=True,
        )