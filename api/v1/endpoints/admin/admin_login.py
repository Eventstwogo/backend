from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from passlib.context import CryptContext

from utils.id_generators import hash_data
from db.models.superadmin import AdminUser, Config
from schemas.admin_user import AdminLoginRequest, AdminLoginResponse
from db.sessions.database import get_db
from utils.jwt import create_access_token

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
router = APIRouter()

MAX_LOGIN_ATTEMPTS = 5

@router.post("/login", response_model=AdminLoginResponse)
async def login_user(
    login_data: AdminLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    
    # Convert email to lowercase for case-insensitive comparison
    email_hash = hash_data(login_data.email.strip().lower())
    # Find user by username or email
    stmt = select(AdminUser).where(
        AdminUser.email_hash == email_hash
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Compare password
    if not pwd_context.verify(login_data.password, user.password):
        user.login_attempts += 1
        await db.commit()
        raise HTTPException(status_code=401, detail="Incorrect password")
    
    # Check if account is locked
    if user.login_status == 1:
        raise HTTPException(status_code=423, detail="Account is locked. Try after 24 hours.")
    
    if user.login_status == -1:
        raise HTTPException(status_code=403, detail="Initial login detected. Please change your password.")

    if user.is_active:
        raise HTTPException(status_code=403, detail="Account is in inactive state")

    # Reset attempts, update login time, set to active
    user.login_attempts = user.login_attempts + 1 if user.login_attempts is not None else 0
    user.login_status = 0  # Set to active
    user.last_login = datetime.utcnow()
    await db.commit()
    
    # Create JWT token
    token_data = {
        "uid": user.user_id,
        "rid": user.role_id,
    }
    access_token = create_access_token(data=token_data)

    return AdminLoginResponse(
        access_token=access_token,
        message= "Login successful"

    )
