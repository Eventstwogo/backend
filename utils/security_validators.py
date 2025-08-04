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
        bool: True if XSS-like patterns are found, False otherwise

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
    
    # Common XSS patterns
    xss_patterns = [
        r"<\s*script[^>]*>",           # <script> tags
        r"<\s*iframe[^>]*>",          # <iframe> tags
        r"<\s*object[^>]*>",          # <object> tags
        r"<\s*embed[^>]*>",           # <embed> tags
        r"<\s*form[^>]*>",            # <form> tags
        r"javascript\s*:",            # javascript: protocol
        r"vbscript\s*:",              # vbscript: protocol
        r"data\s*:",                  # data: protocol
        r"on\w+\s*=",                 # event handlers (onclick, onload, etc.)
        r"expression\s*\(",           # CSS expression()
        r"<\s*meta[^>]*http-equiv",   # meta refresh
        r"<\s*link[^>]*>",            # link tags
        r"<\s*style[^>]*>",           # style tags
    ]
    
    return any(re.search(pattern, content_lower) for pattern in xss_patterns)


def contains_sql_injection(content: str) -> bool:
    """
    Detects potential SQL injection patterns in content.

    Args:
        content (str): The content to check for SQL injection patterns

    Returns:
        bool: True if SQL injection patterns are detected, False otherwise

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
    content_lower: str = content.lower()
    
    # SQL injection patterns
    sql_patterns = [
        r"'\s*or\s+",                    # ' OR
        r'"\s*or\s+',                    # " OR
        r";\s*drop\s+",                  # ; DROP
        r";\s*delete\s+",                # ; DELETE
        r";\s*insert\s+",                # ; INSERT
        r";\s*update\s+",                # ; UPDATE
        r";\s*create\s+",                # ; CREATE
        r";\s*alter\s+",                 # ; ALTER
        r";\s*truncate\s+",              # ; TRUNCATE
        r"union\s+select",               # UNION SELECT
        r"exec\s*\(",                    # EXEC(
        r"execute\s*\(",                 # EXECUTE(
        r"sp_\w+",                       # stored procedures
        r"xp_\w+",                       # extended procedures
        r"--\s*",                        # SQL comments
        r"/\*.*\*/",                     # SQL block comments
        r"'\s*;\s*--",                   # '; --
        r'"\s*;\s*--',                   # "; --
        r"or\s+1\s*=\s*1",              # OR 1=1
        r"and\s+1\s*=\s*1",             # AND 1=1
        r"'\s*=\s*'",                    # '='
        r'"\s*=\s*"',                    # "="
        r"char\s*\(",                    # CHAR(
        r"ascii\s*\(",                   # ASCII(
        r"substring\s*\(",               # SUBSTRING(
        r"waitfor\s+delay",              # WAITFOR DELAY
        r"benchmark\s*\(",               # BENCHMARK(
        r"sleep\s*\(",                   # SLEEP(
    ]
    
    return any(re.search(pattern, content_lower) for pattern in sql_patterns)


def sanitize_input(content: Optional[str]) -> str:
    """
    Fully sanitizes user input:
    - Removes dangerous HTML tags and their content (XSS protection)
    - Strips all other HTML tags
    - Escapes HTML special characters (&, <, >, etc.)
    - Removes SQL injection characters and patterns
    - Removes JavaScript protocols and event handlers

    Args:
        content (Optional[str]): Raw user input

    Returns:
        str: Safe, sanitized string
    """
    if not content:
        return ""

    # Trim whitespace
    content = content.strip()

    # Remove dangerous HTML tags and their content
    dangerous_tags = [
        r"<script.*?>.*?</script>",
        r"<iframe.*?>.*?</iframe>",
        r"<object.*?>.*?</object>",
        r"<embed.*?>.*?</embed>",
        r"<form.*?>.*?</form>",
        r"<style.*?>.*?</style>",
        r"<link.*?>",
        r"<meta.*?>",
    ]
    
    for tag_pattern in dangerous_tags:
        content = re.sub(tag_pattern, "", content, flags=re.IGNORECASE | re.DOTALL)

    # Remove all other HTML tags
    content = re.sub(r"<.*?>", "", content)

    # Remove JavaScript and VBScript protocols
    content = re.sub(r"javascript\s*:", "", content, flags=re.IGNORECASE)
    content = re.sub(r"vbscript\s*:", "", content, flags=re.IGNORECASE)
    content = re.sub(r"data\s*:", "", content, flags=re.IGNORECASE)

    # Remove event handlers
    content = re.sub(r"on\w+\s*=\s*[\"'][^\"']*[\"']", "", content, flags=re.IGNORECASE)

    # Escape HTML special characters
    content = html.escape(content)

    # Remove SQL injection characters and patterns
    content = re.sub(r"[\"';`]|--", "", content)
    content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)

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
