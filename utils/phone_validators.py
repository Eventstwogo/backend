"""
Contains phone number-related validation functions
"""

import re
from re import Pattern

import phonenumbers
from fastapi import HTTPException, status

# =============================================================================
# PHONE NUMBER VALIDATION CONSTANTS
# =============================================================================

OLD_PHONE_ERRORS: dict[str, str] = {
    "invalid_length": "Phone number must contain exactly 10 digits.",
    "leading_zeros": "Phone number cannot have more than one leading zero.",
    "sequential": "Phone number digits cannot be in sequential order.",
    "repetitive": "All digits in the phone number cannot be the same.",
}

PHONE_ERRORS: dict[str, str] = {
    "invalid_format": "Invalid phone number format.",
    "invalid_country_code": "Invalid or missing country code.",
    "invalid_length": "Phone number length is incorrect for the given country.",
    "leading_zeros": "Phone number cannot have multiple leading zeros.",
    "sequential": "Phone number digits cannot be in sequential order.",
    "repetitive": "Phone number cannot contain all identical digits.",
}

# Phone validation patterns
PHONE_PATTERN: Pattern[str] = re.compile(r"^\d{10}$")
SEQUENTIAL_PATTERNS: list[str] = [
    "0123456789",
    "1234567890",
    "9876543210",
    "0987654321",
    "1111111111",
    "2222222222",
    "3333333333",
    "4444444444",
    "5555555555",
    "6666666666",
    "7777777777",
    "8888888888",
    "9999999999",
    "0000000000",
]


# =============================================================================
# PHONE VALIDATOR CLASSES
# =============================================================================


class OldPhoneValidator:
    """
    Simple phone number validator for basic 10-digit phone numbers.

    This validator provides basic phone number validation with pattern matching
    and common validation rules for sequential and repetitive numbers.
    """

    @staticmethod
    def validate(phone_number: str) -> str:
        """
        Validates a phone number based on format and structure.

        Args:
            phone_number (str): The phone number to validate

        Returns:
            str: The validated and cleaned phone number

        Raises:
            HTTPException: If phone number fails validation
        """
        if phone_number.startswith("00"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=OLD_PHONE_ERRORS["leading_zeros"],
            )

        phone_number = re.sub(r"\s+|-|\+", "", phone_number.lstrip("0"))

        if not re.match(PHONE_PATTERN, phone_number):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=OLD_PHONE_ERRORS["invalid_length"],
            )

        if len(set(phone_number)) == 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=OLD_PHONE_ERRORS["repetitive"],
            )

        if phone_number in SEQUENTIAL_PATTERNS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=OLD_PHONE_ERRORS["sequential"],
            )

        return phone_number


class PhoneValidator:
    """
    Advanced phone number validator using the phonenumbers library.

    This validator provides comprehensive phone number validation with
    international format support and country-specific validation rules.
    """

    @staticmethod
    def validate(phone_number: str, country: str = "US") -> str:
        """
        Validates the given phone number based on format, length,
        and country code.

        Args:
            phone_number (str): The input phone number.
            country (str): The country code (default is "US").

        Returns:
            str: The formatted phone number if valid.

        Raises:
            HTTPException: If the phone number is invalid.
        """
        phone_number = phone_number.strip().replace(" ", "").replace("-", "")

        # Check for multiple leading zeros
        if phone_number.startswith("00"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=PHONE_ERRORS["leading_zeros"],
            )

        # Check for invalid sequential patterns
        if phone_number in SEQUENTIAL_PATTERNS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=PHONE_ERRORS["sequential"],
            )

        # Check if all digits are the same
        if len(set(phone_number)) == 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=PHONE_ERRORS["repetitive"],
            )

        # Parse phone number using phonenumbers library
        try:
            parsed_number = phonenumbers.parse(phone_number, country)
            if not phonenumbers.is_valid_number(parsed_number):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=PHONE_ERRORS["invalid_length"],
                )

            # Format the number into the international format
            formatted_number = phonenumbers.format_number(
                parsed_number, phonenumbers.PhoneNumberFormat.E164
            )
            return str(formatted_number)
        except phonenumbers.NumberParseException as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=PHONE_ERRORS["invalid_format"],
            ) from exc
