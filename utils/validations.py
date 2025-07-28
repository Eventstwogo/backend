
import re
import secrets
import string

from fastapi import HTTPException


def validate_password(Id_password: str):
    # Check length first
    if not (8 <= len(Id_password) <= 12):
        return {"status_code": 400, "message": "Password length must be between 8 and 12 characters."}
    
    # Check for lowercase letter
    if not any(c.islower() for c in Id_password):
        return {"status_code": 400, "message": "Password must contain at least one lowercase letter."}
    
    # Check for uppercase letter
    if not any(c.isupper() for c in Id_password):
        return {"status_code": 400, "message": "Password must contain at least one uppercase letter."}
    
    # Check for digit
    if not any(c.isdigit() for c in Id_password):
        return {"status_code": 400, "message": "Password must contain at least one digit."}
    
    # Check for special character
    if not any(c in '!@#$%^&*()-_=+[]{}|;:,.<>?/~`' for c in Id_password):
        return {"status_code": 400, "message": "Password must contain at least one special character (!@#$%^&*()-_=+[]{}|;:,.<>?/~`)."}
    
    return {"status_code": 200, "message": "Password is valid."}


def validate_name(input_name: str, field_name: str) -> str:
    cleaned_name = input_name.strip()
    if not re.match(r'^[A-Za-z0-9\s!@#$%^&*(),.?":{}|<>_-]+$', cleaned_name):
        raise HTTPException(status_code=400, detail=f"{field_name} should contain only letters, digits and special characters.")
    return cleaned_name


def generate_random_password(length: int = 12) -> str:
    chars = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(chars) for _ in range(length))