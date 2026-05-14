"""Auth tests — Django'ning accounts/tests.py teng porta."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_signup_creates_user(client):
    r = await client.post("/api/auth/login/", json={
        "phone": "+998901234567", "password": "pass", "full_name": "Otabek",
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["new"] is True
    assert data["user"]["phone"] == "+998901234567"
    assert data["user"]["full_name"] == "Otabek"
    assert "access" in data and "refresh" in data


@pytest.mark.asyncio
async def test_login_existing_user(client):
    await client.post("/api/auth/login/", json={"phone": "+998901111111", "password": "pass"})
    r = await client.post("/api/auth/login/", json={"phone": "+998901111111", "password": "pass"})
    assert r.status_code == 200
    assert r.json()["new"] is False


@pytest.mark.asyncio
async def test_wrong_password(client):
    await client.post("/api/auth/login/", json={"phone": "+998902222222", "password": "pass"})
    r = await client.post("/api/auth/login/", json={"phone": "+998902222222", "password": "wrong"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_short_password_rejected(client):
    r = await client.post("/api/auth/login/", json={"phone": "+998903333333", "password": "p"})
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_me_endpoint_requires_auth(client):
    r = await client.get("/api/auth/me/")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_me_returns_user(client):
    auth = await client.post("/api/auth/login/", json={
        "phone": "+998904444444", "password": "pass",
    })
    token = auth.json()["access"]
    r = await client.get("/api/auth/me/", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["phone"] == "+998904444444"


@pytest.mark.asyncio
async def test_refresh_token(client):
    auth = await client.post("/api/auth/login/", json={
        "phone": "+998905555555", "password": "pass",
    })
    refresh = auth.json()["refresh"]
    r = await client.post("/api/auth/token/refresh/", json={"refresh": refresh})
    assert r.status_code == 200
    assert "access" in r.json()
