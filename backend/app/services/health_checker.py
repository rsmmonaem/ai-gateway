import asyncio
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.logging import logger
from app.database.session import async_session_factory
from app.models.model_registry import ModelDefinition, ModelInstance
from app.providers.registry import provider_registry


class HealthChecker:
    """Periodically checks health status of all registered model instances."""

    def __init__(self, interval_seconds: int = 30):
        self.interval_seconds = interval_seconds
        self._running = False
        self._task: asyncio.Task = None

    async def check_all_models(self) -> None:
        """Check all instances across all models and update DB."""
        try:
            async with async_session_factory() as session:
                stmt = select(ModelDefinition).options(selectinload(ModelDefinition.instances))
                res = await session.execute(stmt)
                models = res.scalars().all()

                for model in models:
                    if not model.enabled:
                        continue

                    instances = model.instances or []
                    if not instances:
                        # If no instances explicitly listed, check model.endpoint
                        provider = provider_registry.get_provider(
                            backend=model.backend,
                            endpoint=model.endpoint,
                            model_name=model.backend_model_name,
                        )
                        is_healthy, status_str, latency = await provider.health_check()
                        logger.debug(f"Health check for {model.slug}: {status_str} ({latency}ms)")
                        continue

                    for inst in instances:
                        if not inst.enabled:
                            continue

                        provider = provider_registry.get_provider(
                            backend=model.backend,
                            endpoint=inst.endpoint,
                            model_name=model.backend_model_name,
                        )
                        is_healthy, status_str, latency = await provider.health_check()
                        inst.health_status = "ONLINE" if is_healthy else "OFFLINE"
                        inst.last_health_check = datetime.now(timezone.utc)
                        if latency is not None:
                            # Moving average
                            inst.avg_latency_ms = round((inst.avg_latency_ms * 0.7) + (latency * 0.3), 2)

                await session.commit()
        except Exception as e:
            logger.error(f"Error in background health check: {e}")

    async def _loop(self) -> None:
        while self._running:
            await self.check_all_models()
            await asyncio.sleep(self.interval_seconds)

    def start(self) -> None:
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._loop())
            logger.info("Background HealthChecker started.")

    def stop(self) -> None:
        if self._running:
            self._running = False
            if self._task:
                self._task.cancel()
            logger.info("Background HealthChecker stopped.")


health_checker = HealthChecker()
