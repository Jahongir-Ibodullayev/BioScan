"""Async PostgreSQL session — SQLAlchemy 2.0 + asyncpg.

Lazy engine — birinchi `_get_engine()` chaqirilganda yaratiladi.
Test'lar paytida `DATABASE_URL` environment'ni o'rnatib qo'ying.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """Barcha modellar shu Base'dan meros oladi."""


_engine: Optional[AsyncEngine] = None
_SessionLocal: Optional[async_sessionmaker[AsyncSession]] = None


def _build_engine() -> AsyncEngine:
    """Postgres: tuned pool. SQLite: default (tests)."""
    url = settings.DATABASE_URL
    kwargs: dict = {"echo": False, "pool_pre_ping": True}
    if url.startswith("postgresql"):
        kwargs.update(
            pool_size=20,
            max_overflow=10,
            pool_recycle=1800,
            pool_timeout=30,
            connect_args={"statement_cache_size": 1024, "server_settings": {"jit": "off"}},
        )
    return create_async_engine(url, **kwargs)


def _get_engine() -> AsyncEngine:
    """Lazy singleton — birinchi chaqirilganda quriladi."""
    global _engine, _SessionLocal
    if _engine is None:
        _engine = _build_engine()
        _SessionLocal = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)
    return _engine


def _get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    _get_engine()  # ensures _SessionLocal
    assert _SessionLocal is not None
    return _SessionLocal


async def dispose_engine() -> None:
    """Lifespan'da chaqiriladi — pool'ni yopadi."""
    global _engine, _SessionLocal
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _SessionLocal = None


def AsyncSessionLocal() -> AsyncSession:
    """Test/seed scripts uchun — `async with AsyncSessionLocal() as db:`."""
    return _get_sessionmaker()()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — har bir requestga alohida session."""
    sm = _get_sessionmaker()
    async with sm() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
