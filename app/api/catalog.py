"""Catalog router — /api/species/."""
from __future__ import annotations

import hashlib
import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from sqlalchemy import or_, select, func

from app.api.deps import DB
from app.db.redis import cache_get, cache_set
from app.models.species import Species
from app.models.species_photo import SpeciesPhoto
from app.schemas.species import SpeciesDetail, SpeciesList, SpeciesListPage, SpeciesPhotoOut

router = APIRouter(prefix="/species", tags=["species"])

CACHE_TTL = 600  # 10 daqiqa


def _cache_key(path: str, qs: str) -> str:
    raw = f"{path}?{qs}"
    return f"species:v4:{hashlib.md5(raw.encode()).hexdigest()}"


@router.get("/", response_model=SpeciesListPage)
async def list_species(
    request: Request,
    response: Response,
    db: DB,
    category: Optional[str] = None,
    red_book: Optional[bool] = None,
    iucn: Optional[str] = None,
    region: Optional[str] = None,
    halal: Optional[str] = None,
    medicinal: Optional[bool] = None,
    honey: Optional[bool] = None,
    edible: Optional[bool] = None,
    livestock_toxic: Optional[str] = None,
    search: Optional[str] = Query(None, alias="search"),
    ordering: str = "name",
    page: int = 1,
    page_size: int = 20,
) -> SpeciesListPage:
    key = _cache_key(request.url.path, request.url.query)
    hit = await cache_get(key)
    if hit is not None:
        response.headers["X-Cache"] = "HIT"
        return SpeciesListPage(**hit)

    stmt = select(Species)
    if category:
        stmt = stmt.where(Species.category == category.lower())
    if red_book is not None:
        stmt = stmt.where(Species.red_book == red_book)
    if iucn:
        stmt = stmt.where(Species.iucn_status == iucn.upper())
    if region:
        stmt = stmt.where(Species.regions.ilike(f"%{region}%"))
    if halal:
        stmt = stmt.where(Species.halal_status == halal.lower())
    if medicinal is not None:
        stmt = stmt.where(Species.is_medicinal == medicinal)
    if honey is not None:
        stmt = stmt.where(Species.is_honey_plant == honey)
    if edible is not None:
        stmt = stmt.where(Species.is_edible == edible)
    if livestock_toxic:
        stmt = stmt.where(Species.livestock_danger == livestock_toxic.lower())
    if search:
        like = f"%{search}%"
        stmt = stmt.where(or_(
            Species.name.ilike(like),
            Species.latin.ilike(like),
            Species.summary.ilike(like),
            Species.description.ilike(like),
        ))

    # Count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt) or 0

    # Order + paginate
    order_col = Species.created_at if ordering.lstrip("-") == "created_at" else Species.name
    if ordering.startswith("-"):
        order_col = order_col.desc()
    stmt = stmt.order_by(order_col).offset((page - 1) * page_size).limit(page_size)

    rows = (await db.scalars(stmt)).all()
    page_data = SpeciesListPage(
        count=total,
        next=None,
        previous=None,
        results=[SpeciesList.model_validate(r) for r in rows],
    )
    await cache_set(key, json.loads(page_data.model_dump_json()), CACHE_TTL)
    response.headers["X-Cache"] = "MISS"
    return page_data


@router.get("/{slug}/", response_model=SpeciesDetail)
async def species_detail(
    slug: str,
    request: Request,
    response: Response,
    db: DB,
) -> SpeciesDetail:
    key = _cache_key(request.url.path, "")
    hit = await cache_get(key)
    if hit is not None:
        response.headers["X-Cache"] = "HIT"
        return SpeciesDetail(**hit)

    sp = await db.scalar(select(Species).where(Species.slug == slug))
    if not sp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tur topilmadi")

    photos_stmt = (
        select(SpeciesPhoto)
        .where(SpeciesPhoto.species_id == sp.id)
        .order_by(SpeciesPhoto.is_default.desc(), SpeciesPhoto.ordering, SpeciesPhoto.id)
    )
    photos = (await db.scalars(photos_stmt)).all()
    photos_out = [SpeciesPhotoOut.model_validate(p) for p in photos]

    base = SpeciesDetail.model_validate(sp).model_dump()
    base["photos"] = [p.model_dump() for p in photos_out]
    result = SpeciesDetail(**base)

    await cache_set(key, json.loads(result.model_dump_json()), CACHE_TTL)
    response.headers["X-Cache"] = "MISS"
    return result
