from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.token import get_current_admin
from app.database.session import get_db
from app.models.api_key import APIKey
from app.models.user import User
from app.schemas.auth import APIKeyOut

router = APIRouter(prefix="/api/admin/api-keys", tags=["Admin - API Keys"])


@router.get("", response_model=List[APIKeyOut])
async def list_all_keys(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all API keys across all users."""
    res = await db.execute(select(APIKey).order_by(APIKey.created_at.desc()))
    return res.scalars().all()


@router.post("/{key_id}/revoke", response_model=APIKeyOut)
async def revoke_key(
    key_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Immediately revoke an API key."""
    res = await db.execute(select(APIKey).where(APIKey.id == key_id))
    key = res.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="API Key not found")

    key.revoked_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(key)
    return key
