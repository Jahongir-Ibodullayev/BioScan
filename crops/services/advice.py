"""Crop advice — ekin uchun maslahat tuzish."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from .weather import average_soil_temp_next_days, get_30day_forecast


def find_region(lat: float, lon: float):
    """GPS → Region (bbox bo'yicha)."""
    from crops.models import Region
    for r in Region.objects.all():
        if r.contains(lat, lon):
            return r
    return None


def best_plant_date(crop, region, forecast) -> date:
    """Eng yaqin to'g'ri ekish sanasi."""
    today = date.today()
    avg_soil = average_soil_temp_next_days(forecast or {})

    # Birinchi qoida: tuproq harorati min'dan past — kutamiz
    if avg_soil is not None and avg_soil < crop.min_soil_temp_c:
        # Tuproq isigunga qadar har hafta tekshirsa bo'ladi — taxminan 14 kun keyin
        return today + timedelta(days=14)

    # Region oxirgi sovugiga qarab — sovuqdan keyin 1 hafta xavfsiz
    if region and crop.frost_sensitive:
        # Yil kuni → sana
        last_frost = date(today.year, 1, 1) + timedelta(days=region.avg_last_frost_doy - 1)
        if today < last_frost:
            return last_frost + timedelta(days=7)

    # Ekish davri ichidamiz?
    if crop.plant_window_start_month <= today.month <= crop.plant_window_end_month:
        return today + timedelta(days=3)  # 3 kun tayyorgarlik

    # Ekish davriga keling yilga keyin
    if today.month < crop.plant_window_start_month:
        return date(today.year, crop.plant_window_start_month, 15)
    return date(today.year + 1, crop.plant_window_start_month, 15)


def watering_schedule(crop, irrigation: str) -> list[dict]:
    """Sug'orish jadvali — 12 hafta uchun."""
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


def build_advice(crop, lat: float, lon: float, irrigation: str,
                 plot_size_m2: int | None = None,
                 experience: str = "beginner") -> dict:
    """Maslahat to'plamini yaratadi — AI'siz, tez."""
    region = find_region(lat, lon)
    forecast = get_30day_forecast(lat, lon)
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

    return {
        "crop": crop.name_uz,
        "region": region.name_uz if region else None,
        "summary_uz": summary,
        "best_plant_dates": [plant_date.isoformat()],
        "expected_harvest": harvest_date.isoformat(),
        "watering_schedule": schedule,
        "tips_uz": tips,
        "warnings_uz": warnings,
        "recommended_variety": recommended,
    }
