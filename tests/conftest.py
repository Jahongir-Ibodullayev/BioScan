"""Test fixtures — in-memory SQLite + httpx AsyncClient."""
from __future__ import annotations

import os

# Test environment'da SECRET_KEY barqaror bo'lsin
os.environ.setdefault("SECRET_KEY", "test-secret-key-very-long-and-stable-string")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://invalid-host-for-testing:6379/15")
os.environ.setdefault("DEBUG", "true")

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.session import Base, get_db
from app.main import app

# In-memory shared SQLite — har bir test uchun yangi
_test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
)
_TestSession = async_sessionmaker(_test_engine, expire_on_commit=False)


async def _override_get_db():
    async with _TestSession() as session:
        try:
            yield session
        finally:
            await session.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest_asyncio.fixture(autouse=True)
async def _setup_db():
    """Har test oldidan jadvallarni yangidan yaratamiz."""
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
