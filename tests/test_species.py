"""Species tests."""
from __future__ import annotations

import pytest
from sqlalchemy import insert

from app.models.species import Species
from tests.conftest import _TestSession


async def _seed_species():
    async with _TestSession() as db:
        for slug, name, cat in [
            ("yantoq", "Yantoq", "giyoh"),
            ("archa", "Archa", "daraxt"),
            ("lola", "Lola", "gul"),
        ]:
            db.add(Species(slug=slug, name=name, category=cat))
        await db.commit()


@pytest.mark.asyncio
async def test_species_list(client):
    await _seed_species()
    r = await client.get("/api/species/")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 3


@pytest.mark.asyncio
async def test_species_filter_by_category(client):
    await _seed_species()
    r = await client.get("/api/species/?category=daraxt")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 1
    assert data["results"][0]["slug"] == "archa"


@pytest.mark.asyncio
async def test_species_detail(client):
    await _seed_species()
    r = await client.get("/api/species/lola/")
    assert r.status_code == 200
    assert r.json()["name"] == "Lola"


@pytest.mark.asyncio
async def test_species_not_found(client):
    r = await client.get("/api/species/yoq-tur/")
    assert r.status_code == 404
