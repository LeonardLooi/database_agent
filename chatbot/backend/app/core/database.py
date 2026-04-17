from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


def _ensure_db_dir() -> None:
    """Create the directory for a file-based SQLite database if it doesn't exist."""
    url = settings.DATABASE_URL
    if "sqlite" not in url:
        return
    # Strip the driver prefix to get the raw path, e.g. sqlite+aiosqlite:///./data/chatbot.db
    path_part = url.split("///", 1)[-1]
    db_path = Path(path_part)
    db_path.parent.mkdir(parents=True, exist_ok=True)


_ensure_db_dir()

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
