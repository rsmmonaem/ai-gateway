import platform
import time
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database.session import get_db

router = APIRouter(tags=["Health"])


@router.get("/health")
@router.get("/v1/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """System and hardware health status endpoint."""
    db_status = "healthy"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "timestamp": int(time.time()),
        "database": db_status,
        "environment": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "target": "Mac mini M4 (Apple Silicon / Metal)",
        },
    }
