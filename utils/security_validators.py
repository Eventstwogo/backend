import html
import re
from typing import Any, Optional

from utils.validators import has_excessive_repetition

# =============================================================================
# SECURITY VALIDATORS
# =============================================================================


def escape_html(content: str) -> str:
    """
    Escapes HTML tags from user input to prevent XSS attacks.

    Args:
        content (str): The input string to escape

    Returns:
        str: HTML-escaped string

    Use cases:
        - Sanitizing user input before displaying in web pages
        - Preventing XSS attacks in form submissions
        - Safe rendering of user-generated content

    Example:
        >>> escape_html('<script>alert("xss")</script>')
        '&lt;script&gt;alert("xss")&lt;/script&gt;'
    """
    return html.escape(s=content)


def contains_xss(content: str) -> bool:
    """
    Detects potential XSS (Cross-Site Scripting) attempts in content.

    Args:
        content (str): The content to check for XSS patterns

    Returns:
        bool: True if XSS-like script tags are found, False otherwise

    Use cases:
        - Pre-validation of user input before processing
        - Content filtering in forums and comment systems
        - Security auditing of user-submitted data

    Example:
        >>> contains_xss('<script>alert("hack")</script>')
        True
        >>> contains_xss('Hello world')
        False
    """
    content_lower: str = content.lower()
    return bool(re.search(r"<\s*script[^>]*>", content_lower))


def contains_sql_injection(content: str) -> bool:
    """
    Detects potential SQL injection patterns in content.

    Args:
        content (str): The content to check for SQL injection patterns

    Returns:
        bool: True if SQL injection keywords are detected, False otherwise

    Use cases:
        - Input validation for database queries
        - Security filtering for search forms
        - Preventing SQL injection attacks

    Example:
        >>> contains_sql_injection("'; DROP TABLE users; --")
        True
        >>> contains_sql_injection('normal search term')
        False
    """
    sql_keywords: list[str] = [
        "select",
        "insert",
        "update",
        "delete",
        "drop",
        "truncate",
        "exec",
        "union",
        "--",
        ";",
        "or 1=1",
        "' or",
        '" or',
    ]
    content_lower: str = content.lower()
    return any(keyword in content_lower for keyword in sql_keywords)


def sanitize_input(content: Optional[str]) -> str:
    """
    Fully sanitizes user input:
    - Removes <script> tags and their content (XSS protection)
    - Strips all other HTML tags
    - Escapes HTML special characters (&, <, >, etc.)
    - Removes basic SQL injection characters (", ', ;, `, --)

    Args:
        content (Optional[str]): Raw user input

    Returns:
        str: Safe, sanitized string
    """
    if not content:
        return ""

    # Trim whitespace
    content = content.strip()

    # Remove <script>...</script> content
    content = re.sub(
        r"<script.*?>.*?</script>", "", content, flags=re.IGNORECASE | re.DOTALL
    )

    # Remove all other HTML tags
    content = re.sub(r"<.*?>", "", content)

    # Escape HTML special characters
    content = html.escape(content)

    # Remove common SQL injection characters
    content = re.sub(r"[\"';`]|--", "", content)

    return content.strip()


def validate_strict_input(field_name: str, value: Any) -> None:
    """
    Performs strict validation with exception raising for invalid inputs.

    Args:
        field_name (str): Name of the field being validated (for error messages)
        value (Any): The value to validate

    Raises:
        ValueError: If validation fails with specific error message

    Use cases:
        - Form validation with detailed error reporting
        - API input validation
        - Strict data integrity checks

    Example:
        >>> validate_strict_input('username', '<script>alert("xss")</script>')
        ValueError: username contains potentially malicious content.
    """
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string.")
    if contains_xss(value):
        raise ValueError(
            f"{field_name} contains potentially malicious content."
        )
    if contains_sql_injection(value):
        raise ValueError(f"{field_name} contains SQL injection patterns.")
    if has_excessive_repetition(value):
        raise ValueError(
            f"{field_name} contains excessive or too many repeated characters."
        )
