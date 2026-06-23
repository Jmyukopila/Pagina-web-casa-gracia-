"""
Async SQLAlchemy engine + session. The connection string comes from
settings.database_url, so YOU can point it at your own Postgres without
touching code (just set DATABASE_URL).
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from .config import settings


def _normalize(url: str) -> str:
    # Accept a plain postgresql:// URL (e.g. from Supabase) and use the async driver.
    if url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]
    return url


DB_URL = _normalize(settings.database_url)
IS_SQLITE = DB_URL.startswith("sqlite")

if IS_SQLITE:
    engine = create_async_engine(DB_URL, echo=False, future=True, pool_pre_ping=True)
else:
    # Supabase pooler (PgBouncer): NullPool + no prepared-statement cache avoids
    # "prepared statement already exists" errors; SSL is required.
    engine = create_async_engine(
        DB_URL, echo=False, future=True, poolclass=NullPool,
        connect_args={"ssl": "require", "statement_cache_size": 0,
                      "server_settings": {"application_name": "casagracia_web"}},
    )

SessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)


class Base(DeclarativeBase):
    pass


async def get_session() -> AsyncSession:
    """FastAPI dependency: yields a session and always closes it."""
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    """Dev convenience for SQLite only. The Supabase/Postgres schema is managed
    by the migrations in db/, so we never auto-create tables there."""
    from . import models  # noqa: F401  (register mappers)
    if not IS_SQLITE:
        return
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
