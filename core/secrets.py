"""
Enhanced Secrets Management System for Shoppersky
Supports HashiCorp Vault with fallback to environment variables
"""

import asyncio
import logging
import os
from functools import lru_cache
from typing import Dict, Optional, Any
import aiohttp
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class VaultConfig(BaseModel):
    """Vault configuration settings"""
    url: str = Field(default_factory=lambda: os.getenv("VAULT_URL", "http://localhost:8200"))
    token: str = Field(default_factory=lambda: os.getenv("VAULT_TOKEN", ""))
    secret_path: str = Field(default_factory=lambda: os.getenv("VAULT_SECRET_PATH", "v1/kv/data/secrets"))
    timeout: int = Field(default=10)
    max_retries: int = Field(default=3)


class SecretsError(Exception):
    """Custom exception for secrets management errors"""
    pass


class SecretsManager:
    """
    Enhanced secrets manager with Vault integration and fallback support
    """
    
    def __init__(self, vault_config: Optional[VaultConfig] = None):
        self.vault_config = vault_config or VaultConfig()
        self._secrets_cache: Optional[Dict[str, Any]] = None
        self._vault_available = False
        
        # Email secrets mapping from Vault to application keys
        self.email_secrets_mapping = {
            "SENDER_EMAIL": "EMAIL_FROM",
            "SENDER_PASSWORD": "SMTP_PASSWORD", 
            "SMTP_LOGIN": "SMTP_USER",
            "SMTP_PORT": "SMTP_PORT",
            "SMTP_SERVER": "SMTP_HOST",
            "EMAIL_FROM_NAME": "EMAIL_FROM_NAME",
            "SUPPORT_EMAIL": "SUPPORT_EMAIL"
        }
        
        # Database secrets mapping
        self.database_secrets_mapping = {
            "DB_HOST": "POSTGRES_HOST",
            "DB_PORT": "POSTGRES_PORT", 
            "DB_USER": "POSTGRES_USER",
            "DB_PASSWORD": "POSTGRES_PASSWORD",
            "SOURCE_DB_NAME": "POSTGRES_DB",
            "DATABASE": "POSTGRES_USER"  # Fallback for user
        }
        
        # DigitalOcean Spaces secrets mapping
        self.spaces_secrets_mapping = {
            "SPACES_ACCESS_KEY": "SPACES_ACCESS_KEY_ID",
            "SPACES_SECRET_KEY": "SPACES_SECRET_ACCESS_KEY",
            "SPACES_BUCKET_NAME": "SPACES_BUCKET_NAME",
            "SPACES_REGION_NAME": "SPACES_REGION_NAME"
        }

    async def _fetch_from_vault(self) -> Dict[str, Any]:
        """
        Fetch secrets from HashiCorp Vault asynchronously
        """
        if not all([self.vault_config.url, self.vault_config.token, self.vault_config.secret_path]):
            raise SecretsError("Vault configuration is incomplete (missing URL, token, or secret path)")

        headers = {
            "X-Vault-Token": self.vault_config.token,
            "Content-Type": "application/json",
        }
        
        url = f"{self.vault_config.url}/{self.vault_config.secret_path}"
        
        for attempt in range(self.vault_config.max_retries):
            try:
                timeout = aiohttp.ClientTimeout(total=self.vault_config.timeout)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url, headers=headers) as response:
                        if response.status == 200:
                            data = await response.json()
                            secrets = data.get("data", {}).get("data", {})
                            logger.info(f"✅ Successfully fetched {len(secrets)} secrets from Vault")
                            self._vault_available = True
                            return secrets
                        elif response.status == 403:
                            raise SecretsError(f"Vault access denied (403). Check token permissions.")
                        elif response.status == 404:
                            raise SecretsError(f"Vault secret path not found (404): {self.vault_config.secret_path}")
                        else:
                            error_text = await response.text()
                            raise SecretsError(f"Vault request failed: HTTP {response.status} - {error_text}")
                            
            except aiohttp.ClientError as e:
                logger.warning(f"Vault connection attempt {attempt + 1} failed: {e}")
                if attempt == self.vault_config.max_retries - 1:
                    raise SecretsError(f"Failed to connect to Vault after {self.vault_config.max_retries} attempts: {e}")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                
            except Exception as e:
                raise SecretsError(f"Unexpected error fetching from Vault: {e}")

    def _get_env_fallback(self, key: str, default: Any = None) -> Any:
        """
        Get value from environment variables with type conversion
        """
        value = os.getenv(key, default)
        
        # Convert string values to appropriate types
        if isinstance(value, str):
            # Handle boolean values
            if value.lower() in ('true', 'false'):
                return value.lower() == 'true'
            # Handle integer values for ports
            if key.endswith('_PORT') and value.isdigit():
                return int(value)
                
        return value

    async def fetch_secrets(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Fetch secrets with Vault priority and environment fallback
        
        Priority order:
        1. HashiCorp Vault (if available)
        2. Environment variables
        3. Default values
        """
        if self._secrets_cache and not force_refresh:
            return self._secrets_cache

        secrets = {}
        vault_secrets = {}
        
        # Try to fetch from Vault first
        try:
            vault_secrets = await self._fetch_from_vault()
            logger.info("🔐 Using secrets from HashiCorp Vault")
        except SecretsError as e:
            logger.warning(f"⚠️  Vault unavailable, falling back to environment variables: {e}")
            self._vault_available = False

        # Combine all secret mappings
        all_mappings = {
            **self.email_secrets_mapping,
            **self.database_secrets_mapping, 
            **self.spaces_secrets_mapping
        }

        # Process each secret with fallback logic
        for vault_key, app_key in all_mappings.items():
            # Priority 1: Vault secrets
            if vault_key in vault_secrets:
                secrets[app_key] = vault_secrets[vault_key]
                continue
                
            # Priority 2: Environment variables (try both vault key and app key)
            env_value = self._get_env_fallback(vault_key) or self._get_env_fallback(app_key)
            if env_value is not None:
                secrets[app_key] = env_value
                continue
                
            # Priority 3: Default values for critical settings
            defaults = self._get_default_values()
            if app_key in defaults:
                secrets[app_key] = defaults[app_key]
                logger.debug(f"Using default value for {app_key}")

        # Add additional secrets that might be in Vault but not mapped
        for key, value in vault_secrets.items():
            if key not in all_mappings and value is not None:
                secrets[key] = value

        self._secrets_cache = secrets
        logger.info(f"📋 Loaded {len(secrets)} configuration secrets")
        return secrets

    def _get_default_values(self) -> Dict[str, Any]:
        """Default values for critical configuration"""
        return {
            "SMTP_HOST": "smtp.gmail.com",
            "SMTP_PORT": 587,
            "EMAIL_FROM_NAME": "Shoppersky Team",
            "SUPPORT_EMAIL": "support@shoppersky.com",
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": 5432,
            "POSTGRES_DB": "shoppersky",
            "SPACES_REGION_NAME": "syd1"
        }

    def get_secret(self, key: str, default: Any = None) -> Any:
        """
        Synchronous method to get a specific secret
        Uses cached secrets if available, otherwise returns environment variable or default
        """
        if self._secrets_cache and key in self._secrets_cache:
            return self._secrets_cache[key]
            
        # Fallback to environment variable
        return self._get_env_fallback(key, default)

    @property
    def is_vault_available(self) -> bool:
        """Check if Vault is available and working"""
        return self._vault_available

    def get_email_config(self) -> Dict[str, Any]:
        """Get email-specific configuration"""
        if not self._secrets_cache:
            # If no cache, try to get from environment
            return {
                "SMTP_HOST": self._get_env_fallback("SMTP_HOST", "smtp.gmail.com"),
                "SMTP_PORT": self._get_env_fallback("SMTP_PORT", 587),
                "SMTP_USER": self._get_env_fallback("SMTP_USER", ""),
                "SMTP_PASSWORD": self._get_env_fallback("SMTP_PASSWORD", ""),
                "EMAIL_FROM": self._get_env_fallback("EMAIL_FROM", ""),
                "EMAIL_FROM_NAME": self._get_env_fallback("EMAIL_FROM_NAME", "Shoppersky Team"),
                "SUPPORT_EMAIL": self._get_env_fallback("SUPPORT_EMAIL", "support@shoppersky.com")
            }
            
        # Return from cache
        return {
            key: self._secrets_cache.get(key, default)
            for key, default in [
                ("SMTP_HOST", "smtp.gmail.com"),
                ("SMTP_PORT", 587),
                ("SMTP_USER", ""),
                ("SMTP_PASSWORD", ""),
                ("EMAIL_FROM", ""),
                ("EMAIL_FROM_NAME", "Shoppersky Team"),
                ("SUPPORT_EMAIL", "support@shoppersky.com")
            ]
        }


# Global secrets manager instance
@lru_cache()
def get_secrets_manager() -> SecretsManager:
    """Get cached secrets manager instance"""
    return SecretsManager()


# Synchronous wrapper for Pydantic settings
def fetch_secrets_sync() -> Dict[str, Any]:
    """
    Synchronous wrapper for fetching secrets
    Used by Pydantic settings during application startup
    """
    try:
        # Try to get existing event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is running, we can't use run_until_complete
            # Return environment variables as fallback
            logger.warning("Event loop is running, using environment variables for secrets")
            manager = get_secrets_manager()
            return {
                key: manager._get_env_fallback(key)
                for key in [
                    "SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD",
                    "EMAIL_FROM", "EMAIL_FROM_NAME", "SUPPORT_EMAIL",
                    "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_USER", 
                    "POSTGRES_PASSWORD", "POSTGRES_DB",
                    "SPACES_ACCESS_KEY_ID", "SPACES_SECRET_ACCESS_KEY",
                    "SPACES_BUCKET_NAME", "SPACES_REGION_NAME"
                ]
            }
    except RuntimeError:
        # No event loop exists, create one
        pass
    
    # Create new event loop for fetching secrets
    try:
        manager = get_secrets_manager()
        return asyncio.run(manager.fetch_secrets())
    except Exception as e:
        logger.error(f"Failed to fetch secrets synchronously: {e}")
        # Return environment variables as final fallback
        manager = get_secrets_manager()
        return manager.get_email_config()


# Async function for use in application lifespan
async def initialize_secrets() -> Dict[str, Any]:
    """
    Initialize secrets during application startup
    """
    manager = get_secrets_manager()
    secrets = await manager.fetch_secrets()
    logger.info(f"🔐 Secrets initialization complete. Vault available: {manager.is_vault_available}")
    return secrets