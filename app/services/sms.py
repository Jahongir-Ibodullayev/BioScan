"""SMS yuborish — Eskiz provider (yoki console dev rejimi)."""
from __future__ import annotations

import logging

import httpx

from app.core.config import settings

log = logging.getLogger(__name__)


async def send_sms(phone: str, text: str) -> bool:
    """Foydalanuvchiga SMS yuborish. True = OK."""
    provider = getattr(settings, "SMS_PROVIDER", "console")

    if provider == "console":
        log.info("SMS [dev] → %s: %s", phone, text)
        return True

    if provider == "eskiz":
        email = getattr(settings, "SMS_ESKIZ_EMAIL", "")
        password = getattr(settings, "SMS_ESKIZ_PASSWORD", "")
        if not email or not password:
            log.warning("Eskiz credentials yo'q")
            return False
        try:
            async with httpx.AsyncClient(timeout=10.0) as c:
                auth = (await c.post(
                    "https://notify.eskiz.uz/api/auth/login",
                    data={"email": email, "password": password},
                )).json()
                token = (auth.get("data") or {}).get("token")
                if not token:
                    log.warning("Eskiz auth failed: %s", auth)
                    return False
                r = await c.post(
                    "https://notify.eskiz.uz/api/message/sms/send",
                    headers={"Authorization": f"Bearer {token}"},
                    data={
                        "mobile_phone": phone.lstrip("+"),
                        "message": text,
                        "from": "4546",
                    },
                )
                return r.status_code == 200
        except httpx.HTTPError as e:
            log.warning("Eskiz SMS error: %s", e)
            return False

    log.warning("Unknown SMS provider: %s", provider)
    return False
