"""Cache utilities with sanitized keys + typed accessors.

Django's cache backend (memcached/locmem) rejects keys with:
  - spaces
  - control chars
  - length > 250

This module gives safe helpers that hash long/unsafe keys.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Callable, TypeVar

from django.core.cache import cache

T = TypeVar("T")


def make_key(namespace: str, *parts: Any) -> str:
    """Build a safe cache key by hashing complex parts.

    Returns: f"{namespace}:{sha1_prefix}" — always <60 chars, no spaces.
    """
    raw = json.dumps(list(parts), sort_keys=True, default=str)
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]
    return f"{namespace}:{digest}"


def get_or_set(namespace: str, parts: tuple[Any, ...], loader: Callable[[], T], *,
               ttl: int = 60 * 30) -> T:
    """Read from cache, or run loader() + cache the result.

    `loader` must be idempotent and pickle-safe.
    """
    key = make_key(namespace, *parts)
    hit = cache.get(key)
    if hit is not None:
        return hit  # type: ignore[return-value]
    value = loader()
    cache.set(key, value, ttl)
    return value


def invalidate(namespace: str, *parts: Any) -> None:
    cache.delete(make_key(namespace, *parts))


def negative_cache(namespace: str, *parts: Any, ttl: int = 60 * 10) -> None:
    """Mark a lookup as empty to avoid hammering upstream."""
    cache.set(make_key(namespace, *parts), "__miss__", ttl)


def is_negative(value: Any) -> bool:
    return value == "__miss__"
