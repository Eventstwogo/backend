# import aiohttp
# from typing import Dict
# import logging

# logger = logging.getLogger(__name__)

# vault_url = "https://vault.shoppersky.com.au"
# vault_token = "hvs.NQlU47GLfI0GBt12JCtvuXf5"
# secret_path = "v1/kv/data/data"

# class VaultError(Exception):
#     """Exception raised for errors in fetching secrets from Vault."""
#     def __init__(self, message: str):
#         super().__init__(message)

# async def fetch_secrets_from_vault() -> Dict[str, str]:
#     """
#     Fetches database credentials stored in HashiCorp Vault.
#     """
#     if not vault_url or not vault_token or not secret_path:
#         raise VaultError("Vault configuration (URL, token, or secret path) is not set")
    
#     try:
#         headers = {
#             "X-Vault-Token": vault_token,
#             "Content-Type": "application/json",
#         }
#         url = f"{vault_url}/{secret_path}"
#         async with aiohttp.ClientSession() as session:
#             async with session.get(url, headers=headers) as response:
#                 if response.status == 200:
#                     response_data = await response.json()
#                     secrets = response_data["data"]["data"]
#                     logger.debug(f"Vault secrets: {secrets}")
#                     return {
#                         "DATABASE": secrets.get("DATABASE"),
#                         "DB_HOST": secrets.get("DB_HOST"),
#                         "DB_PASSWORD": secrets.get("DB_PASSWORD"),
#                         "DB_PORT": secrets.get("DB_PORT"),
#                         "SOURCE_DB_NAME": secrets.get("SOURCE_DB_NAME"),
#                         "DB_USER": secrets.get("DB_USER"),
#                         "SENDER_EMAIL": secrets.get("SENDER_EMAIL"),
#                         "SMTP_LOGIN": secrets.get("SMTP_LOGIN"),
#                         "SENDER_PASSWORD": secrets.get("SENDER_PASSWORD"),
#                         "SMTP_PORT": secrets.get("SMTP_PORT"),
#                         "SMTP_SERVER": secrets.get("SMTP_SERVER"),
#                         "SPACES_ACCESS_KEY": secrets.get("SPACES_ACCESS_KEY"),
#                         "SPACES_BUCKET_NAME": secrets.get("SPACES_BUCKET_NAME"),
#                         "SPACES_REGION_NAME": secrets.get("SPACES_REGION_NAME"),
#                         "SPACES_SECRET_KEY": secrets.get("SPACES_SECRET_KEY")
#                     }
#                 raise VaultError(f"Failed to fetch secrets. HTTP Status: {response.status}, Response: {await response.text()}")
#     except aiohttp.ClientError as e:
#         raise VaultError(f"HTTP Client Error: {str(e)}")
#     except KeyError as e:
#         raise VaultError(f"Missing expected key in Vault response: {str(e)}")
#     except Exception as e:
#         raise VaultError(f"Unexpected error fetching secrets from Vault: {str(e)}")



# core/secrets_dependencies.py

import aiohttp
import logging
from typing import Dict

logger = logging.getLogger(__name__)

VAULT_URL = "https://vault.shoppersky.com.au"
VAULT_TOKEN = "hvs.NQlU47GLfI0GBt12JCtvuXf5"  # ❗Replace with env or secure vault in production
SECRET_PATH = "v1/kv/data/data"


class VaultError(Exception):
    """Custom exception for Vault fetch errors."""
    pass


async def fetch_secrets_from_vault() -> Dict[str, str]:
    if not VAULT_URL or not VAULT_TOKEN or not SECRET_PATH:
        raise VaultError("Vault configuration is incomplete")

    try:
        headers = {
            "X-Vault-Token": VAULT_TOKEN,
            "Content-Type": "application/json",
        }
        url = f"{VAULT_URL}/{SECRET_PATH}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    raise VaultError(f"Vault request failed: {response.status}, {await response.text()}")

                data = await response.json()
                secrets = data["data"]["data"]
                logger.debug(f"✅ Vault secrets fetched: keys={list(secrets.keys())}")
                return secrets

    except aiohttp.ClientError as e:
        raise VaultError(f"HTTP error fetching Vault secrets: {str(e)}")
    except KeyError as e:
        raise VaultError(f"Malformed Vault response: missing key {str(e)}")
    except Exception as e:
        raise VaultError(f"Unexpected Vault error: {str(e)}")

