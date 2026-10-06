"""Map + Saved species tests."""
from __future__ import annotations

import pytest

from app.models.mapdata import MapMarker
from app.models.species import Species
from tests.conftest import _TestSession


async def _seed():
    async with _TestSession() as db:
        db.add(MapMarker(type="plant", label="Archa", latitude=41.5, longitude=70.0))
        db.add(MapMarker(type="danger", label="Gyurza", latitude=39.8, longitude=66.1))
        db.add(Species(slug="archa", name="Archa", category="daraxt"))
        await db.commit()


@pytest.mark.asyncio
async def test_map_markers(client):
    await _seed()
    r = await client.get("/api/map/markers/")
    assert r.status_code == 200
    assert len(r.json()["results"]) == 2


@pytest.mark.asyncio
async def test_map_markers_filter_type(client):
    await _seed()
    r = await client.get("/api/map/markers/?type=danger")
    assert len(r.json()["results"]) == 1


@pytest.mark.asyncio
async def test_saved_requires_auth(client):
    r = await client.get("/api/saved/")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_saved_crud(client):
    await _seed()
    auth = await client.post("/api/auth/login/", json={"phone": "+998900012345", "password": "pass"})
    token = auth.json()["access"]
    h = {"Authorization": f"Bearer {token}"}

    r = await client.post("/api/saved/", json={"species_slug": "archa", "note": "ko'rdim"}, headers=h)
    assert r.status_code == 201, r.text

    r = await client.get("/api/saved/", headers=h)
    assert len(r.json()["results"]) == 1
    # Yangi shape: species (id) + species_detail (nested)
    item = r.json()["results"][0]
    assert isinstance(item["species"], int)
    assert item["species_detail"]["slug"] == "archa"

    # Idempotency — ikkinchi marta yana qo'shsa OK
    r = await client.post("/api/saved/", json={"species_slug": "archa"}, headers=h)
    assert r.status_code == 201 and r.json().get("already") is True

    # Delete
    r = await client.delete("/api/saved/archa/", headers=h)
    assert r.status_code == 200

    r = await client.get("/api/saved/", headers=h)
    assert len(r.json()["results"]) == 0
