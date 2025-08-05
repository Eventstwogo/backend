
import logging
from logging import Logger

# Configure logging
logging.basicConfig(level=logging.INFO)
logger: Logger = logging.getLogger(__name__)

import json
import os
from functools import lru_cache
from typing import List, Literal, Dict, Any

from dotenv import load_dotenv
from pydantic import SecretBytes, SecretStr, EmailStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from core.secrets_dependencies import fetch_secrets_from_vault
from keys.key_manager import KeyManager

# # Remove environment variable override for database settings
# os.environ.pop("ENVIRONMENT", None)  # Prevent override
# load_dotenv(dotenv_path=".env.local", override=True)

class Settings(BaseSettings):
    """
    Application-wide configuration settings.
    Loaded from environment variables, .env files, or Vault.
    """

    # === General ===
    APP_NAME: str = "FastAPI Application"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: Literal["development", "testing", "production"] = "development"
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8000
    LOG_LEVEL: str = "info"
    DEBUG: bool = True
    ADMIN_FRONTEND_URL: str = "https://admin.shoppersky.com.au"
    VENDOR_FRONTEND_URL: str = "https://vendor.shoppersky.com.au"
    USERS_APPLICATION_FRONTEND_URL: str = "https://shoppersky.com.au"
    DESCRIPTION: str = (
        "Shoppersky application for managing products, users and their purchases."
    )

    # === Database ===
    POSTGRES_DRIVER: str = "asyncpg"
    POSTGRES_SCHEME: str = "postgresql"
    POSTGRES_HOST: str = "192.168.0.207"  # Will be set by Vault
    POSTGRES_PORT: int = 5432  # Will be set by Vault
    POSTGRES_USER: str = "postgres"  # Will be set by Vault
    POSTGRES_PASSWORD: str = "postgres"  # Will be set by Vault
    POSTGRES_DB: str = "shoppersky"  # Will be set by Vault

    # === Vault Configuration ===
    VAULT_URL: str = os.getenv("VAULT_URL", "http://localhost:8200")
    VAULT_TOKEN: str = os.getenv("VAULT_TOKEN", "")
    VAULT_SECRET_PATH: str = os.getenv("VAULT_SECRET_PATH", "v1/kv/data/secrets")

    @property
    def DATABASE_URL(self) -> str:
        """Builds the SQLAlchemy-compatible database URL."""
        return (
           
           f"{self.POSTGRES_SCHEME}+{self.POSTGRES_DRIVER}://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

        )

    # === CORS ===
    ALLOWED_ORIGINS: str = "http://localhost,http://localhost:3000"

    @property
    def CORS_ORIGINS(self) -> List[str]:
        try:
            parsed = json.loads(self.ALLOWED_ORIGINS)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    # === Media ===
    MEDIA_ROOT: str = "media/"
    MEDIA_BASE_URL: str = "https://shoppersky.syd1.digitaloceanspaces.com/"  # Updated to Spaces
    DEFAULT_MEDIA_URL: str = "config/logo/abcd1234.png"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10 MB
    ALLOWED_MEDIA_TYPES: List[str] = [
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "image/svg+xml",
    ]

    CATEGORY_IMAGE_PATH: str = "categories/{slug_name}/"
    SUBCATEGORY_IMAGE_PATH: str = "subcategories/{category_id}/{slug_name}/"
    CONFIG_LOGO_PATH: str = "config/logo/"
    PROFILE_PICTURE_UPLOAD_PATH: str = "users/profile_pictures/{username}_avatar"

    # === Email Configuration ===
    # SMTP Connection Settings
    SMTP_TLS: bool = True
    SMTP_SSL: bool = False  # Set to True for port 465
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_USER: str = os.getenv("SMTP_USER", "your-email@gmail.com")
    SMTP_PASSWORD: SecretStr = SecretStr(os.getenv("SMTP_PASSWORD", "your-smtp-password"))
    
    # Email Identity Settings
    EMAIL_FROM: str = os.getenv("EMAIL_FROM", "your-email@gmail.com")
    EMAIL_FROM_NAME: str = os.getenv("EMAIL_FROM_NAME", "Shoppersky Team")
    SUPPORT_EMAIL: str = os.getenv("SUPPORT_EMAIL", "support@shoppersky.com")
    
    # Email Template Settings
    EMAIL_TEMPLATES_DIR: str = "templates"
    EMAIL_TIMEOUT: int = 30  # SMTP timeout in seconds
    EMAIL_MAX_RETRIES: int = 3  # Maximum retry attempts for failed emails
    
    # Email Provider Presets (for easy switching)
    EMAIL_PROVIDER: Literal["gmail", "sendgrid", "brevo", "ses", "custom"] = "gmail"
    
    @property
    def EMAIL_CONFIG(self) -> Dict[str, Any]:
        """Get email configuration based on provider"""
        provider_configs = {
            "gmail": {
                "SMTP_HOST": "smtp.gmail.com",
                "SMTP_PORT": 587,
                "SMTP_TLS": True,
                "SMTP_SSL": False
            },
            "sendgrid": {
                "SMTP_HOST": "smtp.sendgrid.net", 
                "SMTP_PORT": 587,
                "SMTP_TLS": True,
                "SMTP_SSL": False
            },
            "brevo": {
                "SMTP_HOST": "smtp-relay.brevo.com",
                "SMTP_PORT": 587,
                "SMTP_TLS": True,
                "SMTP_SSL": False
            },
            "ses": {
                "SMTP_HOST": "email-smtp.us-east-1.amazonaws.com",  # Default region
                "SMTP_PORT": 587,
                "SMTP_TLS": True,
                "SMTP_SSL": False
            },
            "custom": {
                "SMTP_HOST": self.SMTP_HOST,
                "SMTP_PORT": self.SMTP_PORT,
                "SMTP_TLS": self.SMTP_TLS,
                "SMTP_SSL": self.SMTP_SSL
            }
        }
        
        config = provider_configs.get(self.EMAIL_PROVIDER, provider_configs["custom"])
        return {
            **config,
            "SMTP_USER": self.SMTP_USER,
            "SMTP_PASSWORD": self.SMTP_PASSWORD.get_secret_value() if isinstance(self.SMTP_PASSWORD, SecretStr) else self.SMTP_PASSWORD,
            "EMAIL_FROM": str(self.EMAIL_FROM),
            "EMAIL_FROM_NAME": self.EMAIL_FROM_NAME,
            "SUPPORT_EMAIL": str(self.SUPPORT_EMAIL),
            "EMAIL_TIMEOUT": self.EMAIL_TIMEOUT,
            "EMAIL_MAX_RETRIES": self.EMAIL_MAX_RETRIES
        }

    # === JWT ===
    JWT_ALGORITHM: str = "RS256"
    JWT_ACCESS_TOKEN_EXPIRE_SECONDS: int = 3600
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_KEYS_DIR: str = "keys"
    JWT_ISSUER: str = "shoppersky-api"
    JWT_AUDIENCE: str = "shoppersky-admin"

    # === DigitalOcean Spaces ===
    SPACES_REGION_NAME: str = "syd1"
    SPACES_ENDPOINT_URL: str = f"https://{SPACES_REGION_NAME}.digitaloceanspaces.com"
    SPACES_BUCKET_NAME: str = "shoppersky"
    SPACES_ACCESS_KEY_ID: str = "spaces-access-key-id"
    SPACES_SECRET_ACCESS_KEY: str = "spaces-secret-access-key"

    @property
    def SPACES_PUBLIC_URL(self) -> str:
        return (
            f"{self.SPACES_ENDPOINT_URL.rstrip('/')}/{self.SPACES_BUCKET_NAME}"
        )

    # === Meta Configuration for Pydantic ===
    model_config = SettingsConfigDict(
        env_file=".env.production",
        env_file_encoding="utf-8",
        extra="allow",
    )

    async def load_vault_secrets(self):
        """Load secrets from Vault using the new secrets management system"""
        try:
            from core.secrets import get_secrets_manager
            
            secrets_manager = get_secrets_manager()
            secrets = await secrets_manager.fetch_secrets()
            
            logger.info(f"🔐 Loading secrets from {'Vault' if secrets_manager.is_vault_available else 'environment variables'}")
            
            # Update database settings
            self.POSTGRES_DB = secrets.get("POSTGRES_DB", self.POSTGRES_DB)
            self.POSTGRES_HOST = secrets.get("POSTGRES_HOST", self.POSTGRES_HOST)
            self.POSTGRES_PASSWORD = secrets.get("POSTGRES_PASSWORD", self.POSTGRES_PASSWORD)
            self.POSTGRES_PORT = int(secrets.get("POSTGRES_PORT", self.POSTGRES_PORT))
            self.POSTGRES_USER = secrets.get("POSTGRES_USER", self.POSTGRES_USER)
            
            # Validate database credentials
            if not all([self.POSTGRES_USER, self.POSTGRES_PASSWORD, self.POSTGRES_HOST, self.POSTGRES_DB]):
                raise ValueError(f"Missing database credentials: user={bool(self.POSTGRES_USER)}, password={bool(self.POSTGRES_PASSWORD)}, host={bool(self.POSTGRES_HOST)}, db={bool(self.POSTGRES_DB)}")
            
            # Update email settings with proper type handling
            self.SMTP_PORT = int(secrets.get("SMTP_PORT", self.SMTP_PORT))
            self.SMTP_HOST = secrets.get("SMTP_HOST", self.SMTP_HOST)
            self.SMTP_USER = secrets.get("SMTP_USER", self.SMTP_USER)
            
            # Handle SecretStr for password
            smtp_password = secrets.get("SMTP_PASSWORD", self.SMTP_PASSWORD)
            if isinstance(smtp_password, str):
                self.SMTP_PASSWORD = SecretStr(smtp_password)
            elif not isinstance(self.SMTP_PASSWORD, SecretStr):
                self.SMTP_PASSWORD = SecretStr(str(self.SMTP_PASSWORD))
            
            # Update email addresses
            email_from = secrets.get("EMAIL_FROM", self.EMAIL_FROM)
            if isinstance(email_from, str) and email_from:
                self.EMAIL_FROM = email_from
                
            support_email = secrets.get("SUPPORT_EMAIL", self.SUPPORT_EMAIL)
            if isinstance(support_email, str) and support_email:
                self.SUPPORT_EMAIL = support_email
                
            self.EMAIL_FROM_NAME = secrets.get("EMAIL_FROM_NAME", self.EMAIL_FROM_NAME)
            
            # Update DigitalOcean Spaces settings
            self.SPACES_REGION_NAME = secrets.get("SPACES_REGION_NAME", self.SPACES_REGION_NAME)
            self.SPACES_BUCKET_NAME = secrets.get("SPACES_BUCKET_NAME", self.SPACES_BUCKET_NAME)
            self.SPACES_ACCESS_KEY_ID = secrets.get("SPACES_ACCESS_KEY_ID", self.SPACES_ACCESS_KEY_ID)
            self.SPACES_SECRET_ACCESS_KEY = secrets.get("SPACES_SECRET_ACCESS_KEY", self.SPACES_SECRET_ACCESS_KEY)
            
            logger.info(f"✅ Configuration updated - DB: {self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}, Email: {self.SMTP_HOST}:{self.SMTP_PORT}")
            
        except Exception as e:
            logger.error(f"❌ Failed to load secrets: {e}")
            # Continue with existing configuration from environment variables
            logger.warning("⚠️  Continuing with environment variable configuration")

@lru_cache()
def get_settings() -> Settings:
    settings = Settings()
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
    return settings

# Load settings synchronously for module-level access
settings: Settings = get_settings()

# KeyManager initialization for JWT
key_manager = KeyManager(
    key_dir=settings.JWT_KEYS_DIR,
    key_refresh_days=settings.REFRESH_TOKEN_EXPIRE_DAYS,
)

PRIVATE_KEY = SecretBytes(key_manager.get_private_key())
PUBLIC_KEY = SecretBytes(key_manager.get_public_key())






