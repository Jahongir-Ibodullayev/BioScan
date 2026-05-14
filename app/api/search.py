"""Search — iNat / GBIF / Wikipedia proxy (cached)."""
from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Query

from app.api.deps import DB
from app.db.redis import cache_get, cache_set
from app.models.species import Species
from sqlalchemy import select

log = logging.getLogger(__name__)
router = APIRouter(prefix="/search", tags=["search"])

INAT_BASE = "https://api.inaturalist.org/v1"
GBIF_BASE = "https://api.gbif.org/v1"
WIKI_BASE_UZ = "https://uz.wikipedia.org/api/rest_v1"


async def _cached_get(url: str, ttl: int = 3600, **kwargs) -> dict | None:
    key = f"ext-api:{url}:{httpx.QueryParams(kwargs)}"
    hit = await cache_get(key)
    if hit is not None:
        return hit
    try:
        async with httpx.AsyncClient(timeout=10.0) as c:
            r = await c.get(url, params=kwargs)
            r.raise_for_status()
            data = r.json()
        await cache_set(key, data, ttl)
        return data
    except httpx.HTTPError as e:
        log.warning("ext API %s failed: %s", url, e)
        return None


@router.get("/taxa/")
async def search_taxa(q: str = Query(..., min_length=2), db: DB = None) -> dict:
    """Lokal katalog → iNat → GBIF fallback. Birinchi mos kelganini qaytaradi."""
    # Lokal Species
    if db is not None:
        like = f"%{q}%"
        local = await db.scalar(
            select(Species).where(
                (Species.name.ilike(like)) | (Species.latin.ilike(like))
            ).limit(1)
        )
        if local:
            return {
                "source": "local",
                "results": [{
                    "id": local.id, "slug": local.slug, "name": local.name,
                    "latin": local.latin, "category": local.category,
                    "picture": local.picture,
                }],
            }

    # iNat
    data = await _cached_get(f"{INAT_BASE}/taxa/autocomplete", q=q, per_page=10)
    if data and data.get("results"):
        results = [
            {
                "id": r.get("id"),
                "name": r.get("preferred_common_name") or r.get("name"),
                "latin": r.get("name"),
                "picture": (r.get("default_photo") or {}).get("medium_url"),
            }
            for r in data.get("results", [])
        ]
        return {"source": "inat", "results": results}

    return {"source": "none", "results": []}


@router.get("/browse/")
async def browse(category: str = "giyoh", db: DB = None) -> dict:
    """Foydalanuvchi 'giyoh / daraxt / gul ...' tablarini bossa."""
    if db is None:
        return {"results": []}
    rows = (await db.scalars(
        select(Species).where(Species.category == category).order_by(Species.name).limit(60)
    )).all()
    return {
        "results": [
            {
                "id": r.id, "slug": r.slug, "name": r.name, "latin": r.latin,
                "category": r.category, "icon_name": r.icon_name,
                "summary": r.summary, "picture": r.picture,
            }
            for r in rows
        ]
    }
