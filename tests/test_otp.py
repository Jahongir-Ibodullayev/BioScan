"""OTP + FCM tests."""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.user import OTPCode, User
from tests.conftest import _TestSession


@pytest.mark.asyncio
async def test_otp_request_console_succeeds(client, monkeypatch):
    """Console rejimida SMS yuborilgan deb hisoblanadi (DEBUG=true)."""
    r = await client.post("/api/auth/otp/request/", json={"phone": "+998901112222"})
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["ok"] is True
    # DEBUG=true bo'lganda dev_code qaytadi
    assert "dev_code" in data
    # OTP DB'da bo'lishi kerak
    async with _TestSession() as db:
        otp = await db.scalar(select(OTPCode).where(OTPCode.phone == "+998901112222"))
        assert otp is not None
        assert len(otp.code) == 6


@pytest.mark.asyncio
async def test_otp_verify_creates_user(client):
    r = await client.post("/api/auth/otp/request/", json={"phone": "+998901113333"})
    code = r.json()["dev_code"]
    r = await client.post("/api/auth/otp/verify/", json={
        "phone": "+998901113333", "code": code, "full_name": "Sardor",
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["new"] is True
    assert data["user"]["full_name"] == "Sardor"
    assert "access" in data


@pytest.mark.asyncio
async def test_otp_verify_wrong_code(client):
    await client.post("/api/auth/otp/request/", json={"phone": "+998901114444"})
    r = await client.post("/api/auth/otp/verify/", json={
        "phone": "+998901114444", "code": "000000",
    })
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_tg_otp_409_when_no_telegram(client):
    r = await client.post("/api/auth/tg-otp/request/", json={"phone": "+998901115555"})
    # User yo'q — 409
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_fcm_register_requires_auth(client):
    r = await client.post("/api/auth/fcm/register/", json={"token": "abc", "platform": "android"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_fcm_register_updates_user(client):
    auth = await client.post("/api/auth/login/", json={
        "phone": "+998901116666", "password": "pass",
    })
    token = auth.json()["access"]
    r = await client.post(
        "/api/auth/fcm/register/",
        json={"token": "fcm-test-token-12345", "platform": "ios"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["platform"] == "ios"

    async with _TestSession() as db:
        u = await db.scalar(select(User).where(User.phone == "+998901116666"))
        assert u.fcm_token == "fcm-test-token-12345"
        assert u.fcm_platform == "ios"


@pytest.mark.asyncio
async def test_fcm_unregister_clears(client):
    auth = await client.post("/api/auth/login/", json={
        "phone": "+998901117777", "password": "pass",
    })
    token = auth.json()["access"]
    await client.post(
        "/api/auth/fcm/register/",
        json={"token": "test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    r = await client.post(
        "/api/auth/fcm/unregister/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    async with _TestSession() as db:
        u = await db.scalar(select(User).where(User.phone == "+998901117777"))
        assert u.fcm_token == ""
