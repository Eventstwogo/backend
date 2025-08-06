import smtplib
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, Optional, Union

from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import EmailStr

from core.config import settings
from core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class EmailConfig:
    """Email configuration class using dataclass to reduce boilerplate."""

    # SMTP connection details
    smtp_server: str
    smtp_port: int

    # Authentication
    smtp_username: str
    smtp_password: str

    # Email content settings
    from_email: str
    template_dir: str

    # Connection security (combined into a single attribute)
    connection_security: str = "tls"  # Options: "tls", "ssl", "none"

    @property
    def use_tls(self) -> bool:
        """Determine if TLS should be used."""
        return self.connection_security == "tls"

    @property
    def use_ssl(self) -> bool:
        """Determine if SSL should be used."""
        return self.connection_security == "ssl"

    # def __post_init__(self):
    #     """Convert password string to SecretStr if needed."""
    #     if self.smtp_password and not isinstance(self.smtp_password, SecretStr):
    #         self.smtp_password = SecretStr(self.smtp_password)


# Email Utility
class EmailSender:
    def __init__(self, config: EmailConfig):
        self.config = config
        self.env = Environment(
            loader=FileSystemLoader(self.config.template_dir),
            autoescape=select_autoescape(["html", "xml"]),
            cache_size=0,  # Disable template caching for development
        )

    def _render_template(
        self, template_file: str, context: Dict[str, Any]
    ) -> str:
        try:
            template = self.env.get_template(template_file)
            return template.render(**context)
        except Exception as e:
            logger.error("Template rendering failed: %s", e)
            return ""
    
    def reload_templates(self):
        """Force reload all templates by recreating the Jinja2 environment."""
        logger.info("Reloading email templates...")
        self.env = Environment(
            loader=FileSystemLoader(self.config.template_dir),
            autoescape=select_autoescape(["html", "xml"]),
            cache_size=0,  # Disable template caching for development
        )

    def _connect_smtp(self) -> Optional[Union[smtplib.SMTP, smtplib.SMTP_SSL]]:
        try:
            if self.config.use_ssl:
                server: Union[smtplib.SMTP, smtplib.SMTP_SSL] = (
                    smtplib.SMTP_SSL(
                        self.config.smtp_server, self.config.smtp_port
                    )
                )
            else:
                server = smtplib.SMTP(
                    self.config.smtp_server, self.config.smtp_port
                )
                if self.config.use_tls:
                    server.starttls()
            server.login(
                self.config.smtp_username,
                self.config.smtp_password,
            )
            return server
        except Exception as e:
            logger.error("SMTP connection/login failed: %s", e)
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
        msg["From"] = self.config.from_email
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(html, "html"))

        try:
            server.sendmail(self.config.from_email, to, msg.as_string())
            logger.info("Email sent to %s", to)
            return True
        except Exception as e:
            logger.error("Failed to send email: %s", e)
            return False
        finally:
            try:
                server.quit()
            except Exception as e:
                logger.warning("Failed to close SMTP connection: %s", e)


# Configuration from settings
email_config = EmailConfig(
    smtp_server=settings.SMTP_HOST,
    smtp_port=settings.SMTP_PORT,
    smtp_username=settings.SMTP_USER,
    smtp_password=settings.SMTP_PASSWORD,
    from_email=settings.EMAIL_FROM,
    template_dir=settings.EMAIL_TEMPLATES_DIR,
    connection_security="tls",  # Use TLS by default (port 587), use "ssl" for port 465
)

email_sender = EmailSender(email_config)
