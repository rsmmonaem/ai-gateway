import asyncio
from typing import Dict
from fastapi import HTTPException, status
from app.core.config import settings
from app.core.logging import logger


class ConcurrencyManager:
    """
    Protects Mac mini M4 hardware from memory exhaustion and GPU thrashing.
    Enforces global and per-model concurrent execution limits with request queuing.
    """

    def __init__(self):
        self._global_semaphore = asyncio.Semaphore(settings.DEFAULT_MAX_CONCURRENT_REQUESTS)
        self._model_semaphores: Dict[str, asyncio.Semaphore] = {}
        self._active_counts: Dict[str, int] = {}
        self._lock = asyncio.Lock()

    async def _get_model_semaphore(self, model_slug: str, limit: int = 2) -> asyncio.Semaphore:
        async with self._lock:
            if model_slug not in self._model_semaphores:
                self._model_semaphores[model_slug] = asyncio.Semaphore(limit)
                self._active_counts[model_slug] = 0
            return self._model_semaphores[model_slug]

    async def acquire(self, model_slug: str, timeout: float = 30.0) -> None:
        """
        Acquire a slot in both the global and model-specific queue.
        Raises 503 if timeout is exceeded.
        """
        sem = await self._get_model_semaphore(model_slug)

        try:
            # Wait for global slot
            await asyncio.wait_for(self._global_semaphore.acquire(), timeout=timeout)
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error": {
                        "message": "Gateway inference capacity is saturated. Please retry shortly.",
                        "type": "server_error",
                        "param": None,
                        "code": "gateway_busy",
                    }
                },
                headers={"Retry-After": "5"},
            )

        try:
            # Wait for model-specific slot
            await asyncio.wait_for(sem.acquire(), timeout=timeout)
            async with self._lock:
                self._active_counts[model_slug] = self._active_counts.get(model_slug, 0) + 1
        except asyncio.TimeoutError:
            # Release global slot if model slot timed out
            self._global_semaphore.release()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error": {
                        "message": f"Model '{model_slug}' is currently processing maximum concurrent requests. Please retry shortly.",
                        "type": "server_error",
                        "param": None,
                        "code": "model_busy",
                    }
                },
                headers={"Retry-After": "5"},
            )

    def release(self, model_slug: str) -> None:
        """Release previously acquired concurrency slots."""
        if model_slug in self._model_semaphores:
            self._model_semaphores[model_slug].release()
            if model_slug in self._active_counts:
                self._active_counts[model_slug] = max(0, self._active_counts[model_slug] - 1)

        self._global_semaphore.release()

    def get_active_count(self, model_slug: str) -> int:
        return self._active_counts.get(model_slug, 0)


concurrency_manager = ConcurrencyManager()
