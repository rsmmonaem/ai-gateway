from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.database.session import async_session_factory
from app.models.usage_record import UsageRecord


class UsageTracker:
    """Asynchronous usage recorder and cost metering service."""

    @staticmethod
    async def record_usage(
        request_id: str,
        user_id: int,
        api_key_id: Optional[int],
        model: str,
        provider: str,
        backend: str,
        started_at: datetime,
        completed_at: datetime,
        duration_ms: float,
        prompt_tokens: int,
        completion_tokens: int,
        status_code: int,
        pricing_input: float = 0.0,
        pricing_output: float = 0.0,
        error_code: Optional[str] = None,
        stream: bool = False,
        client_ip: Optional[str] = None,
        prompt_content: Optional[str] = None,
        response_content: Optional[str] = None,
    ) -> None:
        total_tokens = prompt_tokens + completion_tokens
        estimated_cost = (
            (prompt_tokens * pricing_input) + (completion_tokens * pricing_output)
        ) / 1_000_000.0

        # Privacy protection: only persist actual prompt/completion text if specifically opted in
        saved_prompt = prompt_content if settings.STORE_REQUEST_CONTENT else None
        saved_response = response_content if settings.STORE_REQUEST_CONTENT else None

        record = UsageRecord(
            request_id=request_id,
            user_id=user_id,
            api_key_id=api_key_id,
            model=model,
            provider=provider,
            backend=backend,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=round(duration_ms, 2),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost=round(estimated_cost, 6),
            status_code=status_code,
            error_code=error_code,
            stream=stream,
            client_ip=client_ip,
            prompt_content=saved_prompt,
            response_content=saved_response,
            created_at=datetime.now(timezone.utc),
        )

        try:
            async with async_session_factory() as session:
                session.add(record)
                await session.commit()
        except Exception as e:
            logger.error(f"Failed to record usage in database for request {request_id}: {e}")

        # Emit structured log
        logger.info(
            f"API Request completed: {model} ({backend}) - {status_code}",
            extra={
                "request_id": request_id,
                "user_id": user_id,
                "api_key_id": api_key_id,
                "model": model,
                "backend": backend,
                "duration_ms": duration_ms,
                "status_code": status_code,
                "client_ip": client_ip,
                "tokens": total_tokens,
            },
        )


usage_tracker = UsageTracker()
