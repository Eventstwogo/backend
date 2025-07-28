import secrets
import string
from datetime import datetime, timezone
from typing import Tuple

from pydantic import EmailStr
from passlib.context import CryptContext

from core.config import settings
from core.logging_config import get_logger
from utils.email import email_sender

logger = get_logger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def generate_admin_password(length: int = 6) -> str:
    """
    Generate a random password for admin users.
    
    Args:
        length: Length of the password (default: 6)
        
    Returns:
        str: Random password containing letters and digits
    """
    # Use only letters and digits for better readability in emails
    chars = string.ascii_letters + string.digits
    password = ''.join(secrets.choice(chars) for _ in range(length))
    
    logger.info(f"Generated new admin password of length {length}")
    return password


def hash_admin_password(password: str) -> str:
    """
    Hash the admin password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        str: Hashed password
    """
    hashed = pwd_context.hash(password)
    logger.info("Password hashed successfully")
    return hashed


def send_admin_credentials_email(
    email: EmailStr,
    username: str,
    password: str,
    logo_url: str = ""
) -> bool:
    """
    Send admin credentials via email.
    
    Args:
        email: Admin user's email address
        username: Admin user's username
        password: Plain text password to send
        logo_url: Optional logo URL
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    body = f"""
Hello {username},

Welcome to Shoppersky Admin Panel!

Your admin account has been created successfully.

Login Details:
- Email: {email}
- Username: {username}
- Password: {password}
- Admin Panel URL: {settings.FRONTEND_URL}/admin

IMPORTANT SECURITY NOTICE:
- Please change your password immediately after your first login
- Do not share these credentials with anyone
- Log out when you finish using the admin panel
- This password is randomly generated and unique to your account

If you have any questions or need assistance, please contact the system administrator.

Best regards,
Shoppersky Admin Team

© {datetime.now(tz=timezone.utc).year} Shoppersky. All rights reserved.

---
This is an automated message. Please do not reply to this email.
    """

    try:
        success = email_sender.send_text_email(
            to=email,
            subject="Shoppersky Admin Account - Login Credentials",
            body=body,
        )
        
        if success:
            logger.info(f"Admin credentials email sent successfully to {email}")
        else:
            logger.error(f"Failed to send admin credentials email to {email}")
            
        return success
        
    except Exception as e:
        logger.error(f"Exception occurred while sending admin credentials email to {email}: {e}")
        return False


def generate_and_send_admin_credentials(
    email: EmailStr,
    username: str,
    logo_url: str = ""
) -> Tuple[str, str, bool]:
    """
    Complete service to generate admin password and send credentials via email.
    
    Args:
        email: Admin user's email address
        username: Admin user's username
        logo_url: Optional logo URL
        
    Returns:
        Tuple[str, str, bool]: (plain_password, hashed_password, email_sent_success)
    """
    try:
        # Generate random password
        plain_password = generate_admin_password(6)
        
        # Hash the password
        hashed_password = hash_admin_password(plain_password)
        
        # Send credentials via email
        email_success = send_admin_credentials_email(
            email=email,
            username=username,
            password=plain_password,
            logo_url=logo_url
        )
        
        logger.info(f"Admin credentials generated and processed for {email}. Email sent: {email_success}")
        
        return plain_password, hashed_password, email_success
        
    except Exception as e:
        logger.error(f"Error in generate_and_send_admin_credentials for {email}: {e}")
        # Return empty values and False on error
        return "", "", False


def verify_admin_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify if a plain password matches the hashed password.
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password from database
        
    Returns:
        bool: True if password matches, False otherwise
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Error verifying admin password: {e}")
        return False