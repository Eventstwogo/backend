
import logging
from logging import Logger

# Configure logging
logging.basicConfig(level=logging.INFO)
logger: Logger = logging.getLogger(__name__)

import json
import os
from functools import lru_cache
from typing import List, Literal

from dotenv import load_dotenv
from pydantic import SecretBytes
from pydantic_settings import BaseSettings, SettingsConfigDict
from core.secrets_dependencies import fetch_secrets_from_vault
from keys.key_manager import KeyManager

# Remove environment variable override for database settings
os.environ.pop("ENVIRONMENT", None)  # Prevent override
load_dotenv(dotenv_path=".env.local", override=True)

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
    FRONTEND_URL: str = "http://localhost:3000"
    DESCRIPTION: str = (
        "Shoppersky application for managing products, users and their purchases."
    )

    # === Database ===
    POSTGRES_DRIVER: str = "asyncpg"
    POSTGRES_SCHEME: str = "postgresql"
    POSTGRES_HOST: str = "192.168.0.207"  # Will be set by Vault
    POSTGRES_PORT: int = 5433  # Will be set by Vault
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

    # === Email ===
    SMTP_TLS: bool = True
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_USER: str = os.getenv("SMTP_USER", "your-email@gmail.com")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "your-smtp-password")
    EMAIL_FROM: str = os.getenv("EMAIL_FROM", "your-email@gmail.com")
    EMAIL_FROM_NAME: str = os.getenv("EMAIL_FROM_NAME", "Shoppersky API")
    EMAIL_TEMPLATES_DIR: str = "templates"
    SUPPORT_EMAIL: str = "support@shoppersky.com"

    # === JWT ===
    JWT_ALGORITHM: str = "RS256"
    JWT_ACCESS_TOKEN_EXPIRE_SECONDS: int = 3600
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_KEYS_DIR: str = "keys"
    JWT_ISSUER: str = "e2g-api"
    JWT_AUDIENCE: str = "e2g-admin"

    FERNET_KEY: str = ""

    # === DigitalOcean Spaces ===
    SPACES_REGION_NAME: str = "syd1"
    SPACES_ENDPOINT_URL: str = "https://syd1.digitaloceanspaces.com"
    SPACES_BUCKET_NAME: str = "shoppersky"
    SPACES_ACCESS_KEY_ID: str = "spaces-access-key-id"
    SPACES_SECRET_ACCESS_KEY: str = "spaces-secret-access-key"

    @property
    def SPACES_PUBLIC_URL(self) -> str:
        """Returns public URL to access the DigitalOcean Spaces bucket."""
        return f"https://{self.SPACES_BUCKET_NAME}.{self.SPACES_REGION_NAME}.digitaloceanspaces.com"

    # === Meta Configuration for Pydantic ===
    model_config = SettingsConfigDict(
        env_file=".env.local",
        env_file_encoding="utf-8",
        extra="allow",
    )

    async def load_vault_secrets(self):
        global vault_url, vault_token, secret_path
        vault_url = self.VAULT_URL
        vault_token = self.VAULT_TOKEN
        secret_path = self.VAULT_SECRET_PATH
        logger.info(f"Fetching secrets from Vault: {vault_url}/{secret_path}")
        secrets = await fetch_secrets_from_vault()
        logger.info(f"Raw secrets from Vault: {secrets}")
        self.POSTGRES_DB = secrets.get("SOURCE_DB_NAME", self.POSTGRES_DB)
        self.POSTGRES_HOST = secrets.get("DB_HOST", self.POSTGRES_HOST)
        self.POSTGRES_PASSWORD = secrets.get("DB_PASSWORD", self.POSTGRES_PASSWORD)
        self.POSTGRES_PORT = int(secrets.get("DB_PORT", self.POSTGRES_PORT))
        self.POSTGRES_USER = secrets.get("DB_USER", self.POSTGRES_USER)
        if not self.POSTGRES_USER:
            self.POSTGRES_USER = secrets.get("DATABASE", self.POSTGRES_USER)
        if not all([self.POSTGRES_USER, self.POSTGRES_PASSWORD, self.POSTGRES_HOST, self.POSTGRES_DB]):
            raise ValueError(f"Missing database credentials after Vault fetch: user={self.POSTGRES_USER}, host={self.POSTGRES_HOST}, port={self.POSTGRES_PORT}, db={self.POSTGRES_DB}, secrets={secrets}")
        self.SMTP_PORT = int(secrets.get("SMTP_PORT", self.SMTP_PORT))
        self.SMTP_HOST = secrets.get("SMTP_SERVER", self.SMTP_HOST)
        self.SMTP_USER = secrets.get("SMTP_LOGIN", self.SMTP_USER)
        self.SMTP_PASSWORD = secrets.get("SENDER_PASSWORD", self.SMTP_PASSWORD)
        self.EMAIL_FROM = secrets.get("SENDER_EMAIL", self.EMAIL_FROM)
        self.SPACES_REGION_NAME = secrets.get("SPACES_REGION_NAME", self.SPACES_REGION_NAME)
        self.SPACES_BUCKET_NAME = secrets.get("SPACES_BUCKET_NAME", self.SPACES_BUCKET_NAME)
        self.SPACES_ACCESS_KEY_ID = secrets.get("SPACES_ACCESS_KEY", self.SPACES_ACCESS_KEY_ID)
        self.SPACES_SECRET_ACCESS_KEY = secrets.get("SPACES_SECRET_KEY", self.SPACES_SECRET_ACCESS_KEY)
        self.FERNET_KEY = secrets.get("FERNET_KEY", self.FERNET_KEY)
        print(self.FERNET_KEY)
        logger.info(f"Updated database settings: user={self.POSTGRES_USER}, host={self.POSTGRES_HOST}, port={self.POSTGRES_PORT}, db={self.POSTGRES_DB}")

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






