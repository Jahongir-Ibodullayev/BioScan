"""Saved species — /api/saved/ va /api/collections/ (webapp alias).

Webapp + Flutter:
  POST /collections/  body {species: <id>, note}   ← species ID (slug emas!)
  DELETE /collections/{id}/                         ← saved.id (slug emas!)
  GET    /collections/  results: [{id, species: id, species_detail: nested, note}]
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUser, DB
from app.models.saved import SavedSpecies
from app.models.species import Species
from app.schemas.common import paginated

router = APIRouter(prefix="/saved", tags=["saved"])
collections_router = APIRouter(prefix="/collections", tags=["collections"])


class SaveByIdIn(BaseModel):
    species: int  # ID
    note: str = ""


class SaveBySlugIn(BaseModel):
    species_slug: str
    note: str = ""


def _species_detail(sp: Species) -> dict:
    return {
        "id": sp.id, "slug": sp.slug, "name": sp.name, "latin": sp.latin,
        "category": sp.category, "icon_name": sp.icon_name,
        "picture": sp.picture, "summary": sp.summary,
    }


async def _list_saved_impl(user, db, page: int, page_size: int) -> dict:
    base = select(SavedSpecies).where(SavedSpecies.user_id == user.id)
    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0

    stmt = (
        select(SavedSpecies, Species)
        .join(Species, Species.id == SavedSpecies.species_id)
        .where(SavedSpecies.user_id == user.id)
        .order_by(SavedSpecies.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    rows = (await db.execute(stmt)).all()
    items = [
        {
            "id": saved.id,
            "species": sp.id,
            "species_detail": _species_detail(sp),
            "note": saved.note,
            "created_at": saved.created_at.isoformat(),
        }
        for saved, sp in rows
    ]
    return paginated(items, total=total, page=page, page_size=page_size)


# ----------------------------------------------------------------------
# /saved/ (slug-based, backward compat)
# ----------------------------------------------------------------------
@router.get("/")
async def list_saved(
    user: CurrentUser, db: DB,
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
) -> dict:
    return await _list_saved_impl(user, db, page, page_size)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def save_by_slug(payload: SaveBySlugIn, user: CurrentUser, db: DB) -> dict:
    sp = await db.scalar(select(Species).where(Species.slug == payload.species_slug))
    if not sp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tur topilmadi")
    return await _do_save(sp.id, payload.note, user, db)


@router.delete("/{slug}/")
async def unsave_by_slug(slug: str, user: CurrentUser, db: DB) -> dict:
    sp = await db.scalar(select(Species).where(Species.slug == slug))
    if not sp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tur topilmadi")
    await db.execute(
        delete(SavedSpecies).where(
            SavedSpecies.user_id == user.id, SavedSpecies.species_id == sp.id
        )
    )
    await db.commit()
    return {"ok": True}


# ----------------------------------------------------------------------
# /collections/ — webapp + Flutter formati (ID-based)
# ----------------------------------------------------------------------
async def _do_save(species_id: int, note: str, user, db) -> dict:
    # Avval mavjudligini tekshiramiz (race condition'siz)
    existing = await db.scalar(
        select(SavedSpecies).where(
            SavedSpecies.user_id == user.id, SavedSpecies.species_id == species_id
        )
    )
    if existing:
        return {"ok": True, "already": True, "id": existing.id}
    item = SavedSpecies(user_id=user.id, species_id=species_id, note=note)
    db.add(item)
    try:
        await db.commit()
        await db.refresh(item)
    except IntegrityError:
        await db.rollback()
        return {"ok": True, "already": True}
    return {"ok": True, "id": item.id}


@collections_router.get("/")
async def list_collections(
    user: CurrentUser, db: DB,
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
) -> dict:
    return await _list_saved_impl(user, db, page, page_size)


@collections_router.post("/", status_code=status.HTTP_201_CREATED)
async def add_collection(payload: SaveByIdIn, user: CurrentUser, db: DB) -> dict:
    """Webapp + Flutter: {species: <ID>, note}."""
    sp = await db.scalar(select(Species).where(Species.id == payload.species))
    if not sp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tur topilmadi")
    return await _do_save(sp.id, payload.note, user, db)


@collections_router.delete("/{saved_id}/")
async def remove_collection(saved_id: int, user: CurrentUser, db: DB) -> dict:
    """Webapp + Flutter: DELETE /collections/{saved.id}/."""
    item = await db.scalar(
        select(SavedSpecies).where(
            SavedSpecies.id == saved_id, SavedSpecies.user_id == user.id
        )
    )
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Saqlangan tur topilmadi")
    await db.delete(item)
    await db.commit()
    return {"ok": True}
