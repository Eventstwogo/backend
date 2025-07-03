from typing import Dict

import aiohttp


class VaultError(Exception):
    """Exception raised for errors in fetching secrets from Vault."""

    def __init__(self, message: str):
        super().__init__(message)


# Function to fetch database credentials from Vault asynchronously
async def fetch_secrets_from_vault(
    vault_url: str, vault_token: str, secret_path: str
) -> Dict[str, str]:
    """
    Fetches database credentials stored in HashiCorp Vault.

    Parameters:
        vault_url (str): The URL of the HashiCorp Vault server.
        vault_token (str): The token used for authenticating with Vault.
        secret_path (str): The path to the secret in Vault.
                        Defaults to "v1/kv/data/shoudb".

    Returns:
        Dict[str, str]: A dictionary containing the database credentials.

    Raises:
        VaultError: If there's an error in fetching the credentials or
        the response is invalid.
    """
    try:
        # Define the headers for the Vault API request
        headers = {
            "X-Vault-Token": vault_token,  # Vault authentication token
            "Content-Type": "application/json",
        }

        # Construct the full URL for the Vault API
        url = f"{vault_url}/{secret_path}"

        # Perform an async GET request to fetch the secret data
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                # Check if the response status is successful (HTTP 200)
                if response.status == 200:
                    # Parse the JSON response
                    response_data = await response.json()

                    # Extract the `data` field containing secrets
                    secrets = response_data["data"]["data"]

                    # Return the extracted secrets in a structured dictionary
                    return {
                        "DATABASE": secrets.get("DATABASE"),
                        "DB_HOST": secrets.get("DB_HOST"),
                        "DB_PASSWORD": secrets.get("DB_PASSWORD"),
                        "DB_PORT": secrets.get("DB_PORT"),
                        "SOURCE_DB_NAME": secrets.get("SOURCE_DB_NAME"),
                        "PLAIN_PASSWORD": secrets.get("PLAIN_PASSWORD"),
                        "HOME_DB_NAME": secrets.get("HOME_DB_NAME"),
                        "SENDER_EMAIL": secrets.get("SENDER_EMAIL"),
                        "SENDER_PASSWORD": secrets.get("SENDER_PASSWORD"),
                        "SMTP_PORT": secrets.get("SMTP_PORT"),
                        "SMTP_SERVER": secrets.get("SMTP_SERVER"),
                        "SPACES_ACCESS_KEY": secrets.get("SPACES_ACCESS_KEY"),
                        "SPACES_BUCKET_NAME": secrets.get("SPACES_BUCKET_NAME"),
                        "SPACES_REGION_NAME": secrets.get("SPACES_REGION_NAME"),
                        "SPACES_SECRET_KEY": secrets.get("SPACES_SECRET_KEY"),
                        "CORS_ORIGINS": secrets.get("CORS_ORIGINS"),
                    }

                # Raise a specific error if the response status is not 200
                raise VaultError(
                    f"Failed to fetch secrets. HTTP Status: {response.status}"
                )

    except aiohttp.ClientError as e:
        # Handle HTTP client errors specifically
        raise VaultError(f"HTTP Client Error: {str(e)}")
    except KeyError as e:
        # Handle missing keys in the response data
        raise VaultError(f"Missing expected key in Vault response: {str(e)}")
    except Exception as e:
        # Raise a VaultError for any other unexpected exceptions
        raise VaultError(
            f"Unexpected error fetching secrets from Vault: {str(e)}"
        )
