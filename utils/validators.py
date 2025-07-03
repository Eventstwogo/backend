"""
Validation utilities for input sanitization, format validation, character type validation, etc.
"""

import keyword
import re
import unicodedata
from typing import List, Optional

# =============================================================================
# CHARACTER TYPE VALIDATORS
# =============================================================================


def is_meaningful(value: Optional[str]) -> bool:
    return bool(value and value.strip())


def is_alpha(content: str) -> bool:
    """
    Validates if content contains only alphabetic characters and spaces.

    Args:
        content (str): Content to validate

    Returns:
        bool: True if only alphabetic characters and spaces, False otherwise

    Use cases:
        - Name field validation
        - Text-only input validation
        - Language content filtering

    Example:
        >>> is_alpha('John Doe')
        True
        >>> is_alpha('John123')
        False
    """
    return bool(re.fullmatch(r"[A-Za-z\s]+", content))


def is_numeric(content: str) -> bool:
    """
    Validates if content contains only numeric characters.

    Args:
        content (str): Content to validate

    Returns:
        bool: True if only numeric characters, False otherwise

    Use cases:
        - ID number validation
        - Quantity input validation
        - Numeric code validation

    Example:
        >>> is_numeric('12345')
        True
        >>> is_numeric('123abc')
        False
    """
    return bool(re.fullmatch(r"\d+", content))


def is_alphanumeric(content: str) -> bool:
    """
    Validates if content contains only alphanumeric characters.

    Args:
        content (str): Content to validate

    Returns:
        bool: True if only alphanumeric characters, False otherwise

    Use cases:
        - Username validation
        - Product code validation
        - Identifier validation

    Example:
        >>> is_alphanumeric('User123')
        True
        >>> is_alphanumeric('User-123')
        False
    """
    return bool(re.fullmatch(r"[A-Za-z0-9]+", content))


def is_english_letters_only(text: str) -> bool:
    """
    Validates if text contains only English letters and spaces.

    Args:
        text (str): Text to validate

    Returns:
        bool: True if only English letters and spaces, False otherwise

    Use cases:
        - English-only content validation
        - Language-specific form validation
        - Text filtering for specific locales

    Example:
        >>> is_english_letters_only('Hello World')
        True
        >>> is_english_letters_only('Hëllo')
        False
    """
    return bool(re.fullmatch(r"[A-Za-z\s]+", text))


def contains_special_chars(text: str) -> bool:
    """
    Checks if text contains special characters.

    Args:
        text (str): Text to check

    Returns:
        bool: True if special characters are found, False otherwise

    Use cases:
        - Password complexity checking
        - Input sanitization decisions
        - Content filtering

    Example:
        >>> contains_special_chars('Hello!')
        True
        >>> contains_special_chars('Hello')
        False
    """
    return bool(re.search(r"[!@#$%^&*(),.?\":{}|<>]", text))


def is_all_upper(text: str) -> bool:
    """
    Checks if all alphabetic characters in text are uppercase.

    Args:
        text (str): Text to check

    Returns:
        bool: True if all letters are uppercase, False otherwise

    Use cases:
        - Format validation for codes/IDs
        - Style consistency checking
        - Data normalization validation

    Example:
        >>> is_all_upper('HELLO WORLD')
        True
        >>> is_all_upper('Hello World')
        False
    """
    return text.isupper()


def is_all_lower(text: str) -> bool:
    """
    Checks if all alphabetic characters in text are lowercase.

    Args:
        text (str): Text to check

    Returns:
        bool: True if all letters are lowercase, False otherwise

    Use cases:
        - Email validation (some systems require lowercase)
        - URL slug validation
        - Consistent formatting checks

    Example:
        >>> is_all_lower('hello world')
        True
        >>> is_all_lower('Hello World')
        False
    """
    return text.islower()


def is_whitespace_only(text: str) -> bool:
    """
    Checks if text contains only whitespace characters.

    Args:
        text (str): Text to check

    Returns:
        bool: True if only whitespace, False otherwise

    Use cases:
        - Empty input detection
        - Form validation (preventing whitespace-only submissions)
        - Data cleaning validation

    Example:
        >>> is_whitespace_only('   ')
        True
        >>> is_whitespace_only('Hello')
        False
    """
    return not text.strip()


# =============================================================================
# LENGTH VALIDATORS
# =============================================================================


def validate_length(
    content: str, min_length: int = 1, max_length: int = 255
) -> bool:
    """
    Validates if string length is within specified range.

    Args:
        content (str): Content to validate
        min_length (int): Minimum allowed length (default: 1)
        max_length (int): Maximum allowed length (default: 255)

    Returns:
        bool: True if length is within range, False otherwise

    Use cases:
        - Form field validation
        - Database constraint validation
        - Input length enforcement

    Example:
        >>> validate_length('Hello', 3, 10)
        True
        >>> validate_length('Hi', 3, 10)
        False
    """
    return min_length <= len(content.strip()) <= max_length


def validate_min_length(text: str, min_len: int) -> bool:
    """
    Validates minimum length requirement.

    Args:
        text (str): Text to validate
        min_len (int): Minimum required length

    Returns:
        bool: True if meets minimum length, False otherwise

    Use cases:
        - Password minimum length validation
        - Comment minimum length enforcement
        - Required field validation

    Example:
        >>> validate_min_length('password123', 8)
        True
        >>> validate_min_length('pass', 8)
        False
    """
    return len(text.strip()) >= min_len


def validate_max_length(text: str, max_len: int) -> bool:
    """
    Validates maximum length constraint.

    Args:
        text (str): Text to validate
        max_len (int): Maximum allowed length

    Returns:
        bool: True if within maximum length, False otherwise

    Use cases:
        - Database field length validation
        - Tweet/message length validation
        - Form input constraints

    Example:
        >>> validate_max_length('Short text', 50)
        True
        >>> validate_max_length('Very long text...', 10)
        False
    """
    return len(text.strip()) <= max_len


def validate_length_range(text: str, min_len: int, max_len: int) -> bool:
    """
    Validates length within a specific range (inclusive).

    Args:
        text (str): Text to validate
        min_len (int): Minimum required length
        max_len (int): Maximum allowed length

    Returns:
        bool: True if length is within range, False otherwise

    Use cases:
        - Username length validation
        - Product name validation
        - Description field validation

    Example:
        >>> validate_length_range('username', 5, 20)
        True
        >>> validate_length_range('usr', 5, 20)
        False
    """
    length = len(text.strip())
    return min_len <= length <= max_len


# =============================================================================
# CONTENT PATTERN VALIDATORS
# =============================================================================


def has_excessive_repetition(content: str, max_repeats: int = 2) -> bool:
    """
    Checks for excessive character repetition in content.

    Args:
        content (str): Content to check
        max_repeats (int): Maximum allowed consecutive repetitions (default: 2)

    Returns:
        bool: True if excessive repetition found, False otherwise

    Use cases:
        - Spam detection
        - Quality content validation
        - User input sanitization

    Example:
        >>> has_excessive_repetition('coool', 2)
        True
        >>> has_excessive_repetition('cool', 2)
        False
    """
    pattern = r"(.)\1{" + str(max_repeats) + ",}"
    return bool(re.search(pattern, content))


def is_valid_name(name: str) -> bool:
    """
    Validates proper name format (first/last/full names).

    Args:
        name (str): Name to validate

    Returns:
        bool: True if valid name format, False otherwise

    Use cases:
        - User registration validation
        - Contact form validation
        - Profile information validation

    Example:
        >>> is_valid_name('John Doe')
        True
        >>> is_valid_name('John123')
        False
    """
    return bool(re.fullmatch(r"[A-Za-z]+([ -][A-Za-z]+)*", name.strip()))


def is_valid_category_name(name: str) -> bool:
    """
    Validates category name format for content organization.

    Args:
        name (str): Category name to validate

    Returns:
        bool: True if valid category name, False otherwise

    Use cases:
        - Content management system validation
        - Product category validation
        - Navigation menu validation

    Example:
        >>> is_valid_category_name('Electronics')
        True
        >>> is_valid_category_name('Electronics & Gadgets')
        True
        >>> is_valid_category_name('Cat@gory!')
        False
    """
    return bool(re.fullmatch(r"^[A-Za-z0-9-_ ]{3,50}$", name.strip()))


def is_valid_subcategory_name(name: str) -> bool:
    """
    Validates subcategory name format with more flexible rules.

    Args:
        name (str): Subcategory name to validate

    Returns:
        bool: True if valid subcategory name, False otherwise

    Use cases:
        - Detailed content categorization
        - Product subcategory validation
        - Hierarchical navigation validation

    Example:
        >>> is_valid_subcategory_name('Mobile Phones & Accessories')
        True
        >>> is_valid_subcategory_name('Sub<category>')
        False
    """
    return bool(re.fullmatch(r"^[A-Za-z0-9 &/()-]{3,60}$", name.strip()))


def is_valid_username(
    value: str, allow_spaces: bool = True, allow_hyphens: bool = True
) -> bool:
    """
    Validates a username to ensure it only contains allowed characters.

    Args:
        value (str): The username to validate.
        allow_spaces (bool): If True, allows spaces in the username.
        allow_hyphens (bool): If True, allows hyphens (-) in the username.

    Returns:
        bool: True if the username is valid, False otherwise.
    """
    # Build allowed character set dynamically
    pattern = r"^[a-zA-Z0-9"
    if allow_spaces:
        pattern += r" "
    if allow_hyphens:
        pattern += r"\-"
    pattern += r"]+$"

    return bool(re.match(pattern, value))


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


def normalize_unicode(text: str) -> str:
    """
    Normalizes Unicode text for consistent storage and comparison.

    Args:
        text (str): Text to normalize

    Returns:
        str: Unicode-normalized text

    Use cases:
        - Database storage normalization
        - Text comparison operations
        - Search functionality improvement

    Example:
        >>> normalize_unicode('café')
        # Handles different Unicode representations
        'café'
    """
    return unicodedata.normalize("NFKC", text)


def normalize_whitespace(text: str) -> str:
    """
    Normalizes whitespace by removing extra spaces and trimming.

    Args:
        text (str): Text to normalize

    Returns:
        str: Text with normalized whitespace

    Use cases:
        - Input cleaning before storage
        - Text preprocessing for comparison
        - Data normalization

    Example:
        >>> normalize_whitespace('  Hello    World  ')
        'Hello World'
    """
    return re.sub(r"\s{2,}", " ", text.strip())


def strip_special_characters(text: str) -> str:
    """
    Removes all special characters, keeping only alphanumeric and spaces.

    Args:
        text (str): Text to clean

    Returns:
        str: Text with special characters removed

    Use cases:
        - Text sanitization for search
        - Creating clean identifiers
        - Data preprocessing

    Example:
        >>> strip_special_characters('Hello, World!')
        'Hello World'
    """
    return re.sub(r"[^A-Za-z0-9\s]", "", text)


def are_fields_equal(val1: str, val2: str) -> bool:
    """
    Compares two fields for equality after trimming whitespace.

    Args:
        val1 (str): First value to compare
        val2 (str): Second value to compare

    Returns:
        bool: True if values are equal after trimming, False otherwise

    Use cases:
        - Password confirmation validation
        - Email confirmation validation
        - Form field matching validation

    Example:
        >>> are_fields_equal('password123', 'password123 ')
        True
        >>> are_fields_equal('password123', 'different')
        False
    """
    return val1.strip() == val2.strip()


def has_duplicate_items(items: List[str]) -> bool:
    """
    Checks for duplicate items in a list after normalization.

    Args:
        items (List[str]): List of strings to check for duplicates

    Returns:
        bool: True if duplicates found, False otherwise

    Use cases:
        - Category/tag validation
        - List uniqueness validation
        - Data integrity checking

    Example:
        >>> has_duplicate_items(['apple', 'banana', 'Apple'])
        True
        >>> has_duplicate_items(['apple', 'banana', 'cherry'])
        False
    """
    normalized = [normalize_whitespace(item.lower()) for item in items]
    return len(normalized) != len(set(normalized))


# =============================================================================
# PYTHON RESERVED WORD VALIDATOR
# =============================================================================
EXTRA_RESERVED_WORDS = {"null", "none", "undefined", "nan"}


def is_single_reserved_word(name: Optional[str]) -> bool:
    """Return True if the input is a single reserved word (Python or custom)."""
    if not name:
        return False
    words = name.strip().split()
    reserved_words = set(kw.lower() for kw in keyword.kwlist).union(
        EXTRA_RESERVED_WORDS
    )
    return len(words) == 1 and words[0].lower() in reserved_words
