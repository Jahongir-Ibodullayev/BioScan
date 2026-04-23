"""Wikipedia client — REST v1 summaries.

Tries uz → ru → en cascade for best language match.
"""
from __future__ import annotations

from togai.core.cache import get_or_set
from togai.core.schemas import WikiSummary

from ._http import get_json


def _base(lang: str) -> str:
    return f"https://{lang}.wikipedia.org/api/rest_v1"


def get_summary(title: str, *, lang: str) -> WikiSummary | None:
    """Fetch one language's summary. Returns None if not found."""
    if not title:
        return None

    def _load() -> WikiSummary | None:
        try:
            data = get_json(f"{_base(lang)}/page/summary/{title.replace(' ', '_')}")
        except Exception:
            return None
        if not data or not data.get("extract"):
            return None
        return WikiSummary(
            title=data.get("title") or title,
            extract=data.get("extract") or "",
            url=((data.get("content_urls", {}) or {}).get("desktop") or {}).get("page") or "",
            lang=lang,
            thumbnail=(data.get("thumbnail") or {}).get("source"),
        )

    return get_or_set("wiki", (lang, title), _load, ttl=60 * 60 * 6)


def get_cascade(*titles_with_lang: tuple[str, str]) -> WikiSummary | None:
    """Try multiple (title, lang) pairs in order — return first match."""
    for title, lang in titles_with_lang:
        result = get_summary(title, lang=lang)
        if result:
            return result
    return None
