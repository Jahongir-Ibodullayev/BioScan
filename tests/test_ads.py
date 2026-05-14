"""Ads tests."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.models.ads import Ad
from tests.conftest import _TestSession


async def _seed_ad():
    async with _TestSession() as db:
        ad = Ad(
            title="Test reklama",
            headline="Sotuv",
            body="Bu test",
            cta_text="Bos",
            target_url="https://example.com",
            slot="splash",
            platform="web",
            is_active=True,
            starts_at=datetime.now(timezone.utc) - timedelta(hours=1),
            priority=10,
        )
        db.add(ad)
        await db.commit()
        return ad.id


@pytest.mark.asyncio
async def test_active_ad_returns(client):
    await _seed_ad()
    r = await client.get("/api/ads/active/?slot=splash&platform=web")
    assert r.status_code == 200
    data = r.json()
    assert data["title"] == "Test reklama"


@pytest.mark.asyncio
async def test_active_ad_204_when_empty(client):
    r = await client.get("/api/ads/active/?slot=banner&platform=apk")
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_click_increments(client):
    ad_id = await _seed_ad()
    r = await client.post(f"/api/ads/{ad_id}/click/")
    assert r.status_code == 200
    assert r.json()["ok"] is True
