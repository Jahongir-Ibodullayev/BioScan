"""Firebase Cloud Messaging — async wrapper sinxron firebase-admin atrofida.

firebase-admin'da async API yo'q, lekin biz uni threadpoolda chaqiramiz
(executor) — event loop bloklanmaydi.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import User

log = logging.getLogger(__name__)

_app = None


def _ensure_app():
    """Firebase'ni lazy yuklash. Yo'q bo'lsa None."""
    global _app
    if _app is not None:
        return _app
    cred_path = settings.FCM_CREDENTIALS_PATH
    if not cred_path or not os.path.exists(cred_path):
        return None
    try:
        import firebase_admin
        from firebase_admin import credentials
        cred = credentials.Certificate(cred_path)
        _app = firebase_admin.initialize_app(cred)
        return _app
    except Exception as e:
        log.warning("Firebase init failed: %s", e)
        return None


def _send_sync(token: str, title: str, body: str, data: Optional[dict] = None) -> bool:
    if _ensure_app() is None:
        return False
    try:
        from firebase_admin import messaging
        msg = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items()},
            token=token,
        )
        messaging.send(msg)
        return True
    except Exception as e:
        log.warning("FCM send failed: %s", e)
        return False


def _send_bulk_sync(tokens: list[str], title: str, body: str, data: Optional[dict] = None) -> int:
    if _ensure_app() is None or not tokens:
        return 0
    try:
        from firebase_admin import messaging
        sent = 0
        for i in range(0, len(tokens), 500):
            batch = tokens[i:i + 500]
            msg = messaging.MulticastMessage(
                notification=messaging.Notification(title=title, body=body),
                data={k: str(v) for k, v in (data or {}).items()},
                tokens=batch,
            )
            resp = messaging.send_each_for_multicast(msg)
            sent += resp.success_count
        return sent
    except Exception as e:
        log.warning("FCM bulk send failed: %s", e)
        return 0


async def send_to_user(user: User, title: str, body: str, data: Optional[dict] = None) -> int:
    token = (user.fcm_token or "").strip()
    if not token:
        return 0
    loop = asyncio.get_event_loop()
    ok = await loop.run_in_executor(None, _send_sync, token, title, body, data)
    return 1 if ok else 0


async def broadcast(db: AsyncSession, title: str, body: str,
                    data: Optional[dict] = None, segment: Optional[str] = None) -> int:
    """Hammaga yoki segmentga."""
    stmt = select(User.fcm_token).where(User.fcm_token != "")
    if segment == "active_7d":
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        stmt = stmt.where(User.last_login >= cutoff)
    tokens = [row for row in (await db.scalars(stmt)).all() if row]
    if not tokens:
        return 0
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _send_bulk_sync, tokens, title, body, data)
