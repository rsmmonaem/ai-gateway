from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_password_hash, generate_api_key
from app.database.base import Base
from app.database.session import engine
from app.models.user import User
from app.models.api_key import APIKey
from app.models.model_registry import ModelDefinition, ModelInstance
from app.core.logging import logger


async def init_db(session: AsyncSession) -> None:
    """Initialize database tables and bootstrap admin user and models."""
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Check for admin user
    result = await session.execute(
        select(User).where(User.email == settings.FIRST_ADMIN_EMAIL)
    )
    admin = result.scalars().first()

    if not admin:
        logger.info(f"Creating default admin user: {settings.FIRST_ADMIN_EMAIL}")
        admin = User(
            email=settings.FIRST_ADMIN_EMAIL,
            name=settings.FIRST_ADMIN_NAME,
            password_hash=get_password_hash(settings.FIRST_ADMIN_PASSWORD),
            role="admin",
            status="active",
        )
        session.add(admin)
        await session.flush()

        # Generate bootstrap admin API key
        raw_key, key_hash, key_prefix = generate_api_key()
        admin_key = APIKey(
            user_id=admin.id,
            key_hash=key_hash,
            key_prefix=key_prefix,
            name="Bootstrap Admin Key",
            rate_limit_rpm=300,
            monthly_limit_tokens=100_000_000,
        )
        session.add(admin_key)
        logger.info("=" * 60)
        logger.info("BOOTSTRAP ADMIN API KEY GENERATED (Save this):")
        logger.info(f"API Key: {raw_key}")
        logger.info(f"Admin Email: {settings.FIRST_ADMIN_EMAIL}")
        logger.info(f"Admin Password: {settings.FIRST_ADMIN_PASSWORD}")
        logger.info("=" * 60)

    # Seed default model definitions if empty
    models_res = await session.execute(select(ModelDefinition))
    existing_models = models_res.scalars().all()

    if not existing_models:
        default_models = [
            ModelDefinition(
                name="Kimi 7B Instruct",
                slug="kimi-7b",
                aliases="kimi,kimi-fast",
                provider="local-ollama",
                backend="ollama",
                backend_model_name="kimi:7b",
                endpoint=settings.OLLAMA_BASE_URL,
                context_length=32768,
                supports_chat=True,
                supports_completion=True,
                supports_tools=False,
                enabled=True,
                priority=100,
                description="Moonshot Kimi 7B running on Apple Silicon Ollama with Metal acceleration.",
            ),
            ModelDefinition(
                name="Qwen 2.5 7B Instruct",
                slug="qwen-7b",
                aliases="qwen,qwen2.5-7b",
                provider="local-ollama",
                backend="ollama",
                backend_model_name="qwen2.5:7b",
                endpoint=settings.OLLAMA_BASE_URL,
                context_length=32768,
                supports_chat=True,
                supports_completion=True,
                supports_tools=True,
                enabled=True,
                priority=95,
                description="Alibaba Qwen 2.5 7B model running natively via Ollama on macOS.",
            ),
            ModelDefinition(
                name="Llama 3.1 8B Instruct",
                slug="llama-8b",
                aliases="llama,llama-3.1-8b",
                provider="local-ollama",
                backend="ollama",
                backend_model_name="llama3.1:8b",
                endpoint=settings.OLLAMA_BASE_URL,
                context_length=131072,
                supports_chat=True,
                supports_completion=True,
                supports_tools=True,
                enabled=True,
                priority=90,
                description="Meta Llama 3.1 8B served via Ollama Metal backend.",
            ),
            ModelDefinition(
                name="OpenAI Compatible Test Model",
                slug="mock-fast",
                aliases="mock,test-model",
                provider="local-mock",
                backend="openai_compatible",
                backend_model_name="mock-fast",
                endpoint="http://127.0.0.1:8000/v1/_mock",
                context_length=16384,
                supports_chat=True,
                supports_completion=True,
                supports_tools=True,
                enabled=True,
                priority=50,
                description="Built-in zero-dependency mock endpoint for immediate offline verification.",
            ),
        ]

        for m in default_models:
            session.add(m)
            await session.flush()
            # Add instance
            inst = ModelInstance(
                model_id=m.id,
                instance_name=f"{m.slug}-primary",
                endpoint=m.endpoint,
                health_status="ONLINE" if m.slug == "mock-fast" else "UNKNOWN",
                enabled=True,
            )
            session.add(inst)

        await session.commit()
        logger.info("Seeded initial model registry.")
    else:
        await session.commit()
