"""Observations router — /api/observations/*.

Django bilan teng:
  GET    /api/observations/             → joriy user observations
  POST   /api/observations/             → create
  POST   /api/observations/scan/        → AI scan (anonymous OK)
  GET    /api/observations/public/      → global feed
  GET    /api/observations/yearbook/?year=YYYY → PDF
"""
from __future__ import annotations

import secrets
from datetime import datetime

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import Response

from pydantic import BaseModel
from slugify import slugify
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DB, OptionalUser
from app.core.config import settings
from app.models.observation import Observation
from app.models.species import Species
from app.services.ai import identify_species_from_image
from app.services.yearbook import render_yearbook

router = APIRouter(prefix="/observations", tags=["observations"])


from app.core.ratelimit import check_scan_limit


class SpeciesNested(BaseModel):
    id: int
    slug: str
    name: str
    latin: str = ""
    category: str
    icon_name: str = "leaf"
    picture: str = ""

    model_config = {"from_attributes": True}


class ObservationOut(BaseModel):
    id: int
    photo: str | None = None
    ai_confidence: float
    note: str
    latitude: float | None = None
    longitude: float | None = None
    place_name: str = ""
    created_at: str
    species: SpeciesNested | None = None

    @classmethod
    def from_obs(cls, obs: Observation):
        # Species selectinload bilan ekspilist olingan bo'ladi.
        # Endpoint tomondan model_dump qilingandan keyin to'ldiramiz.
        return cls(
            id=obs.id,
            photo=f"{settings.MEDIA_URL}{obs.photo}" if obs.photo else None,
            ai_confidence=obs.ai_confidence,
            note=obs.note,
            latitude=obs.latitude,
            longitude=obs.longitude,
            place_name=obs.place_name,
            created_at=obs.created_at.isoformat(),
        )


@router.get("/")
async def list_my_observations(user: CurrentUser, db: DB) -> dict:
    """User'ning kuzatuvlari — composite index (user_id, created_at) tez ishlatadi.

    selectinload bilan species N+1'siz olinadi (bitta IN query).
    """
    stmt = (
        select(Observation)
        .options(selectinload(Observation.species))
        .where(Observation.user_id == user.id)
        .order_by(Observation.created_at.desc())
    )
    rows = (await db.scalars(stmt)).all()
    out = []
    for o in rows:
        d = ObservationOut.from_obs(o).model_dump()
        if o.species:
            d["species"] = SpeciesNested.model_validate(o.species).model_dump()
        out.append(d)
    return {"results": out}


@router.get("/public/")
async def public_feed(
    db: DB,
    bbox: str | None = None,
    limit: int = Query(200, ge=1, le=500),
) -> dict:
    stmt = (
        select(Observation)
        .options(selectinload(Observation.species))
        .where(Observation.latitude.is_not(None), Observation.longitude.is_not(None))
        .order_by(Observation.created_at.desc())
    )
    if bbox:
        try:
            a, b, c, d = [float(x) for x in bbox.split(",")[:4]]
            stmt = stmt.where(
                Observation.latitude.between(min(a, c), max(a, c)),
                Observation.longitude.between(min(b, d), max(b, d)),
            )
        except (TypeError, ValueError):
            pass
    rows = (await db.scalars(stmt.limit(limit))).all()
    return {
        "count": len(rows),
        "results": [ObservationOut.from_obs(o).model_dump() for o in rows],
    }


@router.post("/scan/")
async def scan_image(
    request: Request,
    db: DB,
    user: OptionalUser,
    photo: UploadFile = File(...),
    lat: float | None = Form(None),
    lng: float | None = Form(None),
) -> dict:
    """AI tur aniqlash — Vision API. Auth ixtiyoriy. Rate: configured per-min."""
    await check_scan_limit(request, user)
    image_bytes = await photo.read()
    if not image_bytes:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Rasm bo'sh")

    result = await identify_species_from_image(image_bytes, mime=photo.content_type or "image/jpeg")

    if not result.get("found"):
        return {
            "identified": False,
            "reason": result.get("reason") or "Rasmda biologik tur topilmadi",
        }

    latin = (result.get("latin") or "").strip()
    name = (result.get("name") or "").strip() or latin
    slug = slugify(latin or name) or f"tur-{secrets.token_hex(4)}"

    # Upsert species
    sp = await db.scalar(select(Species).where(Species.slug == slug))
    defaults = {
        "name": name or latin,
        "latin": latin,
        "category": result.get("category") or "giyoh",
        "summary": (result.get("summary") or "")[:280],
        "description": result.get("description") or "",
        "habitat": result.get("habitat") or "",
        "uses": result.get("uses") or "",
        "warnings": result.get("warnings") or "",
        "first_aid": result.get("first_aid") or "",
        "regions": result.get("regions") or "",
    }
    if sp is None:
        sp = Species(slug=slug, **defaults)
        db.add(sp)
    else:
        for k, v in defaults.items():
            if v:
                setattr(sp, k, v)
    await db.commit()
    await db.refresh(sp)

    # Observation faqat auth bo'lsa saqlanadi
    obs_id = None
    if user is not None:
        obs = Observation(
            user_id=user.id,
            species_id=sp.id,
            ai_confidence=float(result.get("confidence") or 0.0),
            latitude=lat,
            longitude=lng,
        )
        db.add(obs)
        await db.commit()
        await db.refresh(obs)
        obs_id = obs.id

    return {
        "identified": True,
        "species": SpeciesNested.model_validate(sp).model_dump(),
        "confidence": float(result.get("confidence") or 0.0),
        "observation_id": obs_id,
    }


class ObservationIn(BaseModel):
    species_slug: str | None = None
    note: str = ""
    latitude: float | None = None
    longitude: float | None = None
    place_name: str = ""


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_observation(payload: ObservationIn, user: CurrentUser, db: DB) -> dict:
    sp_id = None
    if payload.species_slug:
        sp = await db.scalar(select(Species).where(Species.slug == payload.species_slug))
        if sp:
            sp_id = sp.id
    obs = Observation(
        user_id=user.id, species_id=sp_id,
        note=payload.note, latitude=payload.latitude,
        longitude=payload.longitude, place_name=payload.place_name,
    )
    db.add(obs)
    await db.commit()
    await db.refresh(obs)
    return ObservationOut.from_obs(obs).model_dump()


@router.get("/{obs_id}/")
async def get_observation(obs_id: int, user: CurrentUser, db: DB) -> dict:
    obs = await db.scalar(
        select(Observation)
        .options(selectinload(Observation.species))
        .where(Observation.id == obs_id, Observation.user_id == user.id)
    )
    if not obs:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kuzatuv topilmadi")
    d = ObservationOut.from_obs(obs).model_dump()
    if obs.species:
        d["species"] = SpeciesNested.model_validate(obs.species).model_dump()
    return d


@router.delete("/{obs_id}/")
async def delete_observation(obs_id: int, user: CurrentUser, db: DB) -> dict:
    obs = await db.scalar(
        select(Observation).where(Observation.id == obs_id, Observation.user_id == user.id)
    )
    if not obs:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kuzatuv topilmadi")
    await db.delete(obs)
    await db.commit()
    return {"ok": True}


@router.post("/yearbook/build/")
async def yearbook_build(user: CurrentUser, year: int = Query(None)) -> dict:
    """Yillik PDF'ni Celery'ga qo'yadi. Bloklamasdan task_id qaytaradi.

    Foydalanuvchi keyin /api/observations/yearbook/status/{task_id}/'dan natija olishi mumkin.
    Yoki to'g'ridan-to'g'ri /api/observations/yearbook/'dan (sync, kichik yillar uchun OK).
    """
    from app.tasks import build_yearbook_pdf
    y = year or datetime.now().year
    result = build_yearbook_pdf.delay(user.id, y)
    return {"task_id": result.id, "status": "queued", "year": y}


@router.get("/yearbook/status/{task_id}/")
async def yearbook_status(task_id: str, user: CurrentUser) -> dict:
    """Celery task holatini ko'rsatadi."""
    from app.tasks import build_yearbook_pdf
    result = build_yearbook_pdf.AsyncResult(task_id)
    if result.state == "SUCCESS":
        info = result.result or {}
        return {"status": "done", **info}
    return {"status": result.state.lower(), "task_id": task_id}


@router.get("/yearbook/")
async def yearbook(
    user: CurrentUser,
    db: DB,
    year: int = Query(None),
) -> Response:
    """Sync PDF (kichik yillar uchun). Katta to'plamlar uchun /yearbook/build/ ishlating."""
    y = year or datetime.now().year
    start = datetime(y, 1, 1)
    end = datetime(y + 1, 1, 1)
    stmt = (
        select(Observation)
        .where(
            Observation.user_id == user.id,
            Observation.created_at >= start,
            Observation.created_at < end,
        )
        .order_by(Observation.created_at)
    )
    obs_rows = (await db.scalars(stmt)).all()

    sp_ids = {o.species_id for o in obs_rows if o.species_id}
    species_map: dict[int, Species] = {}
    if sp_ids:
        sp_rows = (await db.scalars(select(Species).where(Species.id.in_(sp_ids)))).all()
        species_map = {s.id: s for s in sp_rows}

    payload = []
    for o in obs_rows:
        sp = species_map.get(o.species_id) if o.species_id else None
        payload.append({
            "species_id": o.species_id,
            "species_name": sp.name if sp else None,
            "species_latin": sp.latin if sp else None,
            "species_category": sp.category if sp else None,
            "species_redbook": bool(sp and sp.red_book),
            "species_picture": (sp.picture if sp else None),
            "ai_confidence": o.ai_confidence,
            "note": o.note,
            "latitude": o.latitude,
            "longitude": o.longitude,
            "place_name": o.place_name,
            "photo": (f"{settings.MEDIA_URL}{o.photo}" if o.photo else None),
            "created_at": o.created_at.isoformat() if o.created_at else None,
        })

    pdf_bytes = await render_yearbook(user.full_name or user.phone, y, payload)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="bioscan-kundalik-{y}.pdf"',
        },
    )
