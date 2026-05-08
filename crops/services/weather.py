"""Open-Meteo integratsiyasi — bepul, kalit kerak emas."""
from __future__ import annotations

import logging

import requests

log = logging.getLogger(__name__)

OPEN_METEO_FORECAST = "https://api.open-meteo.com/v1/forecast"


def get_30day_forecast(lat: float, lon: float) -> dict | None:
    """30 kunlik prognoz — kunlik harorat, yog'ingarchilik, tuproq harorati."""
    try:
        r = requests.get(
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
            timeout=10,
        )
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        log.warning("open-meteo failed: %s", e)
        return None


def average_soil_temp_next_days(forecast: dict, days: int = 7) -> float | None:
    """Keyingi N kunda o'rtacha tuproq harorati."""
    if not forecast or "daily" not in forecast:
        return None
    soil = forecast["daily"].get("soil_temperature_0_to_7cm_max", [])
    if not soil:
        return None
    series = [t for t in soil[:days] if t is not None]
    if not series:
        return None
    return sum(series) / len(series)
