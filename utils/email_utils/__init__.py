"""Email utilities package for Shoppersky."""

from .user_emails import (
    send_password_reset_email,
    send_user_verification_email,
    send_welcome_email,
    send_order_confirmation_email,
)
from .admin_emails import (
    send_admin_password_reset_email,
    send_admin_welcome_email,
)
from .vendor_emails import (
    send_vendor_onboarding_email,
    send_vendor_verification_email,
    send_vendor_password_reset_email,
    send_vendor_employee_credentials_email,
)

__all__ = [
    # User email functions
    "send_password_reset_email",
    "send_user_verification_email", 
    "send_welcome_email",
    "send_order_confirmation_email",
    # Admin email functions
    "send_admin_password_reset_email",
    "send_admin_welcome_email",
    # Vendor email functions
    "send_vendor_onboarding_email",
    "send_vendor_verification_email",
    "send_vendor_password_reset_email",
    "send_vendor_employee_credentials_email",
]