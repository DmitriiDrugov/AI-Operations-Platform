from contextlib import asynccontextmanager
from typing import AsyncGenerator

import asyncpg
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from .config import get_settings

_engine: AsyncEngine | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            echo=settings.is_development,
        )
    return _engine


AsyncSessionLocal = sessionmaker(
    class_=AsyncSession,
    expire_on_commit=False,
)


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = get_engine()
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def set_session_context(
    conn: asyncpg.Connection,
    organisation_id: str,
    user_id: str | None,
    role: str,
    trace_id: str | None = None,
) -> None:
    """Set Postgres session settings consumed by RLS policies and audit triggers."""
    await conn.execute("SELECT set_config('app.organisation_id', $1, true)", organisation_id)
    await conn.execute("SELECT set_config('app.role', $1, true)", role)
    if user_id:
        await conn.execute("SELECT set_config('app.current_user_id', $1, true)", user_id)
    if trace_id:
        await conn.execute("SELECT set_config('app.trace_id', $1, true)", trace_id)
