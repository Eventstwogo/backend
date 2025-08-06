from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime
from passlib.context import CryptContext
from typing import Optional
from starlette.responses import JSONResponse
import math

from core.api_response import api_response
from utils.id_generators import generate_digits_letters, hash_data, encrypt_data, decrypt_data, generate_employee_business_profile_id
from db.models.superadmin import VendorLogin, Role, BusinessProfile, VendorSignup
from schemas.vendor_employee import (
    VendorEmployeeCreateRequest, 
    VendorEmployeeUpdateRequest,
)
from db.sessions.database import get_db
from utils.exception_handlers import exception_handler
from utils.email_utils import send_vendor_employee_credentials_email

def safe_decrypt_username(encrypted_username: str, fallback: str = None) -> str:
    """Safely decrypt username with fallback handling"""
    try:
        return decrypt_data(encrypted_username)
    except Exception:
        # If decryption fails, try to return a fallback or placeholder
        if fallback:
            return fallback
        return "[DECRYPTION_FAILED]"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
router = APIRouter()


@router.post("/create")
@exception_handler
async def create_vendor_employee(
    employee_data: VendorEmployeeCreateRequest,
    vendor_id: str = Query(..., description="Vendor ID to associate with the employee"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    # Validate vendor_id exists in VendorLogin table
    vendor_stmt = select(VendorLogin).where(VendorLogin.user_id == vendor_id)
    vendor_result = await db.execute(vendor_stmt)
    vendor = vendor_result.scalar_one_or_none()
    
    if not vendor:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"Vendor with ID '{vendor_id}' not found"
        )
    
    # Validate role_id exists and is active in Role table
    role_stmt = select(Role).where(Role.role_id == employee_data.role_id)
    role_result = await db.execute(role_stmt)
    role = role_result.scalar_one_or_none()
    
    if not role:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"Role with ID '{employee_data.role_id}' not found"
        )
    
    # Check if role is active (role_status = False means active)
    if role.role_status:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=f"Role '{role.role_name}' is inactive and cannot be assigned"
        )
    
    # Check if email already exists in ven_signup table
    email_hash_for_signup = hash_data(employee_data.email)
    signup_email_stmt = select(VendorSignup).where(VendorSignup.email_hash == email_hash_for_signup)
    signup_email_result = await db.execute(signup_email_stmt)
    existing_signup_email = signup_email_result.scalar_one_or_none()
    
    if existing_signup_email:
        return api_response(
            status_code=status.HTTP_409_CONFLICT,
            message=f"This email '{employee_data.email}' is already registered for vendor signup. Please try with another email."
        )
    
    # Check if username is unique and prepare username data
    encrypted_username = encrypt_data(employee_data.username)
    username_hash = hash_data(employee_data.username.lower())
    
    # Check uniqueness using username_hash (more efficient)
    username_stmt = select(VendorLogin).where(VendorLogin.username_hash == username_hash)
    username_result = await db.execute(username_stmt)
    existing_username = username_result.scalar_one_or_none()
    
    if existing_username:
        return api_response(
            status_code=status.HTTP_409_CONFLICT,
            message=f"Username '{employee_data.username}' is already taken"
        )
    
    # Check if email is unique and prepare email data
    encrypted_email = encrypt_data(employee_data.email)
    email_hash = hash_data(employee_data.email)
    email_stmt = select(VendorLogin).where(VendorLogin.email_hash == email_hash)
    email_result = await db.execute(email_stmt)
    existing_email = email_result.scalar_one_or_none()
    
    if existing_email:
        return api_response(
            status_code=status.HTTP_409_CONFLICT,
            message=f"Email '{employee_data.email}' is already registered"
        )
    
    # Generate unique IDs and password
    user_id = generate_digits_letters(6)
    generated_password = generate_digits_letters(6)
    
    # Ensure user_id is unique
    while True:
        user_check_stmt = select(VendorLogin).where(VendorLogin.user_id == user_id)
        user_check_result = await db.execute(user_check_stmt)
        if not user_check_result.scalar_one_or_none():
            break
        user_id = generate_digits_letters(6)
    
    # For employees, generate business_profile_id with format "sho" + 3 random digits
    # Ensure business_profile_id is unique
    while True:
        business_profile_id = generate_employee_business_profile_id()
        biz_check_stmt = select(VendorLogin).where(VendorLogin.business_profile_id == business_profile_id)
        biz_check_result = await db.execute(biz_check_stmt)
        if not biz_check_result.scalar_one_or_none():
            break
        # If the generated ID already exists, the loop will continue and generate a new one
    
    # Generate user_profile_id normally
    user_profile_id = generate_digits_letters(6)
    
    # Ensure user_profile_id is unique
    while True:
        user_prof_check_stmt = select(VendorLogin).where(VendorLogin.user_profile_id == user_profile_id)
        user_prof_check_result = await db.execute(user_prof_check_stmt)
        if not user_prof_check_result.scalar_one_or_none():
            break
        user_profile_id = generate_digits_letters(6)
    
    # Hash the generated password
    hashed_password = pwd_context.hash(generated_password)
    
    # Create new vendor employee login entry
    new_employee = VendorLogin(
        user_id=user_id,
        username=encrypted_username,
        username_hash=username_hash,
        email=encrypted_email,
        email_hash=email_hash,
        password=hashed_password,
        business_profile_id=business_profile_id,
        user_profile_id=user_profile_id,
        vendor_ref_id=vendor_id,
        role=employee_data.role_id,  # Assign the validated role_id
        is_verified=True,
        is_active=False,  # False means active
        login_attempts=0,
        login_failed_attempts=0,
        login_status=-1,  # -1 means initial password for employee
        timestamp=datetime.utcnow()
    )

    db.add(new_employee)
    await db.commit()
    await db.refresh(new_employee)
    
    # Send credentials email to the new employee
    try:
        # Get vendor business name from BusinessProfile if available
        vendor_business_name = None
        try:
            # Try to get business profile for the vendor
            business_profile_stmt = select(BusinessProfile).where(
                BusinessProfile.profile_ref_id == vendor.business_profile_id
            )
            business_profile_result = await db.execute(business_profile_stmt)
            business_profile = business_profile_result.scalar_one_or_none()
            
            if business_profile and business_profile.store_name:
                vendor_business_name = business_profile.store_name
            else:
                # Fallback to vendor username
                vendor_business_name = decrypt_data(vendor.username) if vendor.username else None
        except Exception:
            vendor_business_name = None
        
        email_sent = send_vendor_employee_credentials_email(
            email=employee_data.email,
            employee_name=employee_data.username,
            business_name=vendor_business_name or "Your Business",
            username=employee_data.username,
            password=generated_password,
            role_name=role.role_name if role else None,
        )
        
        if not email_sent:
            # Log the email failure but don't fail the employee creation
            print(f"Warning: Failed to send credentials email to {employee_data.email}")
            
    except Exception as e:
        # Log the email error but don't fail the employee creation
        print(f"Error sending credentials email: {str(e)}")
    
    return api_response(
        status_code=status.HTTP_201_CREATED,
        message="Vendor employee created successfully",
        data={
            "user_id": user_id,
            "username": employee_data.username,
            "email": employee_data.email,
            "password": generated_password,
            "vendor_ref_id": vendor_id
        }
    )


@router.get("/{user_id}")
@exception_handler
async def get_vendor_employee_by_id(
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Get vendor employee by user_id"""
    stmt = select(VendorLogin, Role.role_name).outerjoin(
        Role, VendorLogin.role == Role.role_id
    ).where(VendorLogin.user_id == user_id)
    
    result = await db.execute(stmt)
    employee_data = result.first()
    
    if not employee_data:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"Employee with ID '{user_id}' not found"
        )
    
    employee, role_name = employee_data
    
    # Decrypt email for response
    try:
        decrypted_email = decrypt_data(employee.email)
    except Exception:
        decrypted_email = "encrypted_email"
    
    # Check if username is "unknown" - not a vendor employee
    if employee.username == "unknown":
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Employee not found"
        )

    # Decrypt username for response
    decrypted_username = safe_decrypt_username(employee.username)
    
    return api_response(
        status_code=status.HTTP_200_OK,
        message="Employee retrieved successfully",
        data={
            "user_id": employee.user_id,
            "username": decrypted_username,
            "email": decrypted_email,
            "role_id": employee.role,
            "role_name": role_name,
            "vendor_ref_id": employee.vendor_ref_id,
            "is_active": employee.is_active
        }
    )


@router.put("/{user_id}")
@exception_handler
async def update_vendor_employee_by_id(
    user_id: str,
    update_data: VendorEmployeeUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Update vendor employee by user_id"""
    # Check if employee exists
    stmt = select(VendorLogin).where(VendorLogin.user_id == user_id)
    result = await db.execute(stmt)
    employee = result.scalar_one_or_none()
    
    if not employee:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"Employee with ID '{user_id}' not found"
        )
    
    # Check if username is "unknown" - not a vendor employee
    if employee.username == "unknown":
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Employee not found"
        )
    
    # Check if any data is provided for update
    update_dict = update_data.model_dump(exclude_unset=True)
    if not update_dict:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="No data provided for update"
        )
    
    # Validate role_id if provided
    if update_data.role_id:
        role_stmt = select(Role).where(Role.role_id == update_data.role_id)
        role_result = await db.execute(role_stmt)
        role = role_result.scalar_one_or_none()
        
        if not role:
            return api_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Role with ID '{update_data.role_id}' not found"
            )
        
        if role.role_status:
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=f"Role '{role.role_name}' is inactive and cannot be assigned"
            )
        
        employee.role = update_data.role_id
    
    # Check username uniqueness if provided
    if update_data.username:
        username_hash = hash_data(update_data.username.lower())
        
        # Check uniqueness using username_hash (excluding current user)
        username_stmt = select(VendorLogin).where(
            and_(
                VendorLogin.username_hash == username_hash,
                VendorLogin.user_id != user_id
            )
        )
        username_result = await db.execute(username_stmt)
        existing_username = username_result.scalar_one_or_none()
        
        if existing_username:
            return api_response(
                status_code=status.HTTP_409_CONFLICT,
                message=f"Username '{update_data.username}' is already taken"
            )
        
        encrypted_username = encrypt_data(update_data.username)
        employee.username = encrypted_username
        employee.username_hash = username_hash
    
    # Check email uniqueness if provided
    if update_data.email:
        encrypted_email = encrypt_data(update_data.email)
        email_hash = hash_data(update_data.email)
        
        # Check if email exists in ven_signup table
        signup_email_stmt = select(VendorSignup).where(VendorSignup.email_hash == email_hash)
        signup_email_result = await db.execute(signup_email_stmt)
        existing_signup_email = signup_email_result.scalar_one_or_none()
        
        if existing_signup_email:
            return api_response(
                status_code=status.HTTP_409_CONFLICT,
                message="This email already registered for vendor"
            )
        
        # Check if email exists in ven_login table (excluding current user)
        login_email_stmt = select(VendorLogin).where(
            and_(
                VendorLogin.email_hash == email_hash,
                VendorLogin.user_id != user_id
            )
        )
        login_email_result = await db.execute(login_email_stmt)
        existing_login_email = login_email_result.scalar_one_or_none()
        
        if existing_login_email:
            return api_response(
                status_code=status.HTTP_409_CONFLICT,
                message="This email already registered for vendor"
            )
        
        employee.email = encrypted_email
        employee.email_hash = email_hash
    
    # Update is_active if provided
    if update_data.is_active is not None:
        employee.is_active = update_data.is_active
    
    await db.commit()
    await db.refresh(employee)
    
    # Get current email for response
    try:
        current_email = decrypt_data(employee.email)
    except Exception:
        current_email = update_data.email if update_data.email else "encrypted_email"
    
    # Get current username for response
    current_username = safe_decrypt_username(employee.username, update_data.username if update_data.username else "updated_username")
    
    return api_response(
        status_code=status.HTTP_200_OK,
        message="Employee updated successfully",
        data={
            "user_id": employee.user_id,
            "username": current_username,
            "email": current_email,
            "role_id": employee.role,
            "vendor_ref_id": employee.vendor_ref_id,
            "is_active": employee.is_active
        }
    )


@router.patch("/{user_id}/soft-delete")
@exception_handler
async def soft_delete_vendor_employee_by_id(
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Soft delete vendor employee by user_id (set is_active to True - inactive)"""
    stmt = select(VendorLogin).where(VendorLogin.user_id == user_id)
    result = await db.execute(stmt)
    employee = result.scalar_one_or_none()
    
    if not employee:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"Employee with ID '{user_id}' not found"
        )
    
    # Check if username is "unknown" - not a vendor employee
    if employee.username == "unknown":
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Employee not found"
        )
    
    if employee.is_active:  # True means inactive
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=f"Employee with ID '{user_id}' is already inactive"
        )
    
    employee.is_active = True  # Set to True (inactive) for soft delete
    await db.commit()
    
    return api_response(
        status_code=status.HTTP_200_OK,
        message="Employee soft deleted successfully",
        data={"user_id": user_id}
    )


@router.delete("/{user_id}/hard-delete")
@exception_handler
async def hard_delete_vendor_employee_by_id(
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Hard delete vendor employee by user_id (permanently remove from database)"""
    stmt = select(VendorLogin).where(VendorLogin.user_id == user_id)
    result = await db.execute(stmt)
    employee = result.scalar_one_or_none()
    
    if not employee:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"Employee with ID '{user_id}' not found"
        )
    
    # Check if username is "unknown" - not a vendor employee
    if employee.username == "unknown":
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Employee not found"
        )
    
    await db.delete(employee)
    await db.commit()
    
    return api_response(
        status_code=status.HTTP_200_OK,
        message="Employee permanently deleted successfully",
        data={"user_id": user_id}
    )


@router.patch("/{user_id}/restore")
@exception_handler
async def restore_vendor_employee_by_id(
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Restore vendor employee by user_id (set is_active to False - active)"""
    stmt = select(VendorLogin).where(VendorLogin.user_id == user_id)
    result = await db.execute(stmt)
    employee = result.scalar_one_or_none()
    
    if not employee:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"Employee with ID '{user_id}' not found"
        )
    
    # Check if username is "unknown" - not a vendor employee
    if employee.username == "unknown":
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Employee not found"
        )
    
    if not employee.is_active:  # False means active
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=f"Employee with ID '{user_id}' is already active"
        )
    
    employee.is_active = False  # Set to False (active) for restore
    await db.commit()
    
    return api_response(
        status_code=status.HTTP_200_OK,
        message="Employee restored successfully",
        data={"user_id": user_id}
    )

@router.get("/")
@exception_handler
async def get_all_vendor_employees(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Get all vendor employees (excluding vendors) with pagination"""
   
    # Build base query with join to get role names
    # Only get employees (vendor_ref_id is not "unknown") - skip vendors (vendor_ref_id is "unknown")
    base_query = select(VendorLogin, Role.role_name).outerjoin(
        Role, VendorLogin.role == Role.role_id
    ).where(VendorLogin.vendor_ref_id != "unknown")
   
    # Get total count for employees only
    count_query = select(func.count(VendorLogin.user_id)).where(VendorLogin.vendor_ref_id != "unknown")
   
    total_result = await db.execute(count_query)
    total = total_result.scalar()
   
    # Calculate pagination
    total_pages = math.ceil(total / per_page)
    offset = (page - 1) * per_page
   
    # Get paginated results
    query = base_query.offset(offset).limit(per_page).order_by(VendorLogin.created_at.desc())
    result = await db.execute(query)
    employees_data = result.all()
   
    # Format response
    employees = []
    for employee, role_name in employees_data:
        try:
            decrypted_email = decrypt_data(employee.email)
        except Exception:
            decrypted_email = "encrypted_email"
       
        # Decrypt username for response
        decrypted_username = safe_decrypt_username(employee.username)
       
        employees.append({
            "user_id": employee.user_id,
            "username": decrypted_username,
            "email": decrypted_email,
            "role_id": employee.role,
            "role_name": role_name,
            "vendor_ref_id": employee.vendor_ref_id,
            "is_active": employee.is_active
        })
   
    return api_response(
        status_code=status.HTTP_200_OK,
        message="Employees retrieved successfully",
        data={
            "employees": employees,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages
        }
    )