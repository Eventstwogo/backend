"""User email functions for Shoppersky."""

from datetime import datetime, timezone
from typing import Optional

from pydantic import EmailStr

from core.config import settings
from core.logging_config import get_logger
from utils.email import email_sender

logger = get_logger(__name__)


def send_password_reset_email(
    email: EmailStr,
    username: str,
    reset_link: str,
    ip_address: Optional[str] = None,
    request_time: Optional[str] = None,
    expiry_minutes: int = 24,
) -> bool:
    """Send a password reset email to a user."""
    context = {
        "username": username,
        "email": email,
        "reset_link": reset_link,
        "ip_address": ip_address,
        "request_time": request_time
        or datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "expiry_minutes": expiry_minutes,
        "year": str(datetime.now(tz=timezone.utc).year),
        "support_email": settings.SUPPORT_EMAIL,
    }

    success = email_sender.send_email(
        to=email,
        subject="Reset Your Shoppersky Password",
        template_file="user_password_reset_email.html",
        context=context,
    )

    if not success:
        logger.warning("Failed to send password reset email to %s", email)

    return success


def send_user_verification_email(
    email: EmailStr,
    username: str,
    verification_token: str,
    user_id: str,
    expires_in_minutes: int = 60,
) -> bool:
    """
    Send a verification email to a new user with email verification link.

    Args:
        email: User's email address
        username: User's username
        verification_token: Email verification token
        user_id: User's unique identifier
        expires_in_minutes: Token expiry time in minutes

    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    verification_link = (
        f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')}/verify-email?email={email}"
        f"&token={verification_token}"
    )

    context = {
        "username": username,
        "email": email,
        "verification_link": verification_link,
        "welcome_url": getattr(settings, 'FRONTEND_URL', 'http://localhost:3000'),
        "year": str(datetime.now(tz=timezone.utc).year),
        "expires_in_minutes": expires_in_minutes,
        "support_email": settings.SUPPORT_EMAIL,
    }

    success = email_sender.send_email(
        to=email,
        subject="Welcome to Shoppersky - Verify Your Email",
        template_file="account_verification_email.html",
        context=context,
    )

    if not success:
        logger.warning("Failed to send verification email to %s", email)

    return success


def send_welcome_email(
    email: EmailStr,
    username: str,
    password: str,
    logo_url: str = "",
) -> bool:
    """
    Send a welcome email to a new user.

    Args:
        email: User's email address
        username: User's username
        password: User's temporary password
        logo_url: URL to company logo

    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    context = {
        "username": username,
        "email": email,
        "password": password,
        "logo_url": logo_url,
        "login_url": getattr(settings, 'FRONTEND_URL', 'http://localhost:3000') + "/login",
        "year": str(datetime.now(tz=timezone.utc).year),
        "support_email": settings.SUPPORT_EMAIL,
    }

    success = email_sender.send_email(
        to=email,
        subject="Welcome to Shoppersky",
        template_file="welcome_email.html",
        context=context,
    )

    if not success:
        logger.warning("Failed to send welcome email to %s", email)

    return success


def send_order_confirmation_email(
    email: EmailStr,
    username: str,
    order_id: str,
    order_details: dict,
    total_amount: float,
) -> bool:
    """
    Send an order confirmation email to a user.

    Args:
        email: User's email address
        username: User's username
        order_id: Order identifier
        order_details: Dictionary containing order details
        total_amount: Total order amount

    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    context = {
        "username": username,
        "email": email,
        "order_id": order_id,
        "total_amount": total_amount,
        "order_url": getattr(settings, 'FRONTEND_URL', 'http://localhost:3000') + f"/orders/{order_id}",
        "year": str(datetime.now(tz=timezone.utc).year),
        "support_email": settings.SUPPORT_EMAIL,
        **order_details,  # Unpack order_details to make all keys available at root level
    }

    success = email_sender.send_email(
        to=email,
        subject=f"Order Confirmation - #{order_id}",
        template_file="order_confirmation_email.html",
        context=context,
    )

    if not success:
        logger.warning("Failed to send order confirmation email to %s", email)

    return success