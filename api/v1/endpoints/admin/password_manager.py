from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from passlib.context import CryptContext

from utils.auth import hash_password
from utils.validations import validate_password
from core.status_codes import APIResponse, StatusCode
from db.models.superadmin import AdminUser
from schemas.admin_user import AdminResetPassword, UpdatePasswordBody, UpdatePasswordResponse
from db.sessions.database import get_db

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.post("/update-password", response_model=UpdatePasswordResponse)
async def update_password(
    user_id: str = Query(..., description="User ID"),
    body: UpdatePasswordBody = Depends(),
    db: AsyncSession = Depends(get_db),
)-> JSONResponse:
    # Fetch user by user_id
    stmt = select(AdminUser).where(AdminUser.user_id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    # Verify old password
    if not pwd_context.verify(body.old_password, user.password):
        raise HTTPException(status_code=401, detail="Old password is incorrect.")

    # Hash and update password
    user.password = pwd_context.hash(body.new_password)
    user.login_status = 0
    user.login_attempts = 0
    user.updated_at = datetime.utcnow()
    user.days_180_timestamp = datetime.utcnow() 

    await db.commit()

    return UpdatePasswordResponse(message="Password updated successfully.")




@router.put("/api/v1/forgot-password/")
async def forgot_password(
    email_token: str,
    data: AdminResetPassword,
    db: AsyncSession = Depends(get_db),
)-> JSONResponse:
    try:
        new_password = data.new_password.strip()
        confirm_new_password = data.confirm_new_password.strip()

        if new_password != confirm_new_password:
            return APIResponse.response(StatusCode.BAD_REQUEST, "Passwords do not match")

        result = await db.execute(
            select(AdminUser).where(AdminUser.email_hash == email_token)
        )
        user = result.scalar_one_or_none()

        if not user:
            return APIResponse.response(StatusCode.NOT_FOUND, "Invalid or expired token")

        validate_password(new_password, user.days_180_flag)

        hashed_password = hash_password(new_password)
        user.password = hashed_password
        user.updated_at = datetime.now(timezone.utc)
        user.email_hash = None  # Clear token after use

        await db.commit()

        return APIResponse.response(StatusCode.SUCCESS, "Password reset successful")

    except Exception as e:
        return APIResponse.response(
            StatusCode.SERVER_ERROR, f"Internal server error: {str(e)}", log_error=True
        )




# @router.put("/api/v1/change-password/")
# async def change_password(
#     user_id: str,
#     data: AdminResetPassword,
#     db: AsyncSession = Depends(get_db),
# ):
#     try:
#         new_password = data.new_password.strip()
#         confirm_new_password = data.confirm_new_password.strip()

#         if new_password != confirm_new_password:
#             return APIResponse.response(StatusCode.BAD_REQUEST, "Passwords do not match")

#         result = await db.execute(
#             select(AdminUser).where(AdminUser.user_id == user_id)
#         )
#         user = result.scalar_one_or_none()

#         if not user:
#             return APIResponse.response(StatusCode.NOT_FOUND, "Invalid user")

#         validate_password(new_password, user.days_180_flag)

#         hashed_password = hash_password(new_password)
#         user.password = hashed_password
#         user.updated_at = datetime.now(timezone.utc)

#         await db.commit()

#         return APIResponse.response(StatusCode.SUCCESS, "Password updated successfully")

#     except Exception as e:
#         return APIResponse.response(
#             StatusCode.SERVER_ERROR, f"Internal server error: {str(e)}", log_error=True
#         )
