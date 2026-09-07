import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Tuple, Union

import jwt
from passlib.context import CryptContext

from app.core.config import settings

# CryptContext supporting both argon2 and bcrypt
pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against an argon2/bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate a secure hash for a password using Argon2id/bcrypt."""
    return pwd_context.hash(password)


def generate_api_key(prefix: str = "sk-local-") -> Tuple[str, str, str]:
    """
    Generate a new API key.
    Returns:
        (raw_key, key_hash, key_prefix)
    Example raw_key: sk-local-9a8f3b2c1d0e4f5a6b7c8d9e0f1a2b3c
    """
    random_bytes = secrets.token_hex(24)
    raw_key = f"{prefix}{random_bytes}"
    key_hash = hash_api_key(raw_key)
    # Prefix for identification in dashboard: e.g. "sk-local-9a8f..."
    key_prefix = f"{raw_key[:14]}..."
    return raw_key, key_hash, key_prefix


def hash_api_key(raw_key: str) -> str:
    """
    Deterministically hash an API key using HMAC-SHA256 with the system secret key.
    This ensures that raw keys can never be recovered from the database.
    """
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        raw_key.strip().encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def create_access_token(
    subject: Union[str, Any],
    role: str = "user",
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT access token for web dashboard sessions."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "role": role,
        "iat": datetime.now(timezone.utc),
    }
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except (jwt.PyJWTError, Exception):
        return None
