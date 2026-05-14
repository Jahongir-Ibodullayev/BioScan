"""Async Redis client — cache uchun."""
from __future__ import annotations

import json

import redis.asyncio as aioredis

from app.core.config import settings

_pool: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _pool
    if _pool is None:
        _pool = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=50,
        )
    return _pool


async def cache_get(key: str):
    """Redis ulanish yo'q bo'lsa — silently None qaytaramiz, app davom etadi."""
    try:
        r = get_redis()
        raw = await r.get(key)
    except Exception:
        return None
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return raw


async def cache_set(key: str, value, ttl: int = 600) -> None:
    try:
        r = get_redis()
        payload = json.dumps(value, default=str)
        await r.set(key, payload, ex=ttl)
    except Exception:
        pass  # Redis muvaffaqiyatsiz — app davom etadi


async def cache_delete(*keys: str) -> None:
    try:
        r = get_redis()
        if keys:
            await r.delete(*keys)
    except Exception:
        pass
