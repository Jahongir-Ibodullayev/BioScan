"""Crop advice — Django crops/services/advice.py async porta."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.redis import cache_get, cache_set
from app.models.crops import Crop, Region

from .ai import openrouter_chat
from .weather import average_soil_temp_next_days, get_30day_forecast


async def find_region(db: AsyncSession, lat: float, lon: float) -> Optional[Region]:
    rows = (await db.scalars(select(Region))).all()
    for r in rows:
        if r.contains(lat, lon):
            return r
    return None


def best_plant_date(crop: Crop, region: Optional[Region], forecast: Optional[dict]) -> date:
    today = date.today()
    avg_soil = average_soil_temp_next_days(forecast or {})

    if avg_soil is not None and avg_soil < crop.min_soil_temp_c:
        return today + timedelta(days=14)

    if region and crop.frost_sensitive:
        last_frost = date(today.year, 1, 1) + timedelta(days=region.avg_last_frost_doy - 1)
        if today < last_frost:
            return last_frost + timedelta(days=7)

    if crop.plant_window_start_month <= today.month <= crop.plant_window_end_month:
        return today + timedelta(days=3)

    if today.month < crop.plant_window_start_month:
        return date(today.year, crop.plant_window_start_month, 15)
    return date(today.year + 1, crop.plant_window_start_month, 15)


def watering_schedule(crop: Crop, irrigation: str) -> list[dict]:
    base = crop.water_freq_days
    if irrigation == "drip":
        return [
            {"week": 1, "frequency_days": base + 2, "liters_per_m2": 3},
            {"week": 4, "frequency_days": base, "liters_per_m2": 4},
            {"week": 8, "frequency_days": base, "liters_per_m2": 5},
            {"week": 12, "frequency_days": base + 1, "liters_per_m2": 4},
        ]
    if irrigation == "sprinkler":
        return [
            {"week": 1, "frequency_days": base, "liters_per_m2": 5},
            {"week": 4, "frequency_days": base - 1, "liters_per_m2": 6},
            {"week": 8, "frequency_days": base - 1, "liters_per_m2": 7},
        ]
    if irrigation == "manual":
        return [
            {"week": 1, "frequency_days": base, "liters_per_m2": 6},
            {"week": 4, "frequency_days": max(base - 2, 2), "liters_per_m2": 8},
            {"week": 8, "frequency_days": max(base - 2, 2), "liters_per_m2": 9},
        ]
    return [{"week": 1, "frequency_days": 0, "liters_per_m2": 0}]


async def _ai_explanation(crop: Crop, region: Optional[Region], irrigation: str,
                          experience: str, plant_date: date) -> str:
    region_slug = region.slug if region else "x"
    cache_key = f"crop-advice:ai:v2:{crop.slug}:{region_slug}:{irrigation}:{experience}"
    cached = await cache_get(cache_key)
    if cached:
        return cached
    region_name = region.name_uz if region else "aniqlanmagan hudud"
    prompt = (
        f"Foydalanuvchi {region_name} hududida {crop.name_uz} ({crop.name_lat}) ekmoqchi. "
        f"Sug'orish: {irrigation}. Tajriba: {experience}. "
        f"Eng yaxshi ekish sanasi: {plant_date}. "
        "3-4 jumlada o'zbek tilida qisqa, amaliy maslahat ber: "
        "tuproq tayyorlash, ekish chuqurligi va qancha suv kerak. "
        "Faqat 4 jumla, takrorlamasdan."
    )
    text = await openrouter_chat(
        prompt,
        system="Sen agrobiologsen — Markaziy Osiyo dehqonlari uchun amaliy maslahat berasen.",
        max_tokens=180,
        temperature=0.4,
    )
    if text and not text.startswith("Hozir javob bera olmadim"):
        await cache_set(cache_key, text, 60 * 60 * 24 * 7)
    return text


async def build_advice(
    db: AsyncSession,
    crop: Crop,
    lat: float,
    lon: float,
    irrigation: str,
    plot_size_m2: Optional[int] = None,
    experience: str = "beginner",
) -> dict:
    from datetime import datetime as _dt
    region = await find_region(db, lat, lon)
    region_slug = region.slug if region else "x"
    week_of_year = _dt.now().isocalendar()[1]
    cache_key = f"crop-advice:v2:{crop.slug}:{region_slug}:{irrigation}:{week_of_year}:{experience}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    forecast = await get_30day_forecast(lat, lon)
    plant_date = best_plant_date(crop, region, forecast)
    harvest_date = plant_date + timedelta(days=(crop.days_to_harvest_min + crop.days_to_harvest_max) // 2)

    schedule = watering_schedule(crop, irrigation)

    tips = []
    if crop.soil_prep_uz:
        tips.append(crop.soil_prep_uz[:200])
    if crop.planting_method_uz:
        tips.append(crop.planting_method_uz[:200])
    if crop.care_tips_uz:
        tips.append(crop.care_tips_uz[:200])

    warnings = []
    if crop.frost_sensitive:
        warnings.append("Bu ekin sovuqdan zaif — agroplenka tayyorlab qo'ying")
    if crop.common_pests:
        warnings.append(f"Asosiy zararkunandalar: {crop.common_pests[:120]}")

    recommended = ""
    if isinstance(crop.common_varieties, list) and crop.common_varieties:
        first = crop.common_varieties[0]
        if isinstance(first, dict):
            recommended = first.get("name", "")

    summary = (
        f"Sizning hudud ({region.name_uz if region else 'aniqlanmagan'}) uchun "
        f"{crop.name_uz} ekish — eng yaqin yaxshi sana: {plant_date.strftime('%d-%m-%Y')}. "
        f"Hosil ~{(harvest_date - plant_date).days} kunda."
    )

    ai_explanation = await _ai_explanation(crop, region, irrigation, experience, plant_date)

    result = {
        "crop": crop.name_uz,
        "region": region.name_uz if region else None,
        "summary_uz": summary,
        "best_plant_dates": [plant_date.isoformat()],
        "expected_harvest": harvest_date.isoformat(),
        "watering_schedule": schedule,
        "tips_uz": tips,
        "warnings_uz": warnings,
        "recommended_variety": recommended,
        "ai_explanation": ai_explanation,
    }
    await cache_set(cache_key, result, 60 * 60 * 24)
    return result
