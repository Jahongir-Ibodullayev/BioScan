"""Incidents — community xavf hisoboti (/api/incidents/).

Webapp + Flutter ikkalasi multipart FormData yuborishadi (photo bilan).
Webapp `reporter_name` kutadi (user.full_name).
"""
from __future__ import annotations

import os
import secrets
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select

from app.api.deps import DB, CurrentUser, OptionalUser
from app.core.config import settings
from app.models.incident import Incident
from app.models.user import User
from app.schemas.common import paginated

router = APIRouter(prefix="/incidents", tags=["incidents"])

MEDIA_INCIDENTS = Path(settings.MEDIA_ROOT) / "incidents"


def _to_out(i: Incident, reporter_name: str = "") -> dict:
    """Webapp + Flutter format — reporter_name (str) qaytaradi."""
    return {
        "id": i.id,
        "code": i.code,
        "category": i.category,
        "severity": i.severity,
        "status": i.status,
        "note": i.note,
        "photo": (f"{settings.MEDIA_URL}{i.photo}" if i.photo else None),
        "latitude": i.latitude,
        "longitude": i.longitude,
        "place_name": i.place_name,
        "reporter_name": reporter_name,
        "reporter_id": i.reporter_id,
        "created_at": i.created_at.isoformat(),
    }


@router.get("/")
async def list_incidents(
    db: DB,
    user: OptionalUser,
    category: Optional[str] = None,
    severity: Optional[str] = None,
    mine: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
) -> dict:
    base = select(Incident)
    if category:
        base = base.where(Incident.category == category)
    if severity:
        base = base.where(Incident.severity == severity)
    if mine and user:
        base = base.where(Incident.reporter_id == user.id)
    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0

    stmt = base.order_by(Incident.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.scalars(stmt)).all()

    # Reporter names ni alohida olib chiqamiz
    reporter_ids = {i.reporter_id for i in rows if i.reporter_id}
    name_map: dict[int, str] = {}
    if reporter_ids:
        users = (await db.scalars(select(User).where(User.id.in_(reporter_ids)))).all()
        name_map = {u.id: (u.full_name or u.phone) for u in users}

    items = [_to_out(i, reporter_name=name_map.get(i.reporter_id, "")) for i in rows]
    return paginated(items, total=total, page=page, page_size=page_size)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_incident(
    user: CurrentUser, db: DB,
    category: str = Form(...),
    severity: str = Form("orta"),
    note: str = Form(""),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    place_name: str = Form(""),
    photo: Optional[UploadFile] = File(None),
) -> dict:
    """multipart/form-data — webapp va Flutter shunday yuborishadi."""
    code = secrets.token_hex(4).upper()
    photo_path = None
    if photo and photo.filename:
        MEDIA_INCIDENTS.mkdir(parents=True, exist_ok=True)
        ext = os.path.splitext(photo.filename)[1] or ".jpg"
        fname = f"{code}_{secrets.token_hex(4)}{ext}"
        out = MEDIA_INCIDENTS / fname
        out.write_bytes(await photo.read())
        photo_path = f"incidents/{fname}"
    incident = Incident(
        reporter_id=user.id, code=code,
        category=category, severity=severity, note=note,
        latitude=latitude, longitude=longitude, place_name=place_name,
        photo=photo_path,
    )
    db.add(incident)
    await db.commit()
    await db.refresh(incident)
    return _to_out(incident, reporter_name=(user.full_name or user.phone))


@router.get("/{incident_id}/")
async def get_incident(incident_id: int, db: DB) -> dict:
    i = await db.scalar(select(Incident).where(Incident.id == incident_id))
    if not i:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Incident topilmadi")
    reporter_name = ""
    if i.reporter_id:
        u = await db.scalar(select(User).where(User.id == i.reporter_id))
        reporter_name = u.full_name or u.phone if u else ""
    return _to_out(i, reporter_name=reporter_name)
