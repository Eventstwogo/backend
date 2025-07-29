import os
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, Template
from pydantic import EmailStr, SecretStr

from core.config import settings
from core.logging_config import get_logger

logger = get_logger(__name__)


class EmailTemplateService:
    """Enhanced email service with HTML template support using Jinja2"""
    
    def __init__(self):
        self.smtp_server = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.EMAIL_FROM
        self.from_name = settings.EMAIL_FROM_NAME
        
        # Setup Jinja2 environment for templates
        template_dir = Path(__file__).parent.parent / "templates"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=True
        )
        
    def _get_smtp_connection(self) -> Optional[smtplib.SMTP]:
        """Create and return SMTP connection"""
        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            return server
        except Exception as e:
            logger.error(f"Failed to connect to SMTP server: {e}")
            return None
    
    def _render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render HTML template with context data"""
        try:
            template = self.jinja_env.get_template(template_name)
            # Add common context variables
            context.update({
                'current_year': datetime.now(tz=timezone.utc).year,
                'company_name': 'Shoppersky',
                'frontend_url': settings.FRONTEND_URL
            })
            return template.render(**context)
        except Exception as e:
            logger.error(f"Failed to render template {template_name}: {e}")
            return ""
    
    def send_html_email(
        self,
        to_email: EmailStr,
        subject: str,
        html_content: str,
        plain_text: Optional[str] = None
    ) -> bool:
        """Send HTML email with optional plain text fallback"""
        try:
            server = self._get_smtp_connection()
            if not server:
                return False
            
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add plain text version if provided
            if plain_text:
                text_part = MIMEText(plain_text, 'plain', 'utf-8')
                msg.attach(text_part)
            
            # Add HTML version
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            server.sendmail(self.from_email, to_email, msg.as_string())
            server.quit()
            
            logger.info(f"HTML email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send HTML email to {to_email}: {e}")
            return False
    
    def send_template_email(
        self,
        to_email: EmailStr,
        subject: str,
        template_name: str,
        context: Dict[str, Any]
    ) -> bool:
        """Send email using HTML template"""
        html_content = self._render_template(template_name, context)
        if not html_content:
            return False
        
        return self.send_html_email(to_email, subject, html_content)
    
    def send_welcome_email(
        self,
        email: EmailStr,
        username: str,
        password: str,
        login_url: Optional[str] = None
    ) -> bool:
        """Send welcome email to new user"""
        context = {
            'username': username,
            'email': email,
            'password': password,
            'login_url': login_url or settings.FRONTEND_URL,
            'header_subtitle': 'Welcome to our platform!'
        }
        
        return self.send_template_email(
            to_email=email,
            subject="Welcome to Shoppersky! 🎉",
            template_name="welcome_email.html",
            context=context
        )
    
    def send_password_reset_email(
        self,
        email: EmailStr,
        username: str,
        reset_link: str,
        expiry_minutes: int = 30,
        ip_address: str = "Unknown",
        user_agent: str = "Unknown"
    ) -> bool:
        """Send password reset email"""
        context = {
            'username': username,
            'reset_link': reset_link,
            'expiry_minutes': expiry_minutes,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'request_time': datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            'header_subtitle': 'Secure password reset request'
        }
        
        return self.send_template_email(
            to_email=email,
            subject="Password Reset Request - Shoppersky Admin 🔐",
            template_name="password_reset_email.html",
            context=context
        )
    
    def send_user_password_reset_email(
        self,
        email: EmailStr,
        username: str,
        reset_link: str,
        expiry_minutes: int = 30,
        ip_address: str = "Unknown",
        user_agent: str = "Unknown"
    ) -> bool:
        """Send password reset email for regular users"""
        context = {
            'username': username,
            'reset_link': reset_link,
            'expiry_minutes': expiry_minutes,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'request_time': datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            'header_subtitle': 'Reset your account password',
            'is_user_account': True  # Flag to distinguish from admin emails
        }
        
        return self.send_template_email(
            to_email=email,
            subject="Password Reset Request - Shoppersky 🔐",
            template_name="user_password_reset_email.html",
            context=context
        )
    
    def send_account_verification_email(
        self,
        email: EmailStr,
        username: str,
        verification_link: str,
        verification_code: str,
        expiry_minutes: int = 30
    ) -> bool:
        """Send account verification email"""
        context = {
            'username': username,
            'verification_link': verification_link,
            'verification_code': verification_code,
            'expiry_minutes': expiry_minutes,
            'header_subtitle': 'Verify your account to get started'
        }
        
        return self.send_template_email(
            to_email=email,
            subject="Verify Your Shoppersky Account",
            template_name="account_verification_email.html",
            context=context
        )
    
    def send_order_confirmation_email(
        self,
        email: EmailStr,
        customer_name: str,
        order_number: str,
        order_date: str,
        order_status: str,
        payment_method: str,
        order_items: List[Dict[str, Any]],
        order_total: str,
        shipping_address: Dict[str, str],
        estimated_delivery_date: str,
        shipping_method: str,
        track_order_url: str
    ) -> bool:
        """Send order confirmation email"""
        context = {
            'customer_name': customer_name,
            'order_number': order_number,
            'order_date': order_date,
            'order_status': order_status,
            'payment_method': payment_method,
            'order_items': order_items,
            'order_total': order_total,
            'shipping_address': shipping_address,
            'estimated_delivery_date': estimated_delivery_date,
            'shipping_method': shipping_method,
            'track_order_url': track_order_url,
            'header_subtitle': 'Your order has been confirmed'
        }
        
        return self.send_template_email(
            to_email=email,
            subject=f"Order Confirmation #{order_number} - Shoppersky 📦",
            template_name="order_confirmation_email.html",
            context=context
        )
    
    def send_admin_welcome_email(
        self,
        email: EmailStr,
        username: str,
        password: str,
        role: str = "Admin",
        admin_panel_url: Optional[str] = None
    ) -> bool:
        """Send welcome email to new admin user"""
        context = {
            'username': username,
            'email': email,
            'password': password,
            'role': role,
            'admin_panel_url': admin_panel_url or f"{settings.FRONTEND_URL}/admin",
            'creation_date': datetime.now(tz=timezone.utc).strftime("%B %d, %Y at %I:%M %p UTC"),
            'header_subtitle': 'Administrator access granted'
        }
        
        return self.send_template_email(
            to_email=email,
            subject="Welcome to Shoppersky Admin Panel 👑",
            template_name="admin_welcome_email.html",
            context=context
        )
    
    def send_vendor_onboarding_email(
        self,
        email: EmailStr,
        vendor_name: str,
        business_name: str,
        reference_number: str,
        status: str = "Active",
        vendor_portal_url: Optional[str] = None,
        support_phone: Optional[str] = None
    ) -> bool:
        """Send onboarding email to new vendor"""
        context = {
            'vendor_name': vendor_name,
            'business_name': business_name,
            'email': email,
            'reference_number': reference_number,
            'status': status,
            'vendor_portal_url': vendor_portal_url or f"{settings.FRONTEND_URL}/vendor",
            'creation_date': datetime.now(tz=timezone.utc).strftime("%B %d, %Y at %I:%M %p UTC"),
            'support_phone': support_phone,
            'header_subtitle': 'Your vendor account is ready',
            'current_year': datetime.now(tz=timezone.utc).year
        }
        
        return self.send_template_email(
            to_email=email,
            subject="Welcome to Shoppersky Vendor Portal 🏪",
            template_name="vendor_onboarding_email.html",
            context=context
        )
    
    def send_vendor_verification_email(
        self,
        vendor_email: EmailStr,
        vendor_name: str,
        verification_token: str,
        business_name: str = "Your Business",
        verification_link: Optional[str] = None,
        expiry_minutes: int = 30
    ) -> bool:
        """Send verification email to vendor with token - UPDATED VERSION"""
        context = {
            'vendor_name': vendor_name,
            'vendor_email': vendor_email,
            'business_name': business_name,
            'verification_token': verification_token,
            'verification_link': verification_link or f"{settings.FRONTEND_URL}/emailconfirmation?token={verification_token}",
            'expiry_minutes': expiry_minutes,
            'registration_date': datetime.now(tz=timezone.utc).strftime("%B %d, %Y at %I:%M %p UTC"),
            'header_subtitle': 'Verify your vendor account to get started'
        }
        
        return self.send_template_email(
            to_email=vendor_email,
            subject="Verify Your Shoppersky Vendor Account",
            template_name="vendor_verification_email.html",
            context=context
        )
    
    def send_custom_email(
        self,
        to_email: EmailStr,
        subject: str,
        message: str,
        is_html: bool = False
    ) -> bool:
        """Send custom email with plain text or HTML content"""
        if is_html:
            return self.send_html_email(to_email, subject, message)
        else:
            # For plain text, create simple HTML wrapper
            html_content = f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <pre style="white-space: pre-wrap; font-family: Arial, sans-serif;">{message}</pre>
                        <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
                        <p style="color: #666; font-size: 12px;">
                            © {datetime.now(tz=timezone.utc).year} Shoppersky. All rights reserved.
                        </p>
                    </div>
                </body>
            </html>
            """
            return self.send_html_email(to_email, subject, html_content, message)
    
    def send_bulk_email(
        self,
        recipients: List[EmailStr],
        subject: str,
        template_name: str,
        context: Dict[str, Any],
        personalize: bool = False
    ) -> Dict[str, bool]:
        """Send bulk emails to multiple recipients"""
        results = {}
        
        for email in recipients:
            try:
                email_context = context.copy()
                if personalize and 'recipients_data' in context:
                    # Look for personalized data for this email
                    recipient_data = context['recipients_data'].get(email, {})
                    email_context.update(recipient_data)
                
                success = self.send_template_email(email, subject, template_name, email_context)
                results[email] = success
                
            except Exception as e:
                logger.error(f"Failed to send bulk email to {email}: {e}")
                results[email] = False
        
        return results


# Create global instance
email_service = EmailTemplateService()


# Convenience functions for backward compatibility
def send_welcome_email(email: EmailStr, username: str, password: str, logo_url: str = "") -> bool:
    """Send welcome email - backward compatible function"""
    return email_service.send_welcome_email(email, username, password)


def send_admin_password_reset_email(
    email: EmailStr,
    username: str,
    reset_link: str,
    expiry_minutes: int,
    ip_address: str,
    request_time: str,
) -> bool:
    """Send admin password reset email - backward compatible function"""
    return email_service.send_password_reset_email(
        email=email,
        username=username,
        reset_link=reset_link,
        expiry_minutes=expiry_minutes,
        ip_address=ip_address
    )


def send_vendor_verification_email(
    vendor_email: EmailStr,
    vendor_name: str,
    verification_token: str,
    business_name: str = "Your Business",
    verification_link: Optional[str] = None,
    expiry_minutes: int = 30
) -> bool:
    """Send vendor verification email - convenience function"""
    return email_service.send_vendor_verification_email(
        vendor_email=vendor_email,
        vendor_name=vendor_name,
        verification_token=verification_token,
        business_name=business_name,
        verification_link=verification_link,
        expiry_minutes=expiry_minutes
    )


def send_user_verification_email(
    email: EmailStr,
    username: str,
    verification_token: str,
    user_id: str,
    expires_in_minutes: int = 60
) -> bool:
    """Send user verification email with verification link"""
    try:
        print(f"Attempting to send verification email to: {email}")
        verification_link = f"{settings.FRONTEND_URL}/verify-email?token={verification_token}&user_id={user_id}"
        
        context = {
            'username': username,
            'email': email,
            'user_id': user_id,
            'verification_token': verification_token,
            'verification_code': verification_token[:8].upper(),  # First 8 chars as display code
            'verification_link': verification_link,
            'expiry_minutes': expires_in_minutes,
            'support_email': settings.SUPPORT_EMAIL,
            'company_name': 'Shoppersky',
            'current_year': datetime.now().year
        }
        
        print(f"Email context: {context}")
        
        # Check if SMTP is configured properly
        if settings.SMTP_USER == "your-email@gmail.com" or settings.SMTP_PASSWORD == "your-smtp-password":
            print("SMTP not configured properly - email sending disabled")
            print(f"Would send email to {email} with verification link: {verification_link}")
            return True  # Return True to not block registration
        
        result = email_service.send_template_email(
            to_email=email,
            subject="Welcome to Shoppersky - Please Verify Your Email",
            template_name="account_verification_email.html",
            context=context
        )
        
        print(f"Email send result: {result}")
        return result
        
    except Exception as e:
        print(f"Error sending verification email: {str(e)}")
        return False


def send_user_password_reset_email(
    email: EmailStr,
    username: str,
    reset_link: str,
    expiry_minutes: int,
    ip_address: str,
) -> bool:
    """Send user password reset email - backward compatible function"""
    return email_service.send_user_password_reset_email(
        email=email,
        username=username,
        reset_link=reset_link,
        expiry_minutes=expiry_minutes,
        ip_address=ip_address
    )


# Example usage functions
def send_test_email(to_email: EmailStr) -> bool:
    """Send a test email to verify email configuration"""
    context = {
        'username': 'Test User',
        'email': to_email,
        'password': 'TestPassword123',
        'login_url': settings.FRONTEND_URL
    }
    
    return email_service.send_template_email(
        to_email=to_email,
        subject="Test Email - Shoppersky Configuration",
        template_name="welcome_email.html",
        context=context
    )


def send_notification_email(
    to_email: EmailStr,
    title: str,
    message: str,
    action_url: Optional[str] = None,
    action_text: str = "View Details"
) -> bool:
    """Send a general notification email"""
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>{title}</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
            .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 5px 5px; }}
            .button {{ display: inline-block; background: #667eea; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
            .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>{title}</h1>
            </div>
            <div class="content">
                <p>{message}</p>
                {f'<a href="{action_url}" class="button">{action_text}</a>' if action_url else ''}
                <div class="footer">
                    <p>© {datetime.now(tz=timezone.utc).year} Shoppersky. All rights reserved.</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    return email_service.send_html_email(to_email, title, html_content)