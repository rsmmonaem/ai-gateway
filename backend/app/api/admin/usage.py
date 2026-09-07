from datetime import datetime, timedelta, timezone
from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.token import get_current_admin
from app.database.session import get_db
from app.models.api_key import APIKey
from app.models.model_registry import ModelDefinition
from app.models.usage_record import UsageRecord
from app.models.user import User
from app.schemas.usage import UsageRecordOut, UsageStatsSummary

router = APIRouter(prefix="/api/admin/usage", tags=["Admin - Usage & Analytics"])


@router.get("/summary", response_model=UsageStatsSummary)
async def get_usage_summary(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve global system health, activity, and cost metrics."""
    # Aggregated token & request totals
    agg_stmt = select(
        func.count(UsageRecord.id).label("total_reqs"),
        func.coalesce(func.sum(UsageRecord.prompt_tokens), 0).label("prompt_t"),
        func.coalesce(func.sum(UsageRecord.completion_tokens), 0).label("comp_t"),
        func.coalesce(func.sum(UsageRecord.total_tokens), 0).label("total_t"),
        func.coalesce(func.sum(UsageRecord.estimated_cost), 0.0).label("cost"),
        func.coalesce(func.avg(UsageRecord.duration_ms), 0.0).label("avg_lat"),
    )
    agg_res = (await db.execute(agg_stmt)).one()

    total_reqs = agg_res.total_reqs
    prompt_t = agg_res.prompt_t
    comp_t = agg_res.comp_t
    total_t = agg_res.total_t
    cost = agg_res.cost
    avg_lat = agg_res.avg_lat

    # Error count
    err_res = await db.execute(
        select(func.count(UsageRecord.id)).where(UsageRecord.status_code >= 400)
    )
    error_count = err_res.scalar() or 0
    error_rate = round((error_count / total_reqs * 100), 2) if total_reqs > 0 else 0.0

    # Today's activity (last 24 hours)
    since_today = datetime.now(timezone.utc) - timedelta(hours=24)
    today_res = await db.execute(
        select(
            func.count(UsageRecord.id),
            func.coalesce(func.sum(UsageRecord.total_tokens), 0),
        ).where(UsageRecord.created_at >= since_today)
    )
    today_reqs, today_tokens = today_res.one()

    # Counts
    models_cnt = (await db.execute(select(func.count(ModelDefinition.id)).where(ModelDefinition.enabled == True))).scalar() or 0
    users_cnt = (await db.execute(select(func.count(User.id)))).scalar() or 0
    keys_cnt = (await db.execute(select(func.count(APIKey.id)).where(APIKey.revoked_at.is_(None)))).scalar() or 0

    return UsageStatsSummary(
        total_requests=total_reqs,
        total_prompt_tokens=prompt_t,
        total_completion_tokens=comp_t,
        total_tokens=total_t,
        estimated_total_cost=round(cost, 4),
        avg_latency_ms=round(avg_lat, 2),
        error_rate_percent=error_rate,
        requests_today=today_reqs or 0,
        tokens_today=today_tokens or 0,
        active_models_count=models_cnt,
        total_users_count=users_cnt,
        active_keys_count=keys_cnt,
    )


@router.get("/records", response_model=List[UsageRecordOut])
async def list_usage_records(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve detailed log of recent requests."""
    stmt = (
        select(UsageRecord)
        .order_by(UsageRecord.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    res = await db.execute(stmt)
    return res.scalars().all()
