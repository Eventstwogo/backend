"""
Contains email-related validation functions
"""

import re
from re import Pattern
from typing import Tuple

from fastapi import HTTPException, status

EMAIL_REGEX: Pattern[str] = re.compile(
    r"^[a-zA-Z0-9+._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
)

EMAIL_ERRORS: dict[str, str] = {
    "invalid_format": "Invalid email address format.",
    "invalid_local": "Invalid characters in the local part of the email.",
    "invalid_domain": "Invalid domain part of the email.",
}

# =============================================================================
# EMAIL VALIDATOR CLASS
# =============================================================================


class EmailValidator:
    """
    Advanced email validation class with comprehensive validation rules.

    This class provides detailed email validation including local part,
    domain part, and length validation with specific error messages.
    """

    @staticmethod
    def validate(email: str) -> str:
        """
        Validates an email address against multiple criteria.

        :param email: The email address to validate
        :return: The sanitized and validated email address
        :raises HTTPException: If email fails validation
        """
        email = email.strip().lower()
        email = re.sub(r"\s", "", email)

        if not EMAIL_REGEX.fullmatch(email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=EMAIL_ERRORS["invalid_format"],
            )

        local_part, domain = EmailValidator._split_email(email)

        if not EmailValidator._is_valid_local_part(local_part):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=EMAIL_ERRORS["invalid_local"],
            )

        if not EmailValidator._is_valid_domain(domain):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=EMAIL_ERRORS["invalid_domain"],
            )

        EmailValidator._validate_length(local_part, domain)
        return email

    @staticmethod
    def _split_email(email: str) -> Tuple[str, str]:
        """
        Splits an email address into local and domain parts.
        """
        parts: list[str] = email.split(sep="@", maxsplit=1)
        return (parts[0], parts[1] if len(parts) > 1 else "")

    @staticmethod
    def _is_valid_local_part(local_part: str) -> bool:
        """
        Validates the local part of an email address.
        """
        if not (1 <= len(local_part) <= 64):
            return False
        if (
            ".." in local_part
            or local_part.startswith(".")
            or local_part.endswith(".")
        ):
            return False
        if re.search(r"[^a-zA-Z0-9+._-]", local_part):
            return False
        if any(char in local_part for char in "#$"):
            return False
        if local_part.startswith(("_", "-")) or local_part.endswith(("_", "-")):
            return False
        return True

    @staticmethod
    def _is_valid_domain(domain: str) -> bool:
        """
        Validates the domain part of an email address.
        """
        if len(domain) > 255:
            return False
        if domain.startswith("-") or domain.endswith("-"):
            return False
        if re.search(r"[^a-zA-Z0-9.-]", domain):
            return False
        if (
            re.search(r"[-+.]{2}", domain)
            or domain.endswith(".")
            or domain.endswith("+")
        ):
            return False
        return True

    @staticmethod
    def _validate_length(local_part: str, domain: str) -> None:
        """
        Checks the length constraints of the email parts.
        """
        if len(local_part) < 1 or len(local_part) > 64:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Local part must be between 1 and 64 characters. "
                    f"Provided: {len(local_part)}"
                ),
            )
        if len(domain) < 4 or len(domain) > 255:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Domain part must be between 4 and 255 characters. "
                    f"Provided: {len(domain)}"
                ),
            )
