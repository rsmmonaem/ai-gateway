from datetime import datetime, timedelta, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.token import get_current_user
from app.core.security import generate_api_key
from app.database.session import get_db
from app.models.api_key import APIKey
from app.models.user import User
from app.schemas.auth import APIKeyCreate, APIKeyCreateResponse, APIKeyOut

router = APIRouter(prefix="/api/user/api-keys", tags=["User - API Keys"])


@router.get("", response_model=List[APIKeyOut])
async def list_my_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List API keys belonging to the logged-in user."""
    stmt = (
        select(APIKey)
        .where(APIKey.user_id == current_user.id)
        .order_by(APIKey.created_at.desc())
    )
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("", response_model=APIKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_my_key(
    key_in: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a new API key.
    IMPORTANT: The raw key is returned ONLY once in this response.
    """
    raw_key, key_hash, key_prefix = generate_api_key()

    expires_at = None
    if key_in.expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=key_in.expires_in_days)

    new_key = APIKey(
        user_id=current_user.id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=key_in.name,
        rate_limit_rpm=key_in.rate_limit_rpm or 60,
        monthly_limit_tokens=key_in.monthly_limit_tokens or 10_000_000,
        expires_at=expires_at,
    )
    db.add(new_key)
    await db.commit()
    await db.refresh(new_key)

    return APIKeyCreateResponse(
        id=new_key.id,
        name=new_key.name,
        raw_key=raw_key,
        key_prefix=new_key.key_prefix,
        rate_limit_rpm=new_key.rate_limit_rpm,
        monthly_limit_tokens=new_key.monthly_limit_tokens,
        created_at=new_key.created_at,
        expires_at=new_key.expires_at,
    )


@router.post("/{key_id}/revoke", response_model=APIKeyOut)
async def revoke_my_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke one of the user's API keys."""
    stmt = select(APIKey).where(APIKey.id == key_id, APIKey.user_id == current_user.id)
    res = await db.execute(stmt)
    key = res.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="API Key not found")

    key.revoked_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(key)
    return key
