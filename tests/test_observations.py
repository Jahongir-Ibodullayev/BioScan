"""Observations + scan + yearbook tests."""
from __future__ import annotations

import io

import pytest

from app.models.observation import Observation
from app.models.species import Species
from app.services import ai as ai_svc
from tests.conftest import _TestSession


@pytest.fixture(autouse=True)
def _stub_vision(monkeypatch):
    async def _fake(*a, **kw):
        return {
            "found": True, "name": "Yantoq", "latin": "Alhagi pseudalhagi",
            "category": "giyoh", "summary": "Test yantoq", "confidence": 0.9,
        }
    monkeypatch.setattr(ai_svc, "identify_species_from_image", _fake)
    from app.api import observations as obs_mod
    monkeypatch.setattr(obs_mod, "identify_species_from_image", _fake)


@pytest.mark.asyncio
async def test_scan_anonymous_creates_species(client):
    files = {"photo": ("test.jpg", io.BytesIO(b"fake-image-bytes"), "image/jpeg")}
    r = await client.post("/api/observations/scan/", files=files)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["identified"] is True
    assert data["species"]["name"] == "Yantoq"
    assert data["observation_id"] is None  # Anonim


@pytest.mark.asyncio
async def test_scan_authenticated_creates_observation(client):
    auth = await client.post("/api/auth/login/", json={"phone": "+998901100110", "password": "pass"})
    token = auth.json()["access"]
    files = {"photo": ("test.jpg", io.BytesIO(b"fake-bytes"), "image/jpeg")}
    r = await client.post(
        "/api/observations/scan/",
        files=files,
        data={"lat": "41.3", "lng": "69.2"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["observation_id"] is not None


@pytest.mark.asyncio
async def test_public_feed_filters_bbox(client):
    async with _TestSession() as db:
        sp = Species(slug="lola", name="Lola", category="gul")
        db.add(sp)
        await db.flush()
        # Login bilan user kerak (foreign key)
        from app.models.user import User
        u = User(phone="+998900011110", password="x", is_active=True)
        db.add(u)
        await db.flush()
        db.add(Observation(user_id=u.id, species_id=sp.id, latitude=41.0, longitude=69.0))
        db.add(Observation(user_id=u.id, species_id=sp.id, latitude=39.0, longitude=66.0))
        await db.commit()

    r = await client.get("/api/observations/public/?bbox=40,68,42,70")
    assert r.status_code == 200
    assert r.json()["count"] == 1
