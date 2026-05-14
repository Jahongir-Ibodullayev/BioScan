"""Telegram bot integratsiyasi — OTP yuborish."""
from __future__ import annotations

import logging

import httpx

from app.core.config import settings

log = logging.getLogger(__name__)


async def send_otp_via_telegram(telegram_id: int, code: str) -> bool:
    """Foydalanuvchining Telegram chat'iga OTP kodini yuboradi."""
    token = settings.TELEGRAM_OTP_BOT_TOKEN or settings.TELEGRAM_BOT_TOKEN
    if not token:
        log.warning("Telegram bot token yo'q — OTP yuborib bo'lmadi")
        return False
    if not telegram_id:
        return False

    text = (
        f"🔐 <b>BioScan tasdiqlash kodi</b>\n\n"
        f"<code>{code}</code>\n\n"
        f"Kod 2 daqiqa amal qiladi. Kodni hech kimga bermang."
    )
    try:
        async with httpx.AsyncClient(timeout=8.0) as c:
            r = await c.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={
                    "chat_id": int(telegram_id),
                    "text": text,
                    "parse_mode": "HTML",
                },
            )
            return r.status_code == 200
    except httpx.HTTPError as e:
        log.warning("Telegram OTP send failed: %s", e)
        return False


async def send_message(telegram_id: int, text: str, parse_mode: str = "HTML") -> bool:
    """Umumiy maqsadli — botdan foydalanuvchiga xabar."""
    token = settings.TELEGRAM_BOT_TOKEN
    if not token or not telegram_id:
        return False
    try:
        async with httpx.AsyncClient(timeout=8.0) as c:
            r = await c.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": int(telegram_id), "text": text, "parse_mode": parse_mode},
            )
            return r.status_code == 200
    except httpx.HTTPError as e:
        log.warning("Telegram send failed: %s", e)
        return False
