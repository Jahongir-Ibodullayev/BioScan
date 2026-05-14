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


@router.get("/taxa/{taxon_id}/")
async def taxon_detail(taxon_id: int, locale: str = "uz") -> dict:
    """iNat taxon detail + Wikipedia summary (cascading uz → ru → en)."""
    data = await _cached_get(f"{INAT_BASE}/taxa/{taxon_id}", ttl=86400)
    if not data or not data.get("results"):
        return {"found": False}
    t = data["results"][0]
    canonical = t.get("name")
    common = t.get("preferred_common_name") or t.get("name")

    # Wikipedia cascade
    wiki = None
    for lang in [locale, "ru", "en"]:
        title = canonical
        w = await _cached_get(f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title}", ttl=86400)
        if w and w.get("extract"):
            wiki = {
                "extract": w.get("extract"),
                "thumbnail": (w.get("thumbnail") or {}).get("source"),
                "url": (w.get("content_urls") or {}).get("desktop", {}).get("page"),
                "lang": lang,
            }
            break

    return {
        "found": True,
        "id": t.get("id"),
        "name": common,
        "latin": canonical,
        "rank": t.get("rank"),
        "kingdom": t.get("ancestry"),
        "picture": (t.get("default_photo") or {}).get("medium_url"),
        "wikipedia": wiki,
    }


@router.get("/observations/")
async def search_observations(
    taxon_id: int = Query(...),
    lat: float | None = None,
    lng: float | None = None,
    radius: int | None = None,
    place: str = "uz",
    per_page: int = Query(30, ge=1, le=100),
) -> dict:
    """iNaturalist'dan eng yaqin kuzatuvlar (Flutter xarita uchun)."""
    params: dict = {"taxon_id": taxon_id, "per_page": per_page, "geo": "true"}
    if lat is not None and lng is not None:
        params["lat"] = lat
        params["lng"] = lng
        if radius:
            params["radius"] = radius
    if place:
        params["place_id"] = {"uz": 7080, "kz": 6926, "tj": 7037}.get(place.lower(), 7080)
    data = await _cached_get(f"{INAT_BASE}/observations", **params)
    if not data:
        return {"results": []}
    return {
        "count": data.get("total_results", 0),
        "results": [
            {
                "id": o.get("id"),
                "lat": o.get("geojson", {}).get("coordinates", [None, None])[1],
                "lng": o.get("geojson", {}).get("coordinates", [None, None])[0],
                "place": o.get("place_guess"),
                "observed_on": o.get("observed_on"),
                "photo": (o.get("photos") or [{}])[0].get("url"),
                "user": (o.get("user") or {}).get("login"),
            }
            for o in data.get("results", [])
        ],
    }


@router.get("/wiki/")
async def wiki_summary(title: str = Query(..., min_length=2), lang: str = "uz") -> dict:
    """Wikipedia REST API — qisqacha ma'lumot."""
    base = f"https://{lang}.wikipedia.org/api/rest_v1"
    data = await _cached_get(f"{base}/page/summary/{title}", ttl=86400)
    if not data:
        return {"found": False}
    return {
        "found": True,
        "title": data.get("title"),
        "extract": data.get("extract"),
        "thumbnail": (data.get("thumbnail") or {}).get("source"),
        "url": (data.get("content_urls") or {}).get("desktop", {}).get("page"),
    }


@router.get("/gbif/")
async def gbif_search(q: str = Query(..., min_length=2), limit: int = 10) -> dict:
    """GBIF taxon backbone qidirish."""
    data = await _cached_get(f"{GBIF_BASE}/species/search", q=q, limit=limit)
    if not data:
        return {"results": []}
    return {
        "results": [
            {
                "key": r.get("key"), "scientificName": r.get("scientificName"),
                "canonicalName": r.get("canonicalName"), "kingdom": r.get("kingdom"),
                "family": r.get("family"), "rank": r.get("rank"),
            }
            for r in data.get("results", [])
        ]
    }


@router.get("/enrich/")
async def enrich_species(latin: str = Query(..., min_length=2)) -> dict:
    """Tur haqida boyitilgan ma'lumot — iNat + GBIF birlashtirildi."""
    inat = await _cached_get(f"{INAT_BASE}/taxa", q=latin, per_page=1) or {}
    inat_first = (inat.get("results") or [{}])[0]
    gbif = await _cached_get(f"{GBIF_BASE}/species/match", name=latin) or {}
    return {
        "latin": latin,
        "common_name": inat_first.get("preferred_common_name"),
        "rank": inat_first.get("rank") or gbif.get("rank"),
        "kingdom": gbif.get("kingdom"),
        "family": gbif.get("family"),
        "photo": (inat_first.get("default_photo") or {}).get("medium_url"),
        "inat_id": inat_first.get("id"),
        "gbif_key": gbif.get("usageKey"),
    }


@router.get("/ai-help/")
async def ai_help(q: str = Query(..., min_length=2)) -> dict:
    """AI yordamchi — tur haqida qisqa javob."""
    from app.services.ai import openrouter_chat
    text = await openrouter_chat(
        f"Quyidagi biologik tur haqida qisqa ma'lumot ber (2-3 jumla): {q}",
        system="Sen biolog mutaxassissan. Markaziy Osiyo turlari bo'yicha.",
        max_tokens=200, temperature=0.4,
    )
    return {"answer": text}


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
