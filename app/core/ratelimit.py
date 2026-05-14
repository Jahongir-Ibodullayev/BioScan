"""Rate limiting — Redis primary, in-memory fallback (silent skip emas).

Eski versiya: Redis o'lganda silently skip — bu cheksiz scan'ga yo'l ochar edi.
Yangi versiya: Redis fail → memory'da hisoblash + WARN log.
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request

from app.core.config import settings
from app.db.redis import get_redis

log = logging.getLogger(__name__)

# In-memory fallback: {key: deque[timestamp]}
_memory_buckets: dict[str, deque[float]] = defaultdict(deque)
_memory_lock = Lock()


def _client_key(request: Request, user) -> str:
    """Auth user bo'lsa user:<id>, bo'lmasa IP."""
    if user:
        return f"user:{user.id}"
    return f"ip:{request.client.host if request.client else 'unknown'}"


async def check_rate_limit(
    request: Request,
    user,
    *,
    bucket: str,
    limit_per_min: int,
) -> None:
    """Bir vaqt oynasi (60 sek)da N ta so'rovga ruxsat.

    Avval Redis. Redis ishlamasa — process memory bilan davom etadi.
    """
    client = _client_key(request, user)
    key = f"ratelimit:{bucket}:{client}"
    now = time.time()
    window_start = now - 60.0

    # 1. Redis (asosiy)
    try:
        r = get_redis()
        count = await r.incr(key)
        if count == 1:
            await r.expire(key, 60)
        if count > limit_per_min:
            ttl = await r.ttl(key)
            raise HTTPException(
                429,
                f"Juda ko'p so'rov. {ttl} sekunddan keyin qayta urinib ko'ring.",
                headers={"Retry-After": str(ttl)},
            )
        return
    except HTTPException:
        raise
    except Exception as e:
        log.warning("Redis rate-limit fail, memory fallback: %s", e)

    # 2. Memory fallback — bir necha worker bo'lsa har birida alohida, lekin
    #    abuse cheklanadi (Redis qayta tirilgunga qadar — ko'pi bilan 1-2 daq).
    with _memory_lock:
        bucket_q = _memory_buckets[key]
        # Eski timestamps tashlash
        while bucket_q and bucket_q[0] < window_start:
            bucket_q.popleft()
        if len(bucket_q) >= limit_per_min:
            oldest = bucket_q[0]
            retry_after = max(1, int(60 - (now - oldest)))
            raise HTTPException(
                429,
                f"Juda ko'p so'rov. {retry_after} sekunddan keyin qayta urinib ko'ring.",
                headers={"Retry-After": str(retry_after)},
            )
        bucket_q.append(now)


# Convenience wrappers
async def check_scan_limit(request: Request, user) -> None:
    await check_rate_limit(
        request, user,
        bucket="scan",
        limit_per_min=settings.RATE_LIMIT_SCAN_PER_MIN,
    )


async def check_advice_limit(request: Request, user) -> None:
    await check_rate_limit(
        request, user,
        bucket="advice",
        limit_per_min=settings.RATE_LIMIT_ADVICE_PER_MIN,
    )


async def check_auth_limit(request: Request, user) -> None:
    await check_rate_limit(
        request, user,
        bucket="auth",
        limit_per_min=settings.RATE_LIMIT_AUTH_PER_MIN,
    )
