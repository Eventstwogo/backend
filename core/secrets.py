import os
from typing import Dict

import requests
from dotenv import load_dotenv

# Load environment variables from .env.production file
load_dotenv(dotenv_path=".env.production")


class VaultError(Exception):
    """Exception raised for errors in fetching secrets from Vault."""

    def __init__(self, message: str):
        super().__init__(message)


def fetch_vault_secrets_sync() -> Dict[str, str]:
    """
    Fetch secrets from Vault synchronously using requests.

    Expects VAULT_URL, VAULT_TOKEN, and VAULT_SECRET_PATH as environment variables.
    """
    try:
        # Read required environment variables
        vault_url = os.getenv("VAULT_URL", "https://vault.shoppersky.com.au")
        vault_token = os.getenv("VAULT_TOKEN", "hvs.")
        vault_secret_path = os.getenv("VAULT_SECRET_PATH", "kv/data/data")

        if not all([vault_url, vault_token, vault_secret_path]):
            raise VaultError(
                "Vault URL, Token, or Secret Path is missing in environment variables"
            )

        # Construct URL and headers
        headers = {
            "X-Vault-Token": vault_token,
            "Content-Type": "application/json",
        }
        url = f"{vault_url}/v1/{vault_secret_path}"

        # Send GET request to Vault
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            raise VaultError(
                f"Failed to fetch secrets. HTTP Status: {response.status_code}"
            )

        response_data = response.json()

        # Extract secrets
        secrets = response_data["data"]["data"]

        # Optional: inject into os.environ
        for key, value in secrets.items():
            if value is not None:
                os.environ[key] = str(value)
                print(f"Injected {key}: {value}")

        return {
            "DATABASE": secrets.get("DATABASE"),
            "DB_HOST": secrets.get("DB_HOST"),
            "DB_PASSWORD": secrets.get("DB_PASSWORD"),
            "DB_PORT": secrets.get("DB_PORT"),
            "SOURCE_DB_NAME": secrets.get("SOURCE_DB_NAME"),
            "SENDER_EMAIL": secrets.get("SENDER_EMAIL"),
            "SENDER_PASSWORD": secrets.get("SENDER_PASSWORD"),
            "SMTP_LOGIN": secrets.get("SMTP_LOGIN"),
            "SMTP_PORT": secrets.get("SMTP_PORT"),
            "SMTP_SERVER": secrets.get("SMTP_SERVER"),
            "SPACES_ACCESS_KEY": secrets.get("SPACES_ACCESS_KEY"),
            "SPACES_BUCKET_NAME": secrets.get("SPACES_BUCKET_NAME"),
            "SPACES_REGION_NAME": secrets.get("SPACES_REGION_NAME"),
            "SPACES_SECRET_KEY": secrets.get("SPACES_SECRET_KEY"),
            "FERNET_KEY": secrets.get("FERNET_KEY"),
        }

    except requests.RequestException as e:
        raise VaultError(f"HTTP Request error: {str(e)}")
    except KeyError as e:
        raise VaultError(f"Missing expected key in Vault response: {str(e)}")
    except Exception as e:
        raise VaultError(
            f"Unexpected error fetching secrets from Vault: {str(e)}"
        )
