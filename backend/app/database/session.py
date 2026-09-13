from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings

import os

# Normalize Postgres connection strings if supplied as postgres:// or postgresql://
database_url = settings.DATABASE_URL
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif database_url.startswith("postgresql://") and not database_url.startswith("postgresql+asyncpg://"):
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif database_url.startswith("sqlite+aiosqlite:///") and not database_url.startswith("sqlite+aiosqlite:////"):
    # Anchor relative sqlite database file to backend directory
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    rel_path = database_url[len("sqlite+aiosqlite:///"):]
    if rel_path.startswith("./"):
        rel_path = rel_path[2:]
    abs_db_path = os.path.abspath(os.path.join(backend_dir, rel_path))
    database_url = f"sqlite+aiosqlite:///{abs_db_path}"

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
