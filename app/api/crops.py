"""Crops router — /api/crops/* (list, advice, plans)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import CurrentUser, DB, OptionalUser
from app.core.ratelimit import check_advice_limit
from app.models.crops import Crop, CropPlan
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
async def list_crops(db: DB, category: str | None = None) -> dict:
    stmt = select(Crop)
    if category:
        stmt = stmt.where(Crop.category == category)
    rows = (await db.scalars(stmt.order_by(Crop.name_uz))).all()
    return {"results": [CropOut.model_validate(r).model_dump() for r in rows]}


@router.get("/advice/")
async def crop_advice(
    request: Request,
    db: DB,
    user: OptionalUser,
    crop_slug: str = Query(...),
    lat: float = Query(...),
    lon: float = Query(...),
    irrigation: str = Query("manual"),
    plot_size_m2: int | None = None,
    experience: str = "beginner",
) -> dict:
    """Rate: 20/min — Open-Meteo + OpenRouter chaqirilishi qimmat."""
    await check_advice_limit(request, user)
    crop = await db.scalar(select(Crop).where(Crop.slug == crop_slug))
    if not crop:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ekin topilmadi")
    return await build_advice(db, crop, lat, lon, irrigation, plot_size_m2, experience)


class PlanIn(BaseModel):
    crop_id: int
    lat: float
    lon: float
    irrigation: str = "manual"
    plot_size_m2: int | None = None
    planned_plant_date: str  # YYYY-MM-DD
    notes: str = ""
    notify: bool = True


@router.get("/plans/")
async def list_plans(user: CurrentUser, db: DB) -> dict:
    rows = (await db.scalars(
        select(CropPlan).where(CropPlan.user_id == user.id).order_by(CropPlan.created_at.desc())
    )).all()
    return {"results": [
        {
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
        for p in rows
    ]}


@router.post("/plans/", status_code=status.HTTP_201_CREATED)
async def create_plan(payload: PlanIn, user: CurrentUser, db: DB) -> dict:
    from datetime import date as _date
    try:
        planned = _date.fromisoformat(payload.planned_plant_date)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "planned_plant_date YYYY-MM-DD formatda bo'lsin")

    plan = CropPlan(
        user_id=user.id,
        crop_id=payload.crop_id,
        lat=payload.lat,
        lon=payload.lon,
        irrigation=payload.irrigation,
        plot_size_m2=payload.plot_size_m2,
        planned_plant_date=planned,
        notes=payload.notes,
        notify=payload.notify,
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return {"id": plan.id, "ok": True}
