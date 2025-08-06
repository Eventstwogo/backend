"""Admin email functions for Shoppersky."""

from datetime import datetime, timezone
from typing import Optional

from pydantic import EmailStr

from core.config import settings
from core.logging_config import get_logger
from utils.email import email_sender

logger = get_logger(__name__)


def send_admin_password_reset_email(
    email: EmailStr,
    username: str,
    reset_link: str,
    ip_address: Optional[str] = None,
    request_time: Optional[str] = None,
    expiry_minutes: int = 24,
) -> bool:
    """Send a password reset email to an admin."""
    context = {
        "username": username,
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
        subject="Reset Your Shoppersky Admin Password",
        template_file="password_reset_email.html",
        context=context,
    )

    if not success:
        logger.warning("Failed to send admin password reset email to %s", email)

    return success


def send_admin_welcome_email(
    email: EmailStr,
    username: str,
    password: str,
    admin_panel_url: Optional[str] = None,
) -> bool:
    """
    Send a welcome email to a new admin.

    Args:
        email: Admin's email address
        username: Admin's username
        password: Admin's temporary password
        admin_panel_url: URL to admin panel

    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    if not admin_panel_url:
        admin_panel_url = settings.ADMIN_FRONTEND_URL

    context = {
        "username": username,
        "email": email,
        "password": password,
        "admin_panel_url": admin_panel_url,
        "login_url": admin_panel_url + "/login",
        "current_year": str(datetime.now(tz=timezone.utc).year),
        "support_email": settings.SUPPORT_EMAIL,
    }

    success = email_sender.send_email(
        to=email,
        subject="Welcome to Shoppersky Admin Panel",
        template_file="admin_welcome_email.html",
        context=context,
    )

    if not success:
        logger.warning("Failed to send admin welcome email to %s", email)

    return success