from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from passlib.context import CryptContext

from db.models.superadmin import AdminUser
from schemas.admin_user import UpdatePasswordBody, UpdatePasswordResponse
from db.sessions.database import get_db

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.post("/update-password", response_model=UpdatePasswordResponse)
async def update_password(
    user_id: str = Query(..., description="User ID"),
    body: UpdatePasswordBody = Depends(),
    db: AsyncSession = Depends(get_db),
):
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
    user.days_180_timestamp = datetime.utcnow()  # Optional: password rotation tracking

    await db.commit()

    return UpdatePasswordResponse(message="Password updated successfully.")
