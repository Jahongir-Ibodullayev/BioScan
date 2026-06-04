"""Open-Meteo — async, kalit kerak emas.

Django'ning crops/services/weather.py async portasi.
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx

from app.db.redis import cache_get, cache_set

log = logging.getLogger(__name__)

OPEN_METEO_FORECAST = "https://api.open-meteo.com/v1/forecast"


async def get_30day_forecast(lat: float, lon: float) -> Optional[dict]:
    """30 kunlik prognoz — 6 soat cache."""
    grid_lat = round(lat * 2) / 2
    grid_lon = round(lon * 2) / 2
    cache_key = f"open-meteo:30d:{grid_lat}:{grid_lon}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            r = await client.get(
                OPEN_METEO_FORECAST,
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "daily": (
                        "temperature_2m_max,temperature_2m_min,"
                        "soil_temperature_0_to_7cm_max,soil_temperature_0_to_7cm_min,"
                        "precipitation_sum"
                    ),
                    "timezone": "Asia/Tashkent",
                    "forecast_days": 16,
                    "past_days": 7,
                },
            )
            r.raise_for_status()
            data = r.json()
        await cache_set(cache_key, data, 60 * 60 * 6)
        return data
    except httpx.HTTPError as e:
        log.warning("open-meteo failed: %s", e)
        return None


def average_soil_temp_next_days(forecast: Optional[dict], days: int = 7) -> Optional[float]:
    if not forecast or "daily" not in forecast:
        return None
    soil = forecast["daily"].get("soil_temperature_0_to_7cm_max", [])
    if not soil:
        return None
    series = [t for t in soil[:days] if t is not None]
    if not series:
        return None
    return sum(series) / len(series)
