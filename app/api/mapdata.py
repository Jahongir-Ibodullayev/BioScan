"""Mapdata — /api/map/markers/."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import DB
from app.models.mapdata import MapMarker
from app.schemas.common import paginated

router = APIRouter(prefix="/map", tags=["map"])


class MarkerOut(BaseModel):
    id: int
    type: str
    label: str
    description: str = ""
    latitude: float
    longitude: float
    region: str = ""
    active: bool = True

    model_config = {"from_attributes": True}


@router.get("/markers/")
async def list_markers(
    db: DB,
    type: Optional[str] = None,
    # Webapp + Flutter: min_lat/max_lat/min_lng/max_lng
    min_lat: Optional[float] = None,
    max_lat: Optional[float] = None,
    min_lng: Optional[float] = None,
    max_lng: Optional[float] = None,
    # Eski: bbox="a,b,c,d"
    bbox: Optional[str] = Query(None),
) -> dict:
    stmt = select(MapMarker).where(MapMarker.active == True)  # noqa: E712
    if type:
        stmt = stmt.where(MapMarker.type == type)

    # 1) Yangi parametr formati
    if min_lat is not None and max_lat is not None:
        stmt = stmt.where(MapMarker.latitude.between(min_lat, max_lat))
    if min_lng is not None and max_lng is not None:
        stmt = stmt.where(MapMarker.longitude.between(min_lng, max_lng))

    # 2) Eski bbox formatini ham qo'llab quvvatlaymiz
    if bbox:
        try:
            a, b, c, d = (float(x) for x in bbox.split(",")[:4])
            stmt = stmt.where(
                MapMarker.latitude.between(min(a, c), max(a, c)),
                MapMarker.longitude.between(min(b, d), max(b, d)),
            )
        except ValueError:
            pass
    rows = (await db.scalars(stmt.limit(2000))).all()
    items = [MarkerOut.model_validate(r).model_dump() for r in rows]
    return paginated(items, total=len(items))
