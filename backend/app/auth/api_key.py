from datetime import datetime, timezone
from typing import Optional, Tuple
from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import hash_api_key
from app.database.session import get_db
from app.models.api_key import APIKey
from app.models.user import User
from app.services.rate_limiter import rate_limiter


async def get_api_key_auth(
    request: Request,
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None, alias="x-api-key"),
    db: AsyncSession = Depends(get_db),
) -> Tuple[User, APIKey]:
    """
    Authenticate a request using an API key from either:
    - Authorization: Bearer sk-local-xxxxxxxx
    - x-api-key: sk-local-xxxxxxxx (Anthropic SDK standard)
    Returns: (User, APIKey)
    """
    raw_key: Optional[str] = None

    if x_api_key:
        raw_key = x_api_key.strip()
    elif authorization:
        parts = authorization.strip().split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            raw_key = parts[1]
        elif len(parts) == 1 and parts[0].startswith("sk-"):
            raw_key = parts[0]

    if not raw_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "message": "Missing API key. Pass 'Authorization: Bearer <key>' or 'x-api-key: <key>'",
                    "type": "invalid_request_error",
                    "param": None,
                    "code": "missing_api_key",
                }
            },
        )

    hashed = hash_api_key(raw_key)

    # Lookup key with user eagerly loaded
    stmt = (
        select(APIKey)
        .options(selectinload(APIKey.user))
        .where(APIKey.key_hash == hashed)
    )
    result = await db.execute(stmt)
    api_key = result.scalar_one_or_none()

    if not api_key or not api_key.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "message": "Incorrect or expired API key provided.",
                    "type": "invalid_request_error",
                    "param": None,
                    "code": "invalid_api_key",
                }
            },
        )

    user = api_key.user
    if not user or user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "message": "User account associated with this key is inactive or disabled.",
                    "type": "access_denied",
                    "param": None,
                    "code": "user_disabled",
                }
            },
        )

    # Check Rate Limiting
    is_allowed, remaining, reset_seconds = await rate_limiter.check_rate_limit(
        key=f"ratelimit:key:{api_key.id}",
        limit=api_key.rate_limit_rpm,
        window_seconds=60,
    )
    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": {
                    "message": f"Rate limit exceeded: {api_key.rate_limit_rpm} requests per minute limit reached. Try again in {reset_seconds} seconds.",
                    "type": "requests",
                    "param": None,
                    "code": "rate_limit_exceeded",
                }
            },
            headers={"Retry-After": str(reset_seconds)},
        )

    # Record last used timestamp (non-blocking flush)
    api_key.last_used_at = datetime.now(timezone.utc)
    await db.commit()

    # Store on request state for logging middleware
    request.state.user = user
    request.state.api_key = api_key

    return user, api_key
