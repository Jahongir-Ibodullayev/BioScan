"""Umumiy schemas — Paginated, count, next, previous (DRF bilan teng)."""
from __future__ import annotations

from typing import TypeVar


T = TypeVar("T")


def paginated(items: list, total: int | None = None, page: int = 1, page_size: int = 20) -> dict:
    """DRF Pagination'ga teng `{count, next, previous, results}` qaytaradi.

    Webapp va Flutter shu shape'ni kutadi (Paginated.fromJson).
    """
    if total is None:
        total = len(items)
    has_next = (page * page_size) < total
    has_prev = page > 1
    return {
        "count": total,
        "next": f"?page={page + 1}" if has_next else None,
        "previous": f"?page={page - 1}" if has_prev else None,
        "results": items,
    }
