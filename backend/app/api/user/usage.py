from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.token import get_current_user
from app.database.session import get_db
from app.models.usage_record import UsageRecord
from app.models.user import User
from app.schemas.usage import UsageRecordOut

router = APIRouter(prefix="/api/user/usage", tags=["User - Usage"])


@router.get("/records", response_model=List[UsageRecordOut])
async def list_my_usage_records(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve recent API calls made by the logged-in user."""
    stmt = (
        select(UsageRecord)
        .where(UsageRecord.user_id == current_user.id)
        .order_by(UsageRecord.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get("/summary")
async def get_my_usage_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve usage aggregate totals for the current user."""
    stmt = select(
        func.count(UsageRecord.id).label("total_requests"),
        func.coalesce(func.sum(UsageRecord.prompt_tokens), 0).label("prompt_tokens"),
        func.coalesce(func.sum(UsageRecord.completion_tokens), 0).label("completion_tokens"),
        func.coalesce(func.sum(UsageRecord.total_tokens), 0).label("total_tokens"),
        func.coalesce(func.sum(UsageRecord.estimated_cost), 0.0).label("estimated_cost"),
    ).where(UsageRecord.user_id == current_user.id)

    res = (await db.execute(stmt)).one()
    return {
        "total_requests": res.total_requests,
        "prompt_tokens": res.prompt_tokens,
        "completion_tokens": res.completion_tokens,
        "total_tokens": res.total_tokens,
        "estimated_cost": round(res.estimated_cost, 4),
    }
