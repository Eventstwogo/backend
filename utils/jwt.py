from datetime import datetime, timedelta
import jwt
from pathlib import Path

PRIVATE_KEY_PATH = Path("keys/private_key.pem")  # Adjust path if needed
PUBLIC_KEY_PATH = Path("keys/public_key.pem")

with open(PRIVATE_KEY_PATH, "rb") as key_file:
    PRIVATE_KEY = key_file.read()

with open(PUBLIC_KEY_PATH, "rb") as key_file:
    PUBLIC_KEY = key_file.read()

ALGORITHM = "RS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 day

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, PRIVATE_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> dict:
    """
    Decode and verify JWT token
    
    Args:
        token: JWT token string
        
    Returns:
        dict: Decoded token payload
        
    Raises:
        jwt.ExpiredSignatureError: If token is expired
        jwt.InvalidTokenError: If token is invalid
    """
    try:
        payload = jwt.decode(token, PUBLIC_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise jwt.ExpiredSignatureError("Token has expired")
    except jwt.InvalidTokenError:
        raise jwt.InvalidTokenError("Invalid token")
