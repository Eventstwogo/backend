import json
import os
from functools import lru_cache
from typing import List, Literal

from dotenv import load_dotenv
from pydantic import SecretBytes
from pydantic_settings import BaseSettings, SettingsConfigDict

from keys.key_manager import KeyManager

os.environ.pop("ENVIRONMENT", None)  # Prevent override
load_dotenv(dotenv_path=".env.local", override=True)


class Settings(BaseSettings):
    """
    Application-wide configuration settings.
    Loaded from environment variables or .env files.
    """

    # === General ===
    APP_NAME: str = "FastAPI Application"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: Literal["development", "testing", "production"] = "development"
    APP_HOST: str = "127.0.0.1"  # nosec B104
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
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5433
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "shoppersky"

    @property
    def DATABASE_URL(self) -> str:
        """Builds the SQLAlchemy-compatible database URL."""
        return (
            f"{self.POSTGRES_SCHEME}+{self.POSTGRES_DRIVER}://"
            f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # === CORS ===
    ALLOWED_ORIGINS: str = "http://localhost,http://localhost:3000"

    @property
    def CORS_ORIGINS(self) -> List[str]:
        """
        Parses ALLOWED_ORIGINS from either:
        - A JSON list (e.g., '["http://localhost", "http://localhost:3000"]')
        - Or a plain comma-separated string (e.g., 'http://localhost,http://localhost:3000')
        """
        try:
            parsed = json.loads(self.ALLOWED_ORIGINS)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass

        return [
            origin.strip()
            for origin in self.ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]

    # === Media ===
    MEDIA_ROOT: str = "media/"
    MEDIA_BASE_URL: str = "http://localhost:8000/media/"
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
    PROFILE_PICTURE_UPLOAD_PATH: str = (
        "users/profile_pictures/{username}_avatar"
    )

    # === Email ===
    SMTP_TLS: bool = True
    SMTP_PORT: int = 587
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_USER: str = "your-email@gmail.com"
    SMTP_PASSWORD: str = "your-smtp-password"
    EMAIL_FROM: str = "your-email@gmail.com"
    EMAIL_FROM_NAME: str = "Shoppersky API"
    EMAIL_TEMPLATES_DIR: str = "templates"
    SUPPORT_EMAIL: str = "support@shoppersky.com"
 

    # === JWT ===
    JWT_ALGORITHM: str = "RS256"
    JWT_ACCESS_TOKEN_EXPIRE_SECONDS: int = 3600
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_KEYS_DIR: str = "keys"
    JWT_ISSUER: str = "e2g-api"
    JWT_AUDIENCE: str = "e2g-admin"

    # === DigitalOcean Spaces ===
    SPACES_REGION_NAME: str = "nyc3"
    SPACES_ENDPOINT_URL: str = "https://nyc3.digitaloceanspaces.com"
    SPACES_BUCKET_NAME: str = "shoppersky"
    SPACES_ACCESS_KEY_ID: str = "spaces-access-key-id"
    SPACES_SECRET_ACCESS_KEY: str = "spaces-secret-access-key"

    @property
    def SPACES_PUBLIC_URL(self) -> str:
        """Returns public URL to access the DigitalOcean Spaces bucket."""
        return f"https://{self.SPACES_BUCKET_NAME}.digitaloceanspaces.com"

    # === Meta Configuration for Pydantic ===
    model_config = SettingsConfigDict(
        env_file=".env.local",
        env_file_encoding="utf-8",
        extra="allow",
    )


# === Singleton accessor (ensures one instance only) ===
@lru_cache()
def get_settings() -> Settings:
    settings = Settings()

    # Automatically create media directory if it doesn't exist
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

    return settings


# === Load settings ===
settings: Settings = get_settings()

# === KeyManager initialization for JWT ===
key_manager = KeyManager(
    key_dir=settings.JWT_KEYS_DIR,
    key_refresh_days=settings.REFRESH_TOKEN_EXPIRE_DAYS,
)

PRIVATE_KEY = SecretBytes(key_manager.get_private_key())
PUBLIC_KEY = SecretBytes(key_manager.get_public_key())
