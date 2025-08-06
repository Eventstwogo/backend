import json
import os
from functools import lru_cache
from typing import Any, Dict, List, Literal, Tuple, Type

from dotenv import load_dotenv
from pydantic import SecretBytes
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from core.secrets import fetch_vault_secrets_sync
from keys.key_manager import KeyManager

# # Development only
# os.environ.pop("ENVIRONMENT", None)
# load_dotenv(dotenv_path=".env.local", override=True)


class VaultSettingsSource(PydanticBaseSettingsSource):
    """
    A custom Pydantic settings source that loads values from Vault.
    Maps Vault keys to app settings keys.
    """

    def __init__(self, settings_cls: Type[BaseSettings]) -> None:
        super().__init__(settings_cls)
        self._vault_data = None

    def _get_vault_data(self) -> Dict[str, Any]:
        """Lazy load vault data to avoid multiple calls."""
        if self._vault_data is None:
            self._vault_data = fetch_vault_secrets_sync()
        return self._vault_data

    def get_field_value(
        self, field: Any, field_name: str
    ) -> Tuple[Any, str, bool]:
        """
        Get field value from Vault data.
        Returns: (value, key, is_complex)
        """
        vault_data = self._get_vault_data()

        # Map field names to vault keys
        vault_key_mapping = {
            "POSTGRES_USER": "DATABASE",
            "POSTGRES_HOST": "DB_HOST",
            "POSTGRES_PASSWORD": "DB_PASSWORD",
            "POSTGRES_PORT": "DB_PORT",
            "POSTGRES_DB": "SOURCE_DB_NAME",
            "EMAIL_FROM": "SENDER_EMAIL",
            "SMTP_PASSWORD": "SENDER_PASSWORD",
            "SMTP_USER": "SMTP_LOGIN",
            "SMTP_PORT": "SMTP_PORT",
            "SMTP_HOST": "SMTP_SERVER",
            "SPACES_ACCESS_KEY_ID": "SPACES_ACCESS_KEY",
            "SPACES_BUCKET_NAME": "SPACES_BUCKET_NAME",
            "SPACES_REGION_NAME": "SPACES_REGION_NAME",
            "SPACES_SECRET_ACCESS_KEY": "SPACES_SECRET_KEY",
            "FERNET_KEY": "FERNET_KEY",
        }

        vault_key = vault_key_mapping.get(field_name)
        if vault_key and vault_key in vault_data:
            value = vault_data[vault_key]
            return value, field_name, False

        # Return None if field not found in vault
        return None, field_name, False

    def __call__(self) -> Dict[str, Any]:
        """Legacy method for backward compatibility."""
        vault_data = self._get_vault_data()

        return {
            "POSTGRES_USER": vault_data.get("DATABASE"),
            "POSTGRES_HOST": vault_data.get("DB_HOST"),
            "POSTGRES_PASSWORD": vault_data.get("DB_PASSWORD"),
            "POSTGRES_PORT": vault_data.get("DB_PORT"),
            "POSTGRES_DB": vault_data.get("SOURCE_DB_NAME"),
            "EMAIL_FROM": vault_data.get("SENDER_EMAIL"),
            "SMTP_PASSWORD": vault_data.get("SENDER_PASSWORD"),
            "SMTP_USER": vault_data.get("SMTP_LOGIN"),
            "SMTP_PORT": vault_data.get("SMTP_PORT"),
            "SMTP_HOST": vault_data.get("SMTP_SERVER"),
            "SPACES_ACCESS_KEY_ID": vault_data.get("SPACES_ACCESS_KEY"),
            "SPACES_BUCKET_NAME": vault_data.get("SPACES_BUCKET_NAME"),
            "SPACES_REGION_NAME": vault_data.get("SPACES_REGION_NAME"),
            "SPACES_SECRET_ACCESS_KEY": vault_data.get("SPACES_SECRET_KEY"),
            "FERNET_KEY": vault_data.get("FERNET_KEY"),
        }


class Settings(BaseSettings):
    """
    Application-wide configuration settings.
    Loaded from environment variables or .env files.
    """

    # === General ===
    APP_NAME: str = "ShopperSky App API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: Literal["development", "testing", "production"] = "development"
    APP_HOST: str = "0.0.0.0"  # nosec B104
    APP_PORT: int = 8000
    LOG_LEVEL: str = "info"
    ADMIN_FRONTEND_URL: str = "https://admin.shoppersky.com.au"
    VENDOR_FRONTEND_URL: str = "https://vendor.shoppersky.com.au"
    USERS_APPLICATION_FRONTEND_URL: str = "https://shoppersky.com.au"
    FRONTEND_URL: str = "https://shoppersky.com.au"  # Default frontend URL for emails
    DESCRIPTION: str = (
        "Shoppersky application for managing products, users and their purchases."
    )

    # === Database ===
    POSTGRES_DRIVER: str = "asyncpg"
    POSTGRES_SCHEME: str = "postgresql"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "shoppersky"

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

    # === DigitalOcean Spaces ===
    SPACES_REGION_NAME: str = "syd1"
    SPACES_ENDPOINT_URL: str = (
        f"https://{SPACES_REGION_NAME}.digitaloceanspaces.com"
    )
    SPACES_BUCKET_NAME: str = "shoppersky"
    SPACES_ACCESS_KEY_ID: str = "spaces-access-key-id"
    SPACES_SECRET_ACCESS_KEY: str = "spaces-secret-access-key"

    # === CORS ===
    ALLOWED_ORIGINS: str = "http://localhost,http://localhost:3000,https://www.shoppersky.com.au,https://admin.shoppersky.com.au,https://vendor.shoppersky.com.au"

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
        "image/avif",
        "image/jxl",
    ]

    CATEGORY_IMAGE_PATH: str = "categories/{slug_name}/"
    SUBCATEGORY_IMAGE_PATH: str = "subcategories/{category_id}/{slug_name}/"
    CONFIG_LOGO_PATH: str = "config/logo/"
    PROFILE_PICTURE_UPLOAD_PATH: str = (
        "users/profile_pictures/{username}_avatar"
    )
    EVENT_CARD_IMAGE_UPLOAD_PATH: str = "events/{event_id}/card_image"
    EVENT_BANNER_IMAGE_UPLOAD_PATH: str = "events/{event_id}/banner_image"
    EVENT_EXTRA_IMAGES_UPLOAD_PATH: str = "events/{event_id}/extra_images"

    # === JWT ===
    JWT_ALGORITHM: str = "RS256"
    JWT_ACCESS_TOKEN_EXPIRE_SECONDS: int = 3600
    REFRESH_TOKEN_EXPIRE_DAYS_IN_SECONDS: int = 604800
    JWT_KEYS_DIR: str = "keys"
    JWT_ISSUER: str = "shoppersky-api"
    JWT_AUDIENCE: str = "shoppersky-admin"

    # === AES256 Encryption ===
    FERNET_KEY: str = "fernet-key"

    # === Pydantic config ===
    model_config = SettingsConfigDict(
        env_file=".env.production",
        env_file_encoding="utf-8",
        extra="allow",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        return (
            VaultSettingsSource(settings_cls),
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )

    @property
    def SPACES_PUBLIC_URL(self) -> str:
        return (
            f"{self.SPACES_ENDPOINT_URL.rstrip('/')}/{self.SPACES_BUCKET_NAME}"
        )

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"{self.POSTGRES_SCHEME}+{self.POSTGRES_DRIVER}://"
            f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def CORS_ORIGINS(self) -> List[str]:
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


# === Singleton accessor (ensures one instance only) ===
@lru_cache()
def get_settings() -> Settings:
    settings_instance = Settings()  # Renamed to avoid redefinition warning

    # Automatically create media directory if it doesn't exist
    os.makedirs(settings_instance.MEDIA_ROOT, exist_ok=True)

    return settings_instance


# === Load settings ===
settings: Settings = get_settings()

# === KeyManager initialization for JWT ===
key_manager = KeyManager(
    key_dir=settings.JWT_KEYS_DIR,
    key_refresh_days=settings.REFRESH_TOKEN_EXPIRE_DAYS_IN_SECONDS,
)

PRIVATE_KEY = SecretBytes(key_manager.get_private_key())
PUBLIC_KEY = SecretBytes(key_manager.get_public_key())
