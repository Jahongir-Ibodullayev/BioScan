"""Celery vazifalari — async wrapper, alohida event loop'da."""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path

from celery import shared_task

log = logging.getLogger(__name__)


@shared_task
def warm_species_cache() -> dict:
    """Top 50 turlarni cache'ga olib qo'yadi (5 daqiqada bir)."""
    import json

    from sqlalchemy import select

    from app.db.redis import get_redis
    from app.db.session import AsyncSessionLocal
    from app.models.species import Species

    async def _run():
        async with AsyncSessionLocal() as db:
            rows = (await db.scalars(select(Species).order_by(Species.name).limit(50))).all()
            payload = [
                {"id": r.id, "slug": r.slug, "name": r.name, "latin": r.latin}
                for r in rows
            ]
        r = get_redis()
        await r.set("bioscan:hot:species:top50", json.dumps(payload), ex=600)
        return len(payload)

    n = asyncio.run(_run())
    log.info("warmed: %s species", n)
    return {"warmed": n}


@shared_task
def send_weekly_tip() -> int:
    """Juma 18:00 — barcha foydalanuvchilarga maslahat."""
    log.info("weekly_tip kerakli FCM credentials yo'q bo'lsa skip")
    return 0


@shared_task(bind=True, max_retries=2)
def build_yearbook_pdf(self, user_id: int, year: int) -> dict:
    """Yillik PDF kitobni Celery worker'da render qiladi (sync blocker).

    Natija: media/yearbook/<user_id>_<year>.pdf — fayl yo'li qaytadi.
    """
    from sqlalchemy import select

    from app.db.session import AsyncSessionLocal
    from app.models.observation import Observation
    from app.models.species import Species
    from app.models.user import User
    from app.services.yearbook import _render_pdf

    async def _gather():
        async with AsyncSessionLocal() as db:
            u = await db.scalar(select(User).where(User.id == user_id))
            if not u:
                return None, []
            start = datetime(year, 1, 1)
            end = datetime(year + 1, 1, 1)
            obs_rows = (await db.scalars(
                select(Observation)
                .where(Observation.user_id == user_id,
                       Observation.created_at >= start,
                       Observation.created_at < end)
                .order_by(Observation.created_at)
            )).all()
            sp_ids = {o.species_id for o in obs_rows if o.species_id}
            sp_map = {}
            if sp_ids:
                sp_rows = (await db.scalars(select(Species).where(Species.id.in_(sp_ids)))).all()
                sp_map = {s.id: s for s in sp_rows}
            user_name = u.full_name or u.phone
        return user_name, [
            {
                "species_id": o.species_id,
                "species_name": (sp_map.get(o.species_id) and sp_map[o.species_id].name),
                "species_latin": (sp_map.get(o.species_id) and sp_map[o.species_id].latin),
                "species_category": (sp_map.get(o.species_id) and sp_map[o.species_id].category),
                "species_redbook": bool(sp_map.get(o.species_id) and sp_map[o.species_id].red_book),
                "species_picture": (sp_map.get(o.species_id) and sp_map[o.species_id].picture),
                "ai_confidence": o.ai_confidence,
                "note": o.note,
                "latitude": o.latitude,
                "longitude": o.longitude,
                "created_at": o.created_at.isoformat() if o.created_at else None,
            }
            for o in obs_rows
        ]

    try:
        user_name, payload = asyncio.run(_gather())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=10) from exc

    if user_name is None:
        return {"status": "error", "reason": "user_not_found"}

    pdf_bytes = _render_pdf(user_name, year, payload)
    out_dir = Path(os.environ.get("MEDIA_ROOT", "media")) / "yearbook"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{user_id}_{year}.pdf"
    out.write_bytes(pdf_bytes)
    return {
        "status": "ok",
        "user_id": user_id,
        "year": year,
        "path": str(out),
        "size_bytes": len(pdf_bytes),
        "observations": len(payload),
    }
