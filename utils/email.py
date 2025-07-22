import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, Optional, Union

from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import EmailStr, SecretStr

from core.config import settings
from core.logging_config import get_logger

logger = get_logger(__name__)


# Configuration
class EmailConfig:
    SMTP_SERVER: str
    SMTP_PORT: int
    SMTP_USERNAME: str
    SMTP_PASSWORD: SecretStr
    FROM_EMAIL: str
    TEMPLATE_DIR: str
    USE_TLS: bool = True
    USE_SSL: bool = False

    def __init__(
        self,
        smtp_server: str,
        smtp_port: int,
        smtp_username: str,
        smtp_password: str,
        from_email: str,
        template_dir: str,
        use_tls: bool = True,
        use_ssl: bool = False,
    ):
        self.SMTP_SERVER = smtp_server
        self.SMTP_PORT = smtp_port
        self.SMTP_USERNAME = smtp_username
        self.SMTP_PASSWORD = SecretStr(smtp_password)
        self.FROM_EMAIL = from_email
        self.TEMPLATE_DIR = template_dir
        self.USE_TLS = use_tls
        self.USE_SSL = use_ssl


# Email Utility
class EmailSender:
    def __init__(self, config: EmailConfig):
        self.config = config
        self.env = Environment(
            loader=FileSystemLoader(self.config.TEMPLATE_DIR),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def _render_template(
        self, template_file: str, context: Dict[str, Any]
    ) -> str:
        try:
            template = self.env.get_template(template_file)
            return template.render(**context)
        except Exception as e:
            logger.error(f"Template rendering failed: {e}")
            return ""

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

    def send_email(
        self,
        to: EmailStr,
        subject: str,
        template_file: str,
        context: Dict[str, Any],
    ) -> bool:
        """Send a rendered HTML email to a recipient."""
        server = self._connect_smtp()
        if not server:
            return False

        html = self._render_template(template_file, context)
        if not html:
            return False

        msg = MIMEMultipart()
        msg["From"] = self.config.FROM_EMAIL
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(html, "html"))

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
        return True


# Configuration from your settings
config = EmailConfig(
    smtp_server=settings.SMTP_HOST,
    smtp_port=settings.SMTP_PORT,
    smtp_username=settings.SMTP_USER,
    smtp_password=settings.SMTP_PASSWORD,
    from_email=settings.EMAIL_FROM,
    template_dir=settings.EMAIL_TEMPLATES_DIR,
    use_tls=True,
    use_ssl=False,  # Set True only for port 465
)

email_sender = EmailSender(config)


def send_welcome_email(
    email: EmailStr,  password: str, logo_url: str
) -> None:
    """Send a welcome email to a new user."""
    context = {
       
        "welcome_url": f"{settings.FRONTEND_URL}",
        "password": password,
        "logo_url": logo_url,
        "year": str(datetime.now(tz=timezone.utc).year),
    }

    success = email_sender.send_email(
        to=email,
        subject="Welcome to Shoppersky!",
        template_file="welcome_email.html",
        context=context,
    )

    if not success:
        logger.warning(f"Failed to send welcome email to {email}")
