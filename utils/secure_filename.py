import os
import re
from urllib.parse import quote


def secure_filename(input_str: str, uri_safe: bool = False) -> str:
    """
    Generates a secure, cross-platform-safe filename from user input.

    Parameters:
    - input_str (str): The raw input string.
    - uri_safe (bool): If True, returns URI-encoded filename using percent encoding.

    Returns:
    - str: A safe filename suitable for file saving.
    """
    # Remove directory traversal
    input_str = os.path.basename(input_str)

    # Replace spaces with underscore
    input_str = input_str.replace(" ", "_")

    # Remove all characters except safe ones
    # Allow: alphanumeric, underscore, hyphen, and period
    input_str = re.sub(r"[^\w\-.]", "", input_str)

    # Optionally encode as URI-safe
    if uri_safe:
        input_str = quote(input_str)

    return input_str
