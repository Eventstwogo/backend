from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union

import jwt
from fastapi import Cookie, Header, HTTPException, status
from passlib.context import CryptContext

from core.config import PUBLIC_KEY, settings
from core.logging_config import get_logger

logger = get_logger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# JWT Creation Function
def create_jwt_token(
    data: Dict[str, Any],
    private_key: Union[str, bytes],
    expires_in: int = settings.JWT_ACCESS_TOKEN_EXPIRE_SECONDS,
    issuer: Optional[str] = None,
    audience: Optional[str] = None,
    subject: Optional[str] = None,
) -> str:
    """
    Create an RS256-signed JWT token.

    Args:
        data (dict): Payload data.
        private_key (str/bytes): RSA private key.
        expires_in (int): Expiry time in seconds.
        issuer (str, optional): 'iss' claim.
        audience (str, optional): 'aud' claim.
        subject (str, optional): 'sub' claim.

    Returns:
        str: Encoded JWT token.

    Raises:
        RuntimeError: For any encoding issues.
    """
    if not data:
        raise ValueError("JWT payload cannot be empty.")
    if not private_key:
        raise ValueError("Private key is required to sign the JWT.")

    now = datetime.now(timezone.utc)
    payload = {
        **data,
        "exp": now + timedelta(seconds=expires_in),
        "iat": now,
        "nbf": now,
    }

    if issuer:
        payload["iss"] = issuer
    if audience:
        payload["aud"] = audience
    if subject:
        payload["sub"] = subject

    try:
        return jwt.encode(
            payload, private_key, algorithm=settings.JWT_ALGORITHM
        )
    except Exception as e:
        logger.exception("JWT encoding failed.")
        raise RuntimeError(f"JWT encoding failed: {e}") from e


# JWT Verification Function
def verify_jwt_token(
    token: str,
    public_key: Union[str, bytes],
    audience: Optional[str] = None,
    issuer: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Verify and decode a RS256 JWT token.

    Args:
        token (str): JWT token to verify.
        public_key (str/bytes): RSA public key.
        audience (str, optional): Expected 'aud' claim.
        issuer (str, optional): Expected 'iss' claim.

    Returns:
        dict: Decoded payload.

    Raises:
        ValueError or RuntimeError for various failures.
    """
    if not token:
        raise ValueError("JWT token is required.")
    if not public_key:
        raise ValueError("Public key is required.")

    options = {
        "verify_signature": True,
        "verify_exp": True,
        "verify_aud": audience is not None,
        "verify_iss": issuer is not None,
    }

    try:
        return jwt.decode(
            token,
            public_key,
            algorithms=[settings.JWT_ALGORITHM],
            audience=audience,
            issuer=issuer,
            options=options,
        )

    except jwt.ExpiredSignatureError as exc:
        logger.warning("JWT token has expired.")
        raise ValueError("JWT token has expired.") from exc

    except jwt.InvalidAudienceError as exc:
        logger.warning("Invalid audience in JWT token.")
        raise ValueError("Invalid audience in JWT token.") from exc

    except jwt.InvalidIssuerError as exc:
        logger.warning("Invalid issuer in JWT token.")
        raise ValueError("Invalid issuer in JWT token.") from exc

    except jwt.InvalidTokenError as exc:
        logger.warning(f"Invalid JWT token: {exc}")
        raise RuntimeError(f"Invalid JWT token: {exc}") from exc


def get_current_user(
    access_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """
    Retrieve and verify JWT token from cookie or Authorization header.

    Priority:
        1. Cookie: 'access_token'
        2. Header: 'Authorization: Bearer <token>'

    Returns:
        dict: Decoded JWT payload (e.g., user_id, role_id)

    Raises:
        HTTPException 401: If token is missing or invalid.
    """
    token = access_token
    print("📦 Cookie Token:", token)
    print("🔐 Authorization Header:", authorization)

    # Fallback: Try Authorization header
    if not token and authorization:
        if authorization.startswith("Bearer "):
            token = authorization[7:]  # remove 'Bearer ' prefix
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Authorization header format.",
            )

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token not provided.",
        )

    try:
        payload = verify_jwt_token(
            token=token,
            public_key=PUBLIC_KEY.get_secret_value(),
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
        )
        return payload

    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(ve)
        ) from ve
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token. {str(e)}",
        ) from e
