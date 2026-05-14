"""Incidents — community xavf hisoboti (/api/incidents/)."""
from __future__ import annotations

import secrets

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import CurrentUser, DB, OptionalUser
from app.models.incident import Incident

router = APIRouter(prefix="/incidents", tags=["incidents"])


class IncidentOut(BaseModel):
    id: int
    code: str
    category: str
    severity: str
    status: str
    note: str
    latitude: float | None = None
    longitude: float | None = None
    place_name: str = ""
    created_at: str
    reporter_id: int | None = None


class IncidentIn(BaseModel):
    category: str
    severity: str = "orta"
    note: str = ""
    latitude: float | None = None
    longitude: float | None = None
    place_name: str = ""


def _to_out(i: Incident) -> IncidentOut:
    return IncidentOut(
        id=i.id, code=i.code, category=i.category, severity=i.severity, status=i.status,
        note=i.note, latitude=i.latitude, longitude=i.longitude,
        place_name=i.place_name, created_at=i.created_at.isoformat(),
        reporter_id=i.reporter_id,
    )


@router.get("/")
async def list_incidents(
    db: DB,
    user: OptionalUser,
    category: str | None = None,
    severity: str | None = None,
    mine: bool = False,
    limit: int = Query(100, ge=1, le=500),
) -> dict:
    stmt = select(Incident).order_by(Incident.created_at.desc()).limit(limit)
    if category:
        stmt = stmt.where(Incident.category == category)
    if severity:
        stmt = stmt.where(Incident.severity == severity)
    if mine and user:
        stmt = stmt.where(Incident.reporter_id == user.id)
    rows = (await db.scalars(stmt)).all()
    return {"count": len(rows), "results": [_to_out(i).model_dump() for i in rows]}


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=IncidentOut)
async def create_incident(payload: IncidentIn, user: CurrentUser, db: DB) -> IncidentOut:
    code = secrets.token_hex(4).upper()
    incident = Incident(
        reporter_id=user.id, code=code, **payload.model_dump(),
    )
    db.add(incident)
    await db.commit()
    await db.refresh(incident)
    return _to_out(incident)


@router.get("/{incident_id}/", response_model=IncidentOut)
async def get_incident(incident_id: int, db: DB) -> IncidentOut:
    i = await db.scalar(select(Incident).where(Incident.id == incident_id))
    if not i:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Incident topilmadi")
    return _to_out(i)
