"""Ads router — /api/ads/active/, /api/ads/{id}/click/."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import select, update

from app.api.deps import DB
from app.core.config import settings
from app.models.ads import Ad
from pydantic import BaseModel

router = APIRouter(prefix="/ads", tags=["ads"])


class AdOut(BaseModel):
    id: int
    title: str
    headline: str
    body: str
    cta_text: str
    target_url: str
    picture: str | None = None
    duration_seconds: int
    skippable_after: int


def _picture(ad: Ad) -> str | None:
    if ad.image:
        return f"{settings.MEDIA_URL}{ad.image}"
    return ad.image_url or None


@router.get("/active/")
async def get_active_ad(
    response: Response,
    db: DB,
    slot: str = Query("splash"),
    platform: str = Query("web"),
):
    """Eng yuqori prioritetli faol reklama. Yo'q bo'lsa 204."""
    now = datetime.now(timezone.utc)
    stmt = (
        select(Ad)
        .where(
            Ad.slot == slot,
            Ad.is_active == True,  # noqa: E712
            Ad.starts_at <= now,
            (Ad.ends_at.is_(None)) | (Ad.ends_at > now),
            Ad.platform.in_([platform, "all"]),
        )
        .order_by(Ad.priority.desc(), Ad.created_at.desc())
        .limit(1)
    )
    ad = await db.scalar(stmt)
    if not ad:
        response.status_code = status.HTTP_204_NO_CONTENT
        return None

    # Impression atomic increment
    await db.execute(update(Ad).where(Ad.id == ad.id).values(impressions=Ad.impressions + 1))
    await db.commit()

    return AdOut(
        id=ad.id,
        title=ad.title,
        headline=ad.headline,
        body=ad.body,
        cta_text=ad.cta_text,
        target_url=ad.target_url,
        picture=_picture(ad),
        duration_seconds=ad.duration_seconds,
        skippable_after=ad.skippable_after,
    )


@router.post("/{ad_id}/click/")
async def click_ad(ad_id: int, db: DB) -> dict:
    """Click counter — atomik inkrement."""
    result = await db.execute(
        update(Ad).where(Ad.id == ad_id).values(clicks=Ad.clicks + 1)
    )
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reklama topilmadi")
    return {"ok": True}
