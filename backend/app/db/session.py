"""
FaultLens Backend — Database Session Factory (Phase 1)

Provides:
  - async_engine   : asyncpg-backed SQLAlchemy engine for the API
  - AsyncSessionLocal : async session factory for dependency injection
  - get_db()       : FastAPI dependency that yields a session per request
  - init_db()      : called at startup to verify connectivity
  - close_db()     : called at shutdown to dispose the connection pool
  - sync_engine    : synchronous engine for Alembic migrations only
"""
import logging
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# ── Module-level engine (created once at startup) ─────────────────────────────
_async_engine = None
AsyncSessionLocal: async_sessionmaker[AsyncSession] | None = None


class Base(DeclarativeBase):
    """
    Shared SQLAlchemy declarative base.
    All ORM models will inherit from this class.
    Import from here, not from sqlalchemy.orm directly.
    """
    pass


def _get_engine():
    """
    Create (or return cached) async engine.
    Called once during startup — never called per-request.
    """
    global _async_engine, AsyncSessionLocal
    if _async_engine is not None:
        return _async_engine

    settings = get_settings()

    if not settings.database_url:
        raise RuntimeError(
            "DATABASE_URL is not set. "
            "Check your .env file or environment variables."
        )

    _async_engine = create_async_engine(
        settings.database_url,
        # Pool settings — keep them conservative for Phase 1
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,   # verify connections before use (avoids stale conn errors)
        pool_timeout=30,       # seconds to wait for a free connection
        echo=False,            # set True temporarily for SQL debugging
    )

    AsyncSessionLocal = async_sessionmaker(
        bind=_async_engine,
        class_=AsyncSession,
        expire_on_commit=False,  # avoid lazy-load errors after commit
        autocommit=False,
        autoflush=False,
    )

    logger.info("Database engine created | url=%s", _redact_url(settings.database_url))
    return _async_engine


async def init_db() -> None:
    """
    Called at application startup.
    Verifies that the database is reachable with a simple SELECT 1.
    Raises on failure so startup aborts early with a clear message.
    """
    engine = _get_engine()
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection verified ✓")
    except Exception as exc:
        logger.error("Database connection FAILED: %s", exc)
        raise


async def close_db() -> None:
    """Called at application shutdown to release all pool connections."""
    global _async_engine
    if _async_engine is not None:
        await _async_engine.dispose()
        _async_engine = None
        logger.info("Database connection pool closed")


async def check_db() -> bool:
    """
    Lightweight connectivity probe used by GET /health/db.
    Returns True if the database responds, False otherwise.
    Never raises — callers handle the False case.
    """
    try:
        engine = _get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.warning("Database health check failed: %s", exc)
        return False


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency — yields a database session for each request.
    Session is automatically closed when the request completes.

    Usage:
        async def my_endpoint(db: AsyncSession = Depends(get_db)):
            ...
    """
    if AsyncSessionLocal is None:
        raise RuntimeError("Database not initialised. Call init_db() at startup.")

    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Helpers ───────────────────────────────────────────────────────────────────
def _redact_url(url: str) -> str:
    """Hide passwords in logged URLs."""
    try:
        from urllib.parse import urlparse, urlunparse
        parsed = urlparse(url)
        if parsed.password:
            netloc = parsed.netloc.replace(parsed.password, "***")
            return urlunparse(parsed._replace(netloc=netloc))
    except Exception:
        pass
    return url
