"""Crops router — /api/crops/*.

Webapp + Flutter contract:
  GET  /crops/list/            — Paginated
  GET  /crops/advice/          — query params
  POST /crops/advice/          — body, Flutter
  GET  /crops/plans/           — Paginated
  POST /crops/plans/           — Flutter: crop_slug (string), Webapp: crop_id
  DELETE /crops/plans/{id}/    — Flutter
"""
from __future__ import annotations

from datetime import date as _date
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import func, select

from app.api.deps import DB, CurrentUser, OptionalUser
from app.core.ratelimit import check_advice_limit
from app.models.crops import Crop, CropPlan
from app.schemas.common import paginated
from app.services.advice import build_advice

router = APIRouter(prefix="/crops", tags=["crops"])


class CropOut(BaseModel):
    id: int
    slug: str
    name_uz: str
    name_lat: str
    category: str
    icon_name: str
    image_url: str
    model_config = {"from_attributes": True}


@router.get("/list/")
async def list_crops(
    db: DB, category: Optional[str] = None,
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
) -> dict:
    base = select(Crop)
    if category:
        base = base.where(Crop.category == category)
    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0
    stmt = base.order_by(Crop.name_uz).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.scalars(stmt)).all()
    items = [CropOut.model_validate(r).model_dump() for r in rows]
    return paginated(items, total=total, page=page, page_size=page_size)


# ----------------------------------------------------------------------
# Advice — GET (query) + POST (body) ikkalasini ham qo'llaymiz
# ----------------------------------------------------------------------
class AdviceIn(BaseModel):
    crop_slug: str
    lat: float
    lon: float
    irrigation: str = "manual"
    plot_size_m2: Optional[int] = None
    experience: str = "beginner"


async def _advice_impl(request, user, db, crop_slug, lat, lon, irrigation, plot_size_m2, experience):
    await check_advice_limit(request, user)
    crop = await db.scalar(select(Crop).where(Crop.slug == crop_slug))
    if not crop:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ekin topilmadi")
    return await build_advice(db, crop, lat, lon, irrigation, plot_size_m2, experience)


@router.get("/advice/")
async def crop_advice_get(
    request: Request, db: DB, user: OptionalUser,
    crop_slug: str = Query(...),
    lat: float = Query(...),
    lon: float = Query(...),
    irrigation: str = Query("manual"),
    plot_size_m2: Optional[int] = None,
    experience: str = "beginner",
) -> dict:
    return await _advice_impl(request, user, db, crop_slug, lat, lon, irrigation, plot_size_m2, experience)


@router.post("/advice/")
async def crop_advice_post(
    payload: AdviceIn, request: Request, db: DB, user: OptionalUser,
) -> dict:
    """Flutter POST formati."""
    return await _advice_impl(
        request, user, db, payload.crop_slug, payload.lat, payload.lon,
        payload.irrigation, payload.plot_size_m2, payload.experience,
    )


# ----------------------------------------------------------------------
# Plans CRUD
# ----------------------------------------------------------------------
class PlanIn(BaseModel):
    # Flutter `crop_slug`, Webapp `crop_id` — ikkalasi qabul qilinadi
    crop_slug: Optional[str] = None
    crop_id: Optional[int] = None
    lat: float
    lon: float
    irrigation: str = "manual"
    plot_size_m2: Optional[int] = None
    planned_plant_date: str  # YYYY-MM-DD
    expected_harvest_date: Optional[str] = None
    notes: str = ""
    notify: bool = True


def _plan_dict(p: CropPlan) -> dict:
    return {
        "id": p.id,
        "crop_id": p.crop_id,
        "lat": float(p.lat),
        "lon": float(p.lon),
        "irrigation": p.irrigation,
        "plot_size_m2": p.plot_size_m2,
        "planned_plant_date": p.planned_plant_date.isoformat() if p.planned_plant_date else None,
        "expected_harvest_date": p.expected_harvest_date.isoformat() if p.expected_harvest_date else None,
        "notes": p.notes,
        "notify": p.notify,
        "created_at": p.created_at.isoformat(),
    }


@router.get("/plans/")
async def list_plans(
    user: CurrentUser, db: DB,
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
) -> dict:
    base = select(CropPlan).where(CropPlan.user_id == user.id)
    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0
    stmt = base.order_by(CropPlan.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.scalars(stmt)).all()
    return paginated([_plan_dict(p) for p in rows], total=total, page=page, page_size=page_size)


@router.post("/plans/", status_code=status.HTTP_201_CREATED)
async def create_plan(payload: PlanIn, user: CurrentUser, db: DB) -> dict:
    # crop_id ni topish
    crop_id = payload.crop_id
    if crop_id is None and payload.crop_slug:
        crop = await db.scalar(select(Crop).where(Crop.slug == payload.crop_slug))
        if not crop:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Ekin topilmadi")
        crop_id = crop.id
    if crop_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "crop_id yoki crop_slug majburiy")

    try:
        planned = _date.fromisoformat(payload.planned_plant_date)
    except ValueError as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "planned_plant_date YYYY-MM-DD formatda"
        ) from exc

    harvest = None
    if payload.expected_harvest_date:
        try:
            harvest = _date.fromisoformat(payload.expected_harvest_date)
        except ValueError:
            pass

    plan = CropPlan(
        user_id=user.id,
        crop_id=crop_id,
        lat=payload.lat,
        lon=payload.lon,
        irrigation=payload.irrigation,
        plot_size_m2=payload.plot_size_m2,
        planned_plant_date=planned,
        expected_harvest_date=harvest,
        notes=payload.notes,
        notify=payload.notify,
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return _plan_dict(plan)


@router.get("/plans/{plan_id}/")
async def get_plan(plan_id: int, user: CurrentUser, db: DB) -> dict:
    p = await db.scalar(
        select(CropPlan).where(CropPlan.id == plan_id, CropPlan.user_id == user.id)
    )
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reja topilmadi")
    return _plan_dict(p)


@router.delete("/plans/{plan_id}/")
async def delete_plan(plan_id: int, user: CurrentUser, db: DB) -> dict:
    p = await db.scalar(
        select(CropPlan).where(CropPlan.id == plan_id, CropPlan.user_id == user.id)
    )
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reja topilmadi")
    await db.delete(p)
    await db.commit()
    return {"ok": True}
