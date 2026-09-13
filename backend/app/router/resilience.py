import asyncio
import random
from typing import AsyncIterator, List, Optional, Tuple
from fastapi import HTTPException
import httpx

from app.core.config import settings
from app.core.logging import logger
from app.models.model_registry import ModelDefinition, ModelInstance
from app.providers.base import InferenceProvider
from app.schemas.openai import ChatCompletionRequest, ChatCompletionResponse


class ResilienceManager:
    """
    Executes inference requests with bounded retries (exponential backoff + jitter)
    and automatic failover to secondary providers when primary backend is offline or timing out.
    """

    @classmethod
    def is_retriable_error(cls, exc: Exception) -> bool:
        """Determines whether an exception is transient and retriable."""
        if isinstance(exc, (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError)):
            return True
        if isinstance(exc, HTTPException):
            # 502, 503, 504, 429 are retriable server/rate limit errors
            return exc.status_code in (429, 500, 502, 503, 504)
        return False

    @classmethod
    async def execute_chat_completion(
        cls,
        request: ChatCompletionRequest,
        primary: Tuple[ModelDefinition, Optional[ModelInstance], InferenceProvider],
        fallbacks: List[Tuple[ModelDefinition, Optional[ModelInstance], InferenceProvider]],
    ) -> Tuple[ChatCompletionResponse, ModelDefinition, Optional[ModelInstance], bool]:
        """
        Executes a non-streaming chat completion with retry and fallback behavior.
        Returns: (response, used_model_def, used_instance, fallback_used)
        """
        candidates = [primary] + fallbacks
        last_exception: Optional[Exception] = None

        for idx, (model_def, instance, provider) in enumerate(candidates):
            fallback_used = (idx > 0)
            max_attempts = settings.MAX_RETRIES + 1

            for attempt in range(1, max_attempts + 1):
                try:
                    logger.debug(
                        f"Attempt {attempt}/{max_attempts} for model '{model_def.slug}' via endpoint '{provider.endpoint}'"
                    )
                    resp = await provider.chat_completion(request)
                    if fallback_used:
                        logger.info(f"Fallback to model '{model_def.slug}' succeeded.")
                    return resp, model_def, instance, fallback_used

                except Exception as exc:
                    last_exception = exc
                    if not cls.is_retriable_error(exc):
                        # Non-retriable application/auth/client error: raise immediately
                        logger.warning(f"Non-retriable error on model '{model_def.slug}': {exc}")
                        raise exc

                    logger.warning(
                        f"Retriable error on model '{model_def.slug}' (attempt {attempt}/{max_attempts}): {exc}"
                    )
                    if attempt < max_attempts:
                        # Exponential backoff with jitter
                        backoff = (settings.RETRY_BACKOFF_FACTOR * (2 ** (attempt - 1))) + random.uniform(0, 0.1)
                        await asyncio.sleep(backoff)

            logger.warning(f"All {max_attempts} attempts failed for model '{model_def.slug}'. Trying next fallback candidate if available...")

        if last_exception:
            raise last_exception
        raise HTTPException(status_code=503, detail={"error": {"message": "All model backends are unavailable."}})


resilience_manager = ResilienceManager()
