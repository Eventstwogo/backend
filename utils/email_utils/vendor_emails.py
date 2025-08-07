"""Vendor email functions for Shoppersky."""

from datetime import datetime, timezone
from typing import Optional

from pydantic import EmailStr

from core.config import settings
from core.logging_config import get_logger
from utils.email import email_sender

logger = get_logger(__name__)


def send_vendor_onboarding_email(
    email: EmailStr,
    business_name: str,
    username: str,
    password: str,
    vendor_portal_url: Optional[str] = None,
    reference_id: Optional[str] = None,
) -> bool:
    """
    Send an onboarding email to a new vendor.

    Args:
        email: Vendor's email address
        business_name: Vendor's business name
        username: Vendor's username
        password: Vendor's temporary password
        vendor_portal_url: URL to vendor portal
        reference_id: Application reference ID

    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    if not vendor_portal_url:
        vendor_portal_url = settings.VENDOR_FRONTEND_URL

    context = {
        "vendor_name": username,
        "business_name": business_name,
        "username": username,
        "email": email,
        "password": password,
        "vendor_portal_url": vendor_portal_url,
        "login_url": vendor_portal_url + "/login",
        "current_year": str(datetime.now(tz=timezone.utc).year),
        "support_email": settings.SUPPORT_EMAIL,
        "reference_id": reference_id,
    }

    success = email_sender.send_email(
        to=email,
        subject="Welcome to Shoppersky Vendor Portal",
        template_file="vendor_onboarding_email.html",
        context=context,
    )

    if not success:
        logger.warning("Failed to send vendor onboarding email to %s", email)

    return success


def send_vendor_verification_email(
    email: EmailStr,
    business_name: str,
    verification_token: str,
    expires_in_minutes: int = 60,
) -> bool:
    """
    Send a verification email to a vendor.

    Args:
        email: Vendor's email address
        business_name: Vendor's business name
        verification_token: Email verification token
        expires_in_minutes: Token expiry time in minutes

    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    verification_link = (
        f"{settings.VENDOR_FRONTEND_URL}/emailconfirmation?email={email}"
        f"&token={verification_token}"
    )

    context = {
        "business_name": business_name,
        "email": email,
        "verification_link": verification_link,
        "vendor_portal_url": settings.VENDOR_FRONTEND_URL,
        "current_year": str(datetime.now(tz=timezone.utc).year),
        "expires_in_minutes": expires_in_minutes,
        "support_email": settings.SUPPORT_EMAIL,
    }

    success = email_sender.send_email(
        to=email,
        subject="Verify Your Shoppersky Vendor Account",
        template_file="vendor_verification_email.html",
        context=context,
    )

    if not success:
        logger.warning("Failed to send vendor verification email to %s", email)

    return success

def send_vendor_password_reset_email(
    email: EmailStr,
    business_name: str,
    reset_link: str,
    ip_address: Optional[str] = None,
    request_time: Optional[str] = None,
    expiry_minutes: int = 24,
) -> bool:
    """Send a password reset email to a vendor."""
    context = {
        "business_name": business_name,
        "email": email,
        "reset_link": reset_link,
        "ip_address": ip_address,
        "request_time": request_time
        or datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "expiry_minutes": expiry_minutes,
        "current_year": str(datetime.now(tz=timezone.utc).year),
        "support_email": settings.SUPPORT_EMAIL,
    }

    success = email_sender.send_email(
        to=email,
        subject="Reset Your Shoppersky Vendor Password",
        template_file="vendor_password_reset_email.html",
        context=context,
    )

    if not success:
        logger.warning("Failed to send vendor password reset email to %s", email)

    return success


def send_vendor_employee_credentials_email(
    email: EmailStr,
    employee_name: str,
    business_name: str,
    username: str,
    password: str,
    vendor_portal_url: Optional[str] = None,
    role_name: Optional[str] = None,
) -> bool:
    """
    Send credentials email to a new vendor employee.

    Args:
        email: Employee's email address
        employee_name: Employee's name
        business_name: Vendor's business name
        username: Employee's username
        password: Employee's temporary password
        vendor_portal_url: URL to vendor portal
        role_name: Employee's role name

    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    if not vendor_portal_url:
        vendor_portal_url = settings.VENDOR_FRONTEND_URL

    context = {
        "employee_name": employee_name,
        "business_name": business_name,
        "username": username,
        "email": email,
        "password": password,
        "vendor_portal_url": vendor_portal_url,
        "login_url": vendor_portal_url + "/login",
        "current_year": str(datetime.now(tz=timezone.utc).year),
        "support_email": settings.SUPPORT_EMAIL,
        "frontend_url": settings.FRONTEND_URL,  # Add missing frontend_url
        "role_name": role_name or "Employee",  # Add role_name with default
        "creation_date": datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),  # Add creation_date
    }

    success = email_sender.send_email(
        to=email,
        subject=f"Your {business_name} Employee Account Credentials",
        template_file="vendor_employee_credentials_email.html",
        context=context,
    )

    if not success:
        logger.warning("Failed to send vendor employee credentials email to %s", email)

    return success


def send_vendor_approval_email(
    email: EmailStr,
    vendor_name: str,
    business_name: str,
    reference_id: str,
    vendor_portal_url: Optional[str] = None,
) -> bool:
    """
    Send an approval email to a vendor.

    Args:
        email: Vendor's email address
        vendor_name: Vendor's name
        business_name: Vendor's business name
        reference_id: Application reference ID
        vendor_portal_url: URL to vendor portal

    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    if not vendor_portal_url:
        vendor_portal_url = settings.VENDOR_FRONTEND_URL

    context = {
        "vendor_name": vendor_name,
        "business_name": business_name,
        "email": email,
        "reference_id": reference_id,
        "vendor_portal_url": vendor_portal_url,
        "approval_date": datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "current_year": str(datetime.now(tz=timezone.utc).year),
        "support_email": settings.SUPPORT_EMAIL,
    }

    success = email_sender.send_email(
        to=email,
        subject="Your Shoppersky Vendor Application Has Been Approved!",
        template_file="vendor_approval_email.html",
        context=context,
    )

    if not success:
        logger.warning("Failed to send vendor approval email to %s", email)

    return success


def send_vendor_rejection_email(
    email: EmailStr,
    vendor_name: str,
    business_name: str,
    reference_id: str,
    reviewer_comment: Optional[str] = None,
    vendor_portal_url: Optional[str] = None,
) -> bool:
    """
    Send a rejection email to a vendor.

    Args:
        email: Vendor's email address
        vendor_name: Vendor's name
        business_name: Vendor's business name
        reference_id: Application reference ID
        reviewer_comment: Reason for rejection
        vendor_portal_url: URL to vendor portal

    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    if not vendor_portal_url:
        vendor_portal_url = settings.VENDOR_FRONTEND_URL

    context = {
        "vendor_name": vendor_name,
        "business_name": business_name,
        "email": email,
        "reference_id": reference_id,
        "reviewer_comment": reviewer_comment,
        "vendor_portal_url": vendor_portal_url,
        "review_date": datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "current_year": str(datetime.now(tz=timezone.utc).year),
        "support_email": settings.SUPPORT_EMAIL,
    }

    success = email_sender.send_email(
        to=email,
        subject="Shoppersky Vendor Application Update",
        template_file="vendor_rejection_email.html",
        context=context,
    )

    if not success:
        logger.warning("Failed to send vendor rejection email to %s", email)

    return success