import platform
import time
from fastapi import APIRouter, Depends
import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database.session import get_db

router = APIRouter(tags=["Health"])


async def _ping(url: str, timeout: float = 2.0) -> bool:
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url)
            return resp.status_code < 500
    except Exception:
        return False


@router.get("/health")
@router.get("/v1/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """System and hardware health status endpoint for Apple Silicon M5 gateway."""
    db_status = "healthy"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    ollama_ok = await _ping(f"{settings.OLLAMA_BASE_URL}/api/tags")
    llamacpp_ok = await _ping(f"{settings.LLAMACPP_BASE_URL}/health")
    mlx_ok = await _ping(f"{settings.MLX_BASE_URL}/v1/models")

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "timestamp": int(time.time()),
        "database": db_status,
        "hardware": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "target": "Apple Silicon M5 (16 GB Unified Memory)",
        },
        "backends": {
            "ollama": {"endpoint": settings.OLLAMA_BASE_URL, "status": "ONLINE" if ollama_ok else "OFFLINE"},
            "llama_server": {"endpoint": settings.LLAMACPP_BASE_URL, "status": "ONLINE" if llamacpp_ok else "OFFLINE"},
            "mlx_lm": {"endpoint": settings.MLX_BASE_URL, "status": "ONLINE" if mlx_ok else "OFFLINE"},
        },
    }
