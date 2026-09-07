import asyncio
import time
from collections import defaultdict, deque
from typing import Dict, Optional, Tuple
from app.core.config import settings
from app.core.logging import logger

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None


class RateLimiter:
    """
    Sliding window rate limiter supporting Redis with automatic in-memory fallback.
    """

    def __init__(self):
        self._redis: Optional[any] = None
        self._memory_store: Dict[str, deque] = defaultdict(deque)
        self._lock = asyncio.Lock()
        self._redis_failed = False

    async def get_redis(self):
        if self._redis_failed or not settings.REDIS_URL or not aioredis:
            return None
        if self._redis is None:
            try:
                self._redis = aioredis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=2,
                )
                await self._redis.ping()
                logger.info("Connected to Redis for distributed rate limiting.")
            except Exception as e:
                logger.warning(f"Redis connection failed ({e}). Falling back to local in-memory rate limiter.")
                self._redis = None
                self._redis_failed = True
        return self._redis

    async def check_rate_limit(
        self, key: str, limit: int, window_seconds: int = 60
    ) -> Tuple[bool, int, int]:
        """
        Check whether the given key is allowed under the rate limit.
        Returns: (is_allowed, remaining_quota, reset_seconds)
        """
        if limit <= 0:
            return True, 999999, 0

        redis_client = await self.get_redis()
        now = time.time()

        if redis_client:
            try:
                pipe = redis_client.pipeline()
                current_window = int(now // window_seconds)
                redis_key = f"{key}:{current_window}"
                pipe.incr(redis_key)
                pipe.expire(redis_key, window_seconds * 2)
                results = await pipe.execute()
                current_count = results[0]
                remaining = max(0, limit - current_count)
                reset_seconds = int(window_seconds - (now % window_seconds))
                return current_count <= limit, remaining, reset_seconds
            except Exception as e:
                logger.warning(f"Redis rate check error: {e}. Using in-memory fallback.")
                self._redis_failed = True

        # In-memory sliding window fallback
        async with self._lock:
            timestamps = self._memory_store[key]
            # Prune timestamps older than the sliding window
            cutoff = now - window_seconds
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()

            if len(timestamps) >= limit:
                oldest = timestamps[0]
                reset_seconds = max(1, int(oldest + window_seconds - now))
                return False, 0, reset_seconds

            timestamps.append(now)
            remaining = limit - len(timestamps)
            reset_seconds = window_seconds
            return True, remaining, reset_seconds


rate_limiter = RateLimiter()
