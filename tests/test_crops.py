"""Crops tests — Open-Meteo va AI'ni stub qilamiz."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.models.crops import Crop, Region
from app.services import advice as advice_svc
from app.services import weather as weather_svc
from tests.conftest import _TestSession


@pytest.fixture(autouse=True)
def _stub_external(monkeypatch):
    async def _fake_forecast(lat, lon):
        return {"daily": {"soil_temperature_0_to_7cm_max": [20, 21, 22, 21, 20, 19, 22]}}
    async def _fake_ai(*a, **kw): return "Test AI maslahat"
    monkeypatch.setattr(weather_svc, "get_30day_forecast", _fake_forecast)
    monkeypatch.setattr(advice_svc, "get_30day_forecast", _fake_forecast)
    monkeypatch.setattr(advice_svc, "openrouter_chat", _fake_ai)


async def _seed_crop_region():
    async with _TestSession() as db:
        db.add(Region(
            slug="tashkent", name_uz="Toshkent",
            lat_min=Decimal("40.5"), lat_max=Decimal("41.7"),
            lon_min=Decimal("68.5"), lon_max=Decimal("70.0"),
            avg_last_frost_doy=80, avg_first_frost_doy=290,
        ))
        db.add(Crop(
            slug="pomidor", name_uz="Pomidor", name_lat="Solanum lycopersicum",
            category="sabzavot", icon_name="leaf",
            min_soil_temp_c=10, optimal_soil_temp_c=20,
            frost_sensitive=True,
            plant_window_start_month=4, plant_window_end_month=6,
            days_to_harvest_min=80, days_to_harvest_max=100,
            water_freq_days=3,
        ))
        await db.commit()


@pytest.mark.asyncio
async def test_crops_list(client):
    await _seed_crop_region()
    r = await client.get("/api/crops/list/")
    assert r.status_code == 200
    assert len(r.json()["results"]) == 1


@pytest.mark.asyncio
async def test_crops_advice(client):
    await _seed_crop_region()
    r = await client.get("/api/crops/advice/?crop_slug=pomidor&lat=41.3&lon=69.2&irrigation=drip")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["crop"] == "Pomidor"
    assert "best_plant_dates" in data
    assert len(data["watering_schedule"]) >= 1


@pytest.mark.asyncio
async def test_crops_advice_404(client):
    r = await client.get("/api/crops/advice/?crop_slug=yoq-ekin&lat=41&lon=69")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_crops_plan_crud(client):
    await _seed_crop_region()
    auth = await client.post("/api/auth/login/", json={"phone": "+998901234567", "password": "pass"})
    token = auth.json()["access"]
    h = {"Authorization": f"Bearer {token}"}

    # Plan yaratish
    async with _TestSession() as db:
        from sqlalchemy import select
        crop = await db.scalar(select(Crop).where(Crop.slug == "pomidor"))
        crop_id = crop.id
    r = await client.post(
        "/api/crops/plans/",
        json={
            "crop_id": crop_id, "lat": 41.3, "lon": 69.2,
            "irrigation": "manual", "planned_plant_date": "2026-05-15",
        },
        headers=h,
    )
    assert r.status_code == 201

    r = await client.get("/api/crops/plans/", headers=h)
    assert r.json()["results"][0]["irrigation"] == "manual"
