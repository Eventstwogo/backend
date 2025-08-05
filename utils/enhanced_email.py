"""
Enhanced Email Utility System for Shoppersky
Supports multiple email providers with Jinja2 templates and comprehensive error handling
"""

import smtplib
import ssl
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import logging
import asyncio
from contextlib import contextmanager

from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from pydantic import EmailStr, SecretStr, ValidationError

logger = logging.getLogger(__name__)


@dataclass
class EmailConfig:
    """
    Dataclass-based email configuration for clean code and type safety
    """
    # SMTP Connection Settings
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    
    # Email Identity
    from_email: str
    from_name: str = "Shoppersky Team"
    
    # Connection Security
    use_tls: bool = True
    use_ssl: bool = False
    
    # Timeout and Retry Settings
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    
    # Template Settings
    templates_dir: str = "templates"
    
    # Validation
    validate_emails: bool = True
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        if self.use_ssl and self.use_tls:
            raise ValueError("Cannot use both SSL and TLS simultaneously")
            
        if self.smtp_port == 465 and not self.use_ssl:
            logger.warning("Port 465 typically requires SSL. Consider setting use_ssl=True")
            
        if self.smtp_port == 587 and not self.use_tls:
            logger.warning("Port 587 typically requires TLS. Consider setting use_tls=True")
            
        # Validate email addresses if validation is enabled
        if self.validate_emails:
            try:
                from pydantic import validate_email
                validate_email(self.from_email)
            except ValidationError as e:
                raise ValueError(f"Invalid from_email address: {e}")

    @classmethod
    def from_provider(cls, provider: str, **kwargs) -> 'EmailConfig':
        """
        Create configuration for popular email providers
        """
        provider_configs = {
            "gmail": {
                "smtp_host": "smtp.gmail.com",
                "smtp_port": 587,
                "use_tls": True,
                "use_ssl": False
            },
            "sendgrid": {
                "smtp_host": "smtp.sendgrid.net",
                "smtp_port": 587,
                "use_tls": True,
                "use_ssl": False
            },
            "brevo": {
                "smtp_host": "smtp-relay.brevo.com",
                "smtp_port": 587,
                "use_tls": True,
                "use_ssl": False
            },
            "ses_us_east_1": {
                "smtp_host": "email-smtp.us-east-1.amazonaws.com",
                "smtp_port": 587,
                "use_tls": True,
                "use_ssl": False
            },
            "ses_eu_west_1": {
                "smtp_host": "email-smtp.eu-west-1.amazonaws.com",
                "smtp_port": 587,
                "use_tls": True,
                "use_ssl": False
            },
            "outlook": {
                "smtp_host": "smtp-mail.outlook.com",
                "smtp_port": 587,
                "use_tls": True,
                "use_ssl": False
            }
        }
        
        if provider not in provider_configs:
            raise ValueError(f"Unknown provider: {provider}. Available: {list(provider_configs.keys())}")
            
        config = provider_configs[provider]
        config.update(kwargs)
        return cls(**config)


@dataclass
class EmailResult:
    """Result of email sending operation"""
    success: bool
    message: str
    recipient: str
    subject: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error_details: Optional[str] = None
    retry_count: int = 0


class EmailSender:
    """
    Enhanced email sender with connection management, templates, and error handling
    """
    
    def __init__(self, config: EmailConfig):
        self.config = config
        self._template_env: Optional[Environment] = None
        self._connection_pool: Dict[str, smtplib.SMTP] = {}
        
        # Initialize Jinja2 environment
        self._setup_templates()
    
    def _setup_templates(self):
        """Setup Jinja2 template environment"""
        try:
            template_path = Path(self.config.templates_dir)
            if not template_path.exists():
                logger.warning(f"Template directory not found: {template_path}")
                return
                
            self._template_env = Environment(
                loader=FileSystemLoader(str(template_path)),
                autoescape=True,
                trim_blocks=True,
                lstrip_blocks=True
            )
            logger.info(f"✅ Email templates loaded from: {template_path}")
            
        except Exception as e:
            logger.error(f"Failed to setup email templates: {e}")
    
    @contextmanager
    def _get_smtp_connection(self):
        """
        Context manager for SMTP connections with automatic cleanup
        """
        server = None
        try:
            # Create connection based on security settings
            if self.config.use_ssl:
                context = ssl.create_default_context()
                server = smtplib.SMTP_SSL(
                    self.config.smtp_host, 
                    self.config.smtp_port,
                    timeout=self.config.timeout,
                    context=context
                )
            else:
                server = smtplib.SMTP(
                    self.config.smtp_host, 
                    self.config.smtp_port,
                    timeout=self.config.timeout
                )
                
                if self.config.use_tls:
                    server.starttls()
            
            # Authenticate
            server.login(self.config.smtp_user, self.config.smtp_password)
            logger.debug(f"✅ SMTP connection established to {self.config.smtp_host}:{self.config.smtp_port}")
            
            yield server
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            raise
        except smtplib.SMTPConnectError as e:
            logger.error(f"SMTP connection failed: {e}")
            raise
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected SMTP error: {e}")
            raise
        finally:
            if server:
                try:
                    server.quit()
                except Exception as e:
                    logger.warning(f"Error closing SMTP connection: {e}")
    
    def _render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render Jinja2 template with context
        """
        if not self._template_env:
            raise ValueError("Template environment not initialized")
            
        try:
            template = self._template_env.get_template(template_name)
            
            # Add common context variables
            common_context = {
                'current_year': datetime.now(timezone.utc).year,
                'company_name': 'Shoppersky',
                'timestamp': datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                'from_name': self.config.from_name
            }
            
            # Merge contexts (user context takes precedence)
            full_context = {**common_context, **context}
            
            return template.render(**full_context)
            
        except TemplateNotFound:
            raise ValueError(f"Template not found: {template_name}")
        except Exception as e:
            raise ValueError(f"Template rendering error: {e}")
    
    def _validate_email(self, email: str) -> bool:
        """Validate email address"""
        if not self.config.validate_emails:
            return True
            
        try:
            from pydantic import validate_email
            validate_email(email)
            return True
        except ValidationError:
            return False
    
    def _create_message(
        self,
        to_email: str,
        subject: str,
        html_content: Optional[str] = None,
        text_content: Optional[str] = None,
        reply_to: Optional[str] = None
    ) -> MIMEMultipart:
        """Create email message with proper headers"""
        
        if not html_content and not text_content:
            raise ValueError("Either html_content or text_content must be provided")
        
        # Create message
        if html_content and text_content:
            msg = MIMEMultipart('alternative')
        else:
            msg = MIMEMultipart()
        
        # Set headers
        msg['From'] = f"{self.config.from_name} <{self.config.from_email}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        
        if reply_to:
            msg['Reply-To'] = reply_to
        
        # Add content
        if text_content:
            text_part = MIMEText(text_content, 'plain', 'utf-8')
            msg.attach(text_part)
        
        if html_content:
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
        
        return msg
    
    def send_email(
        self,
        to_email: Union[str, EmailStr],
        subject: str,
        html_content: Optional[str] = None,
        text_content: Optional[str] = None,
        reply_to: Optional[str] = None
    ) -> EmailResult:
        """
        Send email with retry logic and comprehensive error handling
        """
        to_email_str = str(to_email)
        
        # Validate recipient email
        if not self._validate_email(to_email_str):
            return EmailResult(
                success=False,
                message="Invalid recipient email address",
                recipient=to_email_str,
                subject=subject,
                error_details="Email validation failed"
            )
        
        # Attempt to send with retries
        last_error = None
        for attempt in range(self.config.max_retries):
            try:
                with self._get_smtp_connection() as server:
                    msg = self._create_message(
                        to_email_str, subject, html_content, text_content, reply_to
                    )
                    
                    server.sendmail(
                        self.config.from_email,
                        to_email_str,
                        msg.as_string()
                    )
                    
                    logger.info(f"✅ Email sent successfully to {to_email_str} (attempt {attempt + 1})")
                    return EmailResult(
                        success=True,
                        message="Email sent successfully",
                        recipient=to_email_str,
                        subject=subject,
                        retry_count=attempt
                    )
                    
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Email send attempt {attempt + 1} failed: {e}")
                
                if attempt < self.config.max_retries - 1:
                    delay = self.config.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.info(f"Retrying in {delay} seconds...")
                    import time
                    time.sleep(delay)
        
        # All attempts failed
        logger.error(f"❌ Failed to send email to {to_email_str} after {self.config.max_retries} attempts")
        return EmailResult(
            success=False,
            message=f"Failed after {self.config.max_retries} attempts",
            recipient=to_email_str,
            subject=subject,
            error_details=last_error,
            retry_count=self.config.max_retries
        )
    
    def send_template_email(
        self,
        to_email: Union[str, EmailStr],
        subject: str,
        template_name: str,
        context: Dict[str, Any],
        reply_to: Optional[str] = None
    ) -> EmailResult:
        """
        Send email using Jinja2 template
        """
        try:
            html_content = self._render_template(template_name, context)
            return self.send_email(
                to_email=to_email,
                subject=subject,
                html_content=html_content,
                reply_to=reply_to
            )
        except Exception as e:
            logger.error(f"Template email failed: {e}")
            return EmailResult(
                success=False,
                message="Template rendering failed",
                recipient=str(to_email),
                subject=subject,
                error_details=str(e)
            )
    
    def send_bulk_emails(
        self,
        recipients: List[Union[str, EmailStr]],
        subject: str,
        html_content: Optional[str] = None,
        text_content: Optional[str] = None,
        max_concurrent: int = 5
    ) -> List[EmailResult]:
        """
        Send emails to multiple recipients with concurrency control
        """
        results = []
        
        # Process in batches to avoid overwhelming the SMTP server
        for i in range(0, len(recipients), max_concurrent):
            batch = recipients[i:i + max_concurrent]
            batch_results = []
            
            for recipient in batch:
                result = self.send_email(
                    to_email=recipient,
                    subject=subject,
                    html_content=html_content,
                    text_content=text_content
                )
                batch_results.append(result)
            
            results.extend(batch_results)
            
            # Brief pause between batches
            if i + max_concurrent < len(recipients):
                import time
                time.sleep(0.5)
        
        successful = sum(1 for r in results if r.success)
        logger.info(f"📧 Bulk email complete: {successful}/{len(recipients)} sent successfully")
        
        return results
    
    def test_connection(self) -> bool:
        """
        Test SMTP connection and authentication
        """
        try:
            with self._get_smtp_connection() as server:
                # Try to get server status
                status = server.noop()
                logger.info(f"✅ SMTP connection test successful: {status}")
                return True
        except Exception as e:
            logger.error(f"❌ SMTP connection test failed: {e}")
            return False


# Convenience functions for common email types
class EmailTemplates:
    """Pre-defined email templates and helpers"""
    
    @staticmethod
    def welcome_email_context(
        username: str,
        email: str,
        password: str,
        login_url: str
    ) -> Dict[str, Any]:
        """Context for welcome email template"""
        return {
            'username': username,
            'email': email,
            'password': password,
            'login_url': login_url,
            'header_subtitle': 'Welcome to our platform!'
        }
    
    @staticmethod
    def password_reset_context(
        username: str,
        reset_link: str,
        expiry_minutes: int = 30,
        ip_address: str = "Unknown"
    ) -> Dict[str, Any]:
        """Context for password reset email template"""
        return {
            'username': username,
            'reset_link': reset_link,
            'expiry_minutes': expiry_minutes,
            'ip_address': ip_address,
            'request_time': datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            'header_subtitle': 'Secure password reset request'
        }
    
    @staticmethod
    def verification_email_context(
        username: str,
        verification_link: str,
        verification_code: str,
        expiry_minutes: int = 30
    ) -> Dict[str, Any]:
        """Context for account verification email template"""
        return {
            'username': username,
            'verification_link': verification_link,
            'verification_code': verification_code,
            'expiry_minutes': expiry_minutes,
            'header_subtitle': 'Verify your account to get started'
        }


# Factory function for easy configuration
def create_email_sender_from_settings(settings) -> EmailSender:
    """
    Create EmailSender from application settings
    """
    # Handle SecretStr password
    password = settings.SMTP_PASSWORD
    if hasattr(password, 'get_secret_value'):
        password = password.get_secret_value()
    
    config = EmailConfig(
        smtp_host=settings.SMTP_HOST,
        smtp_port=settings.SMTP_PORT,
        smtp_user=settings.SMTP_USER,
        smtp_password=str(password),
        from_email=str(settings.EMAIL_FROM),
        from_name=settings.EMAIL_FROM_NAME,
        use_tls=getattr(settings, 'SMTP_TLS', True),
        use_ssl=getattr(settings, 'SMTP_SSL', False),
        timeout=getattr(settings, 'EMAIL_TIMEOUT', 30),
        max_retries=getattr(settings, 'EMAIL_MAX_RETRIES', 3),
        templates_dir=getattr(settings, 'EMAIL_TEMPLATES_DIR', 'templates')
    )
    
    return EmailSender(config)