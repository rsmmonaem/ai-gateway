from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings

# Normalize Postgres connection strings if supplied as postgres:// or postgresql://
database_url = settings.DATABASE_URL
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif database_url.startswith("postgresql://") and not database_url.startswith("postgresql+asyncpg://"):
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# Connect args for SQLite
connect_args = {}
if "sqlite" in database_url:
    connect_args["check_same_thread"] = False

engine = create_async_engine(
    database_url,
    echo=settings.DATABASE_ECHO,
    future=True,
    connect_args=connect_args,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
