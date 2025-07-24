import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, Union

from pydantic import EmailStr, SecretStr

from core.config import settings
from core.logging_config import get_logger

logger = get_logger(__name__)


# Simple Email Configuration
class EmailConfig:
    SMTP_SERVER: str
    SMTP_PORT: int
    SMTP_USERNAME: str
    SMTP_PASSWORD: SecretStr
    FROM_EMAIL: str
    USE_TLS: bool = True
    USE_SSL: bool = False

    def __init__(
        self,
        smtp_server: str,
        smtp_port: int,
        smtp_username: str,
        smtp_password: str,
        from_email: str,
        use_tls: bool = True,
        use_ssl: bool = False,
    ):
        self.SMTP_SERVER = smtp_server
        self.SMTP_PORT = smtp_port
        self.SMTP_USERNAME = smtp_username
        self.SMTP_PASSWORD = SecretStr(smtp_password)
        self.FROM_EMAIL = from_email
        self.USE_TLS = use_tls
        self.USE_SSL = use_ssl


# Simple Email Utility
class EmailSender:
    def __init__(self, config: EmailConfig):
        self.config = config

    def _connect_smtp(self) -> Optional[Union[smtplib.SMTP, smtplib.SMTP_SSL]]:
        try:
            if self.config.USE_SSL:
                server: Union[smtplib.SMTP, smtplib.SMTP_SSL] = (
                    smtplib.SMTP_SSL(
                        self.config.SMTP_SERVER, self.config.SMTP_PORT
                    )
                )
            else:
                server = smtplib.SMTP(
                    self.config.SMTP_SERVER, self.config.SMTP_PORT
                )
                if self.config.USE_TLS:
                    server.starttls()
            server.login(
                self.config.SMTP_USERNAME,
                self.config.SMTP_PASSWORD.get_secret_value(),
            )
            return server
        except Exception as e:
            logger.error(f"SMTP connection/login failed: {e}")
            return None

    def send_text_email(
        self,
        to: EmailStr,
        subject: str,
        body: str,
    ) -> bool:
        """Send a plain text email to a recipient."""
        server = self._connect_smtp()
        if not server:
            return False

        msg = MIMEMultipart()
        msg["From"] = self.config.FROM_EMAIL
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        try:
            server.sendmail(self.config.FROM_EMAIL, to, msg.as_string())
            logger.info(f"Email sent to {to}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
        finally:
            try:
                server.quit()
            except Exception as e:
                logger.warning(f"Failed to close SMTP connection: {e}")


# Configuration from your settings
config = EmailConfig(
    smtp_server=settings.SMTP_HOST,
    smtp_port=settings.SMTP_PORT,
    smtp_username=settings.SMTP_USER,
    smtp_password=settings.SMTP_PASSWORD,
    from_email=settings.EMAIL_FROM,
    use_tls=True,
    use_ssl=False,  # Set True only for port 465
)

email_sender = EmailSender(config)


def send_welcome_email(
    email: EmailStr, password: str, logo_url: str
) -> None:
    """Send a welcome email to a new user."""
    body = f"""
Welcome to Shoppersky!

Your account has been created successfully.

Login Details:
- Email: {email}
- Password: {password}
- Login URL: {settings.FRONTEND_URL}

Please change your password after your first login for security.

Best regards,
Shoppersky Team

© {datetime.now(tz=timezone.utc).year} Shoppersky. All rights reserved.
    """

    success = email_sender.send_text_email(
        to=email,
        subject="Welcome to Shoppersky!",
        body=body,
    )

    if not success:
        logger.warning(f"Failed to send welcome email to {email}")


def send_admin_password_reset_email(
    email: EmailStr,
    username: str,
    reset_link: str,
    expiry_minutes: int,
    ip_address: str,
    request_time: str,
) -> bool:
    """Send a password reset email to an admin user."""
    body = f"""
Hello {username},

We received a request to reset your password for your Shoppersky admin account.

Reset Link: {reset_link}

This link will expire in {expiry_minutes} minutes for security reasons.

Security Information:
- Request Time: {request_time}
- IP Address: {ip_address}

If you didn't request this password reset, you can safely ignore this email.

For security reasons, we recommend:
- Using a strong, unique password
- Not sharing your login credentials
- Logging out when finished using the admin panel

Best regards,
Shoppersky Team

© {datetime.now(tz=timezone.utc).year} Shoppersky. All rights reserved.
    """
    
    # For development, just log the email content
    logger.info(f"Password reset email would be sent to {email}")
    logger.info(f"Reset link: {reset_link}")
    
    # In production, uncomment this to actually send emails:
    # success = email_sender.send_text_email(
    #     to=email,
    #     subject="Password Reset Request - Shoppersky Admin",
    #     body=body,
    # )
    # return success
    
    return True  # Return True for development
