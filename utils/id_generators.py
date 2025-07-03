import random
import secrets
import string

from typing_extensions import LiteralString

## for snos 
def generate_digits_uppercase(length: int = 6) -> str:
    """
    Generate a secure random string with digits and uppercase letters.

    Args:
        length (int): Length of the string to generate. Default is 6.

    Returns:
        str: A secure random string.
    """
    chars: LiteralString = string.digits + string.ascii_uppercase
    return "".join(secrets.choice(seq=chars) for _ in range(length))

## for affiliate id
def generate_digits_lowercase(length: int = 6) -> str:
    """
    Generate a secure random string with digits and lowercase letters.

    Args:
        length (int): Length of the string to generate. Default is 6.

    Returns:
        str: A secure random string.
    """
    chars: LiteralString = string.digits + string.ascii_lowercase
    return "".join(secrets.choice(seq=chars) for _ in range(length))

## for vendor id
def generate_digits_letters(length: int = 6) -> str:
    """
    Generate a secure random string with digits, lowercase and uppercase letters.

    Args:
        length (int): Length of the string to generate. Default is 6.

    Returns:
        str: A secure random string.
    """
    chars: LiteralString = string.ascii_lowercase + string.ascii_uppercase + string.digits
    return "".join(secrets.choice(seq=chars) for _ in range(length))
    
## for coupons
def generate_lower_uppercase(length: int = 8) -> str:
    """
    Generate a secure random string with lowercase and uppercase letters.

    Args:
        length (int): Length of the string to generate. Default is 8.

    Returns:
        str: A secure random string.
    """
    chars: LiteralString = string.ascii_lowercase + string.ascii_uppercase
    return "".join(secrets.choice(seq=chars) for _ in range(length))


## for product id's 
def generate_lowercase(length: int = 6) -> str:

    """
    Generate a secure random string with lowercase letters.

    Args:
        length (int): Length of the string to generate. Default is 6.

    Returns:
        str: A secure random string.
    """

    chars: LiteralString = string.ascii_lowercase
    return "".join(secrets.choice(seq=chars) for _ in range(length))


## for token

def random_token():
    # Generate random hexadecimal digits for each part of the UUID
    parts = [
        ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(4)),
        ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(3)),
        ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(4)),
        ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(5))
       
    ]
    
    # Combine the parts with hyphens in the specified format
    authtoken = '-'.join(parts)
    return authtoken