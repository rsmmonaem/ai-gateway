import asyncio
from typing import Dict, Optional
from fastapi import HTTPException, status
from app.core.config import settings
from app.core.logging import logger


class ConcurrencyManager:
    """
    Protects Apple Silicon M5 (16 GB Unified Memory) from RAM exhaustion and GPU thrashing.
    Enforces global, per-backend, and per-model concurrency limits with request queuing.
    """

    def __init__(self):
        self._global_semaphore = asyncio.Semaphore(settings.DEFAULT_MAX_CONCURRENT_REQUESTS)
        self._backend_semaphores: Dict[str, asyncio.Semaphore] = {
            "ollama": asyncio.Semaphore(settings.OLLAMA_CONCURRENCY),
            "llamacpp": asyncio.Semaphore(settings.LLAMACPP_CONCURRENCY),
            "mlx": asyncio.Semaphore(settings.MLX_CONCURRENCY),
            "openai_compatible": asyncio.Semaphore(4),
        }
        self._model_semaphores: Dict[str, asyncio.Semaphore] = {}
        self._active_counts: Dict[str, int] = {}
        self._lock = asyncio.Lock()

    async def _get_model_semaphore(self, model_slug: str, limit: int = 2) -> asyncio.Semaphore:
        async with self._lock:
            if model_slug not in self._model_semaphores:
                # 27B heavy model has limit 1, 7B models limit 2
                model_limit = 1 if "27b" in model_slug.lower() or "heavy" in model_slug.lower() else limit
                self._model_semaphores[model_slug] = asyncio.Semaphore(model_limit)
                self._active_counts[model_slug] = 0
            return self._model_semaphores[model_slug]

    async def acquire(self, model_slug: str, backend: str = "ollama", timeout: float = 30.0) -> None:
        """
        Acquires slots across global, backend-specific, and model-specific semaphores.
        Raises HTTP 503 if queue timeout is exceeded.
        """
        sem = await self._get_model_semaphore(model_slug)
        backend_sem = self._backend_semaphores.get(backend.lower(), self._global_semaphore)

        try:
            # 1. Global slot
            await asyncio.wait_for(self._global_semaphore.acquire(), timeout=timeout)
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error": {
                        "message": "Gateway inference capacity is saturated. Please retry shortly.",
                        "type": "server_error",
                        "code": "gateway_busy",
                    }
                },
                headers={"Retry-After": "5"},
            )

        try:
            # 2. Backend slot
            await asyncio.wait_for(backend_sem.acquire(), timeout=timeout)
        except asyncio.TimeoutError:
            self._global_semaphore.release()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error": {
                        "message": f"Backend '{backend}' capacity saturated on Apple Silicon M5.",
                        "type": "server_error",
                        "code": "backend_busy",
                    }
                },
                headers={"Retry-After": "5"},
            )

        try:
            # 3. Model slot
            await asyncio.wait_for(sem.acquire(), timeout=timeout)
            async with self._lock:
                self._active_counts[model_slug] = self._active_counts.get(model_slug, 0) + 1
        except asyncio.TimeoutError:
            backend_sem.release()
            self._global_semaphore.release()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error": {
                        "message": f"Model '{model_slug}' is currently processing maximum concurrent requests.",
                        "type": "server_error",
                        "code": "model_busy",
                    }
                },
                headers={"Retry-After": "5"},
            )

    def release(self, model_slug: str, backend: str = "ollama") -> None:
        """Release previously acquired concurrency slots."""
        if model_slug in self._model_semaphores:
            self._model_semaphores[model_slug].release()
            if model_slug in self._active_counts:
                self._active_counts[model_slug] = max(0, self._active_counts[model_slug] - 1)

        backend_sem = self._backend_semaphores.get(backend.lower())
        if backend_sem:
            backend_sem.release()

        self._global_semaphore.release()

    def get_active_count(self, model_slug: str) -> int:
        return self._active_counts.get(model_slug, 0)


concurrency_manager = ConcurrencyManager()
