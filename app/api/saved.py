"""Saved species — /api/saved/."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUser, DB
from app.models.saved import SavedSpecies
from app.models.species import Species

router = APIRouter(prefix="/saved", tags=["saved"])


class SaveIn(BaseModel):
    species_slug: str
    note: str = ""


@router.get("/")
async def list_saved(user: CurrentUser, db: DB) -> dict:
    stmt = (
        select(SavedSpecies, Species)
        .join(Species, Species.id == SavedSpecies.species_id)
        .where(SavedSpecies.user_id == user.id)
        .order_by(SavedSpecies.created_at.desc())
    )
    rows = (await db.execute(stmt)).all()
    return {
        "results": [
            {
                "id": saved.id,
                "note": saved.note,
                "created_at": saved.created_at.isoformat(),
                "species": {
                    "id": sp.id, "slug": sp.slug, "name": sp.name, "latin": sp.latin,
                    "category": sp.category, "icon_name": sp.icon_name,
                    "picture": sp.picture, "summary": sp.summary,
                },
            }
            for saved, sp in rows
        ]
    }


@router.post("/", status_code=status.HTTP_201_CREATED)
async def save(payload: SaveIn, user: CurrentUser, db: DB) -> dict:
    sp = await db.scalar(select(Species).where(Species.slug == payload.species_slug))
    if not sp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tur topilmadi")
    try:
        item = SavedSpecies(user_id=user.id, species_id=sp.id, note=payload.note)
        db.add(item)
        await db.commit()
        await db.refresh(item)
    except IntegrityError:
        await db.rollback()
        return {"ok": True, "already": True}
    return {"ok": True, "id": item.id}


@router.delete("/{slug}/")
async def unsave(slug: str, user: CurrentUser, db: DB) -> dict:
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
