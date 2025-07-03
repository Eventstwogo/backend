
import re

from fastapi import HTTPException


def validate_password(Id_password: str):
        if 8 <= len(Id_password) <= 12:
            if any(c.islower() for c in Id_password) and \
                any(c.isupper() for c in Id_password) and \
                any(c.isdigit() for c in Id_password) and \
                any(c in '!@#$%^&*()-_=+[]{}|;:,.<>?/~`' for c in Id_password):
                return {"status_code": 200, "message": "Password is valid."}
            return {"status_code": 400, "message": "Password must contain atleast one Uppercase, one Lowercase, one Digit, one Special Character."}
        return {"status_code": 400, "message": "Password length must be between 8 and 12 characters."}


def validate_name(input_name: str, field_name: str) -> str:
    cleaned_name = input_name.strip()
    if not re.match(r'^[A-Za-z0-9\s!@#$%^&*(),.?":{}|<>_-]+$', cleaned_name):
        raise HTTPException(status_code=400, detail=f"{field_name} should contain only letters, digits and special characters.")
    return cleaned_name
