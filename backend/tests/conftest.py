import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Set testing environment variables
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key-at-least-32-chars-long-123456"
os.environ["REDIS_URL"] = ""

from app.core.security import get_password_hash, hash_api_key
from app.database.base import Base
from app.database.session import get_db
from app.main import app
from app.models.api_key import APIKey
from app.models.model_registry import ModelDefinition
from app.models.user import User
from app.services.rate_limiter import rate_limiter

test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
)
test_session_factory = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture
async def db_session():
    # Clear in-memory rate limiter store for clean isolated test runs
    rate_limiter._memory_store.clear()

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with test_session_factory() as session:
        # Seed test admin
        admin = User(
            email="admin@test.local",
            name="Admin User",
            password_hash=get_password_hash("adminpass123"),
            role="admin",
            status="active",
        )
        session.add(admin)

        # Seed test standard user
        normal_user = User(
            email="user@test.local",
            name="Normal User",
            password_hash=get_password_hash("userpass123"),
            role="user",
            status="active",
        )
        session.add(normal_user)
        await session.flush()

        # Seed standard valid test API key (high limit for general test suite)
        test_raw_key = "sk-local-testkey123456"
        valid_key = APIKey(
            user_id=normal_user.id,
            key_hash=hash_api_key(test_raw_key),
            key_prefix="sk-local-test...",
            name="Test Key",
            rate_limit_rpm=1000,
            monthly_limit_tokens=10_000_000,
        )
        session.add(valid_key)

        # Seed low rate-limit test key for rate limit testing (limit: 3 RPM)
        low_limit_raw_key = "sk-local-lowlimit"
        low_limit_key = APIKey(
            user_id=normal_user.id,
            key_hash=hash_api_key(low_limit_raw_key),
            key_prefix="sk-local-lowl...",
            name="Low Limit Key",
            rate_limit_rpm=3,
            monthly_limit_tokens=1_000_000,
        )
        session.add(low_limit_key)

        # Seed revoked test API key
        revoked_raw_key = "sk-local-revokedkey"
        from datetime import datetime, timezone
        revoked_key = APIKey(
            user_id=normal_user.id,
            key_hash=hash_api_key(revoked_raw_key),
            key_prefix="sk-local-revo...",
            name="Revoked Key",
            revoked_at=datetime.now(timezone.utc),
        )
        session.add(revoked_key)

        # Seed models
        mock_model = ModelDefinition(
            name="Mock Fast Model",
            slug="mock-fast",
            aliases="mock,test-mock",
            provider="local-mock",
            backend="openai_compatible",
            backend_model_name="mock-fast",
            endpoint="http://127.0.0.1:8000/v1/_mock",
            context_length=16384,
            supports_chat=True,
            supports_completion=True,
            enabled=True,
            priority=100,
        )
        session.add(mock_model)

        disabled_model = ModelDefinition(
            name="Disabled Model",
            slug="disabled-model",
            provider="local-mock",
            backend="openai_compatible",
            backend_model_name="disabled",
            endpoint="http://127.0.0.1:8000/v1/_mock",
            context_length=4096,
            enabled=False,
            priority=10,
        )
        session.add(disabled_model)

        await session.commit()
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer sk-local-testkey123456"}
