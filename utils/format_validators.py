import json
import os
import re
import string
from typing import Dict, Union

from fastapi import status

# =============================================================================
# FORMAT VALIDATORS
# =============================================================================


def is_valid_email(email: str) -> bool:
    """
    Validates email address format.

    Args:
        email (str): Email address to validate

    Returns:
        bool: True if email format is valid, False otherwise

    Use cases:
        - User registration validation
        - Contact form validation
        - Email list verification

    Example:
        >>> is_valid_email('user@example.com')
        True
        >>> is_valid_email('invalid-email')
        False
    """
    return bool(re.fullmatch(r"^[\w\.-]+@[\w\.-]+\.\w{2,}$", email))


def is_strong_password(password: str) -> bool:
    """
    Validates password strength requirements.

    Requirements:
        - At least 8 characters
        - At least 1 uppercase letter
        - At least 1 lowercase letter
        - At least 1 number
        - At least 1 special character

    Args:
        password (str): Password to validate

    Returns:
        bool: True if password meets strength requirements, False otherwise

    Use cases:
        - User registration password validation
        - Password change validation
        - Security policy enforcement

    Example:
        >>> is_strong_password('MyPass123!')
        True
        >>> is_strong_password('weak')
        False
    """
    pattern = (
        r"^(?=.*[a-z])"  # at least one lowercase letter
        r"(?=.*[A-Z])"  # at least one uppercase letter
        r"(?=.*\d)"  # at least one digit
        r"(?=.*[@$!%*?&#])"  # at least one special character
        r"[A-Za-z\d@$!%*?&#]{8,}$"  # at least 8 characters total
    )
    return bool(re.fullmatch(pattern, password))


class PasswordValidator:
    """
    A utility class for validating passwords based on security criteria.
    """

    SPECIAL_CHARACTERS = set(string.punctuation)
    MIN_LENGTH = 8
    MAX_LENGTH = 14

    @staticmethod
    def is_strong_password(password: str) -> bool:
        """
        Quick boolean validation using regex.

        Requirements:
            - At least 8 characters
            - At least 1 uppercase letter
            - At least 1 lowercase letter
            - At least 1 number
            - At least 1 special character
        """
        pattern = (
            r"^(?=.*[a-z])"  # at least one lowercase letter
            r"(?=.*[A-Z])"  # at least one uppercase letter
            r"(?=.*\d)"  # at least one digit
            r"(?=.*[@$!%*?&#])"  # at least one special character
            r"[A-Za-z\d@$!%*?&#]{8,}$"  # at least 8 total characters
        )
        return bool(re.fullmatch(pattern, password))

    @classmethod
    def validate(cls, password: str) -> Dict[str, Union[int, str]]:
        """
        Full validation with error messages.

        :param password: Password to validate
        :return: Dictionary with status_code and message
        """
        if not cls.MIN_LENGTH <= len(password) <= cls.MAX_LENGTH:
            return {
                "status_code": status.HTTP_400_BAD_REQUEST,
                "message": (
                    f"Password length must be between {cls.MIN_LENGTH} and "
                    f"{cls.MAX_LENGTH} characters."
                ),
            }

        conditions = {
            "uppercase": any(c.isupper() for c in password),
            "lowercase": any(c.islower() for c in password),
            "digit": any(c.isdigit() for c in password),
            "special_character": any(
                c in cls.SPECIAL_CHARACTERS for c in password
            ),
        }

        if all(conditions.values()):
            return {
                "status_code": status.HTTP_200_OK,
                "message": "Password is valid.",
            }

        missing = [
            k.replace("_", " ").capitalize()
            for k, v in conditions.items()
            if not v
        ]

        return {
            "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "message": (
                "Password must contain at least one: " f"{', '.join(missing)}."
            ),
        }


def is_valid_phone(phone: str) -> bool:
    """
    Validates phone number format (international format supported).

    Args:
        phone (str): Phone number to validate

    Returns:
        bool: True if phone format is valid, False otherwise

    Use cases:
        - Contact information validation
        - User profile validation
        - SMS service integration

    Example:
        >>> is_valid_phone('+1234567890')
        True
        >>> is_valid_phone('123-456-7890')
        False
    """
    return bool(re.fullmatch(r"^\+?\d{7,15}$", phone))


def is_valid_url(url: str) -> bool:
    """
    Validates URL format (HTTP/HTTPS).

    Args:
        url (str): URL to validate

    Returns:
        bool: True if URL format is valid, False otherwise

    Use cases:
        - Link validation in forms
        - Social media profile validation
        - Website URL verification

    Example:
        >>> is_valid_url('https://example.com')
        True
        >>> is_valid_url('not-a-url')
        False
    """
    return bool(re.fullmatch(r"https?://[^\s]+", url))


def is_valid_ipv4(ip: str) -> bool:
    """
    Validates IPv4 address format.

    Args:
        ip (str): IP address to validate

    Returns:
        bool: True if IPv4 format is valid, False otherwise

    Use cases:
        - Network configuration validation
        - Server address validation
        - IP whitelist/blacklist management

    Example:
        >>> is_valid_ipv4('192.168.1.1')
        True
        >>> is_valid_ipv4('999.999.999.999')
        False
    """
    return bool(re.fullmatch(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$", ip))

def sanitize_filename(name: str, default_ext: str = "txt") -> str:
    """
    Sanitizes and returns a safe filename by removing invalid characters.

    Args:
        name (str): Input filename
        default_ext (str): Default extension to use if missing (default: 'txt')

    Returns:
        str: A safe, sanitized filename

    Examples:
        >>> sanitize_filename("file<>name?.pdf")
        'filename.pdf'
        >>> sanitize_filename("weird*name")
        'weirdname.txt'
    """
    # Split filename and extension
    base, ext = os.path.splitext(name)

    # Remove unwanted characters from base (keep letters, numbers, underscore, hyphen, space)
    base = re.sub(r"[^\w\s-]", "", base).strip()

    # Replace spaces with underscores (optional)
    base = re.sub(r"[\s]+", "_", base)

    # Sanitize extension: remove leading dot, allow only letters (1 to 5 chars)
    ext = re.sub(r"[^\w]", "", ext.lstrip("."))
    if not ext or len(ext) > 5:
        ext = default_ext

    # Ensure the base has at least one character
    if not base:
        base = "file"

    return f"{base}.{ext}"

def is_valid_hex_color(value: str) -> bool:
    """
    Validates hexadecimal color code format.

    Args:
        value (str): Color code to validate

    Returns:
        bool: True if hex color format is valid, False otherwise

    Use cases:
        - Theme customization validation
        - CSS color validation
        - Design tool input validation

    Example:
        >>> is_valid_hex_color('#FF5733')
        True
        >>> is_valid_hex_color('red')
        False
    """
    return bool(re.fullmatch(r"^#(?:[0-9a-fA-F]{3}){1,2}$", value))


def is_valid_credit_card_format(card_number: str) -> bool:
    """
    Validates credit card number format (format only, not Luhn algorithm).

    Args:
        card_number (str): Credit card number to validate

    Returns:
        bool: True if format is valid, False otherwise

    Use cases:
        - Payment form validation
        - E-commerce checkout validation
        - Financial data format checking

    Note:
        This only checks format, not actual card validity

    Example:
        >>> is_valid_credit_card_format('4111111111111111')
        True
        >>> is_valid_credit_card_format('123')
        False
    """
    return bool(re.fullmatch(r"\d{13,19}", card_number))


def is_valid_filename(name: str) -> bool:
    """
    Validates filename format for safe file operations.

    Args:
        name (str): Filename to validate

    Returns:
        bool: True if filename format is valid, False otherwise

    Use cases:
        - File upload validation
        - Document management systems
        - Safe file naming enforcement

    Example:
        >>> is_valid_filename('document.pdf')
        True
        >>> is_valid_filename('file<>name.txt')
        False
    """
    return bool(re.fullmatch(r"^[\w,\s-]+\.[A-Za-z]{1,5}$", name))


def is_valid_json_string(value: str) -> bool:
    """
    Validates if a string is valid JSON format.

    Args:
        value (str): String to validate as JSON

    Returns:
        bool: True if valid JSON, False otherwise

    Use cases:
        - API payload validation
        - Configuration file validation
        - Data import/export validation

    Example:
        >>> is_valid_json_string('{"key": "value"}')
        True
        >>> is_valid_json_string('invalid json')
        False
    """
    try:
        json.loads(value)
        return True
    except (json.JSONDecodeError, TypeError):
        return False
