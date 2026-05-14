"""Mapdata — /api/map/markers/."""
from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import DB
from app.models.mapdata import MapMarker

router = APIRouter(prefix="/map", tags=["map"])


class MarkerOut(BaseModel):
    id: int
    type: str
    label: str
    description: str = ""
    latitude: float
    longitude: float
    region: str = ""

    model_config = {"from_attributes": True}


@router.get("/markers/")
async def list_markers(
    db: DB,
    type: str | None = None,
    bbox: str | None = Query(None),
) -> dict:
    stmt = select(MapMarker).where(MapMarker.active == True)  # noqa: E712
    if type:
        stmt = stmt.where(MapMarker.type == type)
    if bbox:
        try:
            a, b, c, d = [float(x) for x in bbox.split(",")[:4]]
            stmt = stmt.where(
                MapMarker.latitude.between(min(a, c), max(a, c)),
                MapMarker.longitude.between(min(b, d), max(b, d)),
            )
        except ValueError:
            pass
    rows = (await db.scalars(stmt.limit(2000))).all()
    return {"results": [MarkerOut.model_validate(r).model_dump() for r in rows]}
