"""Health + root."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/api/health/")
    assert r.status_code == 200
    assert r.json()["ok"] is True


@pytest.mark.asyncio
async def test_root(client):
    r = await client.get("/")
    assert r.status_code == 200
    assert "BioScan" in r.json()["service"]


@pytest.mark.asyncio
async def test_openapi(client):
    r = await client.get("/api/openapi.json")
    assert r.status_code == 200
    assert "paths" in r.json()
