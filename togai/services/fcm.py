"""Firebase Cloud Messaging — push xabarlari yuborish.

FCM_CREDENTIALS_PATH .env'da bo'lsa to'liq ishlaydi. Bo'lmasa funksiyalar
shunchaki 0 qaytaradi (server crash bo'lmasin).

Ishlatish:
    from togai.services.fcm import send_to_user, broadcast
    send_to_user(user, "Salom", "Yangi reklama!", data={"deep_link": "/app"})
    broadcast("Yangilanish", "BioScan v2.0 chiqdi", segment="active_7d")
"""
from __future__ import annotations

import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

log = logging.getLogger(__name__)

_app = None  # firebase_admin app — lazy init


def _ensure_app():
    """Firebase'ni lazy yuklaymiz — paket o'rnatilmagan/kalit yo'q bo'lsa None."""
    global _app
    if _app is not None:
        return _app
    cred_path = getattr(settings, "FCM_CREDENTIALS_PATH", "")
    if not cred_path:
        return None
    try:
        import firebase_admin
        from firebase_admin import credentials
        cred = credentials.Certificate(cred_path)
        _app = firebase_admin.initialize_app(cred)
        return _app
    except Exception as e:
        log.warning("FCM init failed: %s", e)
        return None


def send_to_user(user, title: str, body: str, data: dict | None = None) -> int:
    """Bir foydalanuvchiga push. Yuborilgan token soni qaytadi."""
    if _ensure_app() is None:
        return 0
    token = (getattr(user, "fcm_token", "") or "").strip()
    if not token:
        return 0
    try:
        from firebase_admin import messaging
        msg = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items()},
            token=token,
        )
        messaging.send(msg)
        return 1
    except Exception as e:
        log.warning("FCM send_to_user failed: %s", e)
        return 0


def broadcast(title: str, body: str, data: dict | None = None,
              segment: str | None = None) -> int:
    """Hammaga yoki segmentga yuboradi.

    segment:
      - None: hammaga
      - "active_7d": oxirgi 7 kunda kirgan foydalanuvchilarga
    """
    if _ensure_app() is None:
        return 0
    from django.contrib.auth import get_user_model
    User = get_user_model()
    qs = User.objects.exclude(fcm_token="")
    if segment == "active_7d":
        cutoff = timezone.now() - timedelta(days=7)
        qs = qs.filter(last_login__gte=cutoff)
    tokens = list(qs.values_list("fcm_token", flat=True))
    if not tokens:
        return 0
    try:
        from firebase_admin import messaging
        sent = 0
        # FCM batch limit 500
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
        log.warning("FCM broadcast failed: %s", e)
        return 0
