"""Firebase Cloud Messaging integration.

Saves user's FCM token + sends push notifications.

Setup steps:
1. Create Firebase project at console.firebase.google.com
2. Add Android app, download google-services.json (for Flutter)
3. Service account → Generate private key → save as
   /var/www/togai-backend/firebase-service-account.json
4. .env: FIREBASE_SERVICE_ACCOUNT=/var/www/togai-backend/firebase-service-account.json
5. pip install firebase-admin

If service account is not configured, push silently no-ops (logged warning).
"""
import logging
import os

from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

log = logging.getLogger(__name__)
User = get_user_model()

_fb_initialized = False


def _ensure_firebase():
    """Initialize Firebase Admin SDK once. Returns True if available."""
    global _fb_initialized
    if _fb_initialized:
        return True
    sa_path = getattr(settings, "FIREBASE_SERVICE_ACCOUNT", "")
    if not sa_path or not os.path.exists(sa_path):
        return False
    try:
        import firebase_admin
        from firebase_admin import credentials
        if not firebase_admin._apps:
            cred = credentials.Certificate(sa_path)
            firebase_admin.initialize_app(cred)
        _fb_initialized = True
        return True
    except Exception as e:
        log.warning("Firebase init failed: %s", e)
        return False


def send_push(user_or_token, title: str, body: str, data: dict | None = None) -> bool:
    """Send a push notification to a user (by User instance) or a raw FCM token.

    Returns True on success.
    """
    if not _ensure_firebase():
        log.info("[push stub] %s → %s · %s", user_or_token, title, body)
        return False

    from firebase_admin import messaging

    if isinstance(user_or_token, User):
        token = user_or_token.fcm_token
    else:
        token = str(user_or_token)
    if not token:
        return False

    try:
        msg = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items()},
            token=token,
        )
        msg_id = messaging.send(msg)
        log.info("✓ FCM push sent id=%s to ...%s", msg_id, token[-12:])
        return True
    except Exception as e:
        log.warning("FCM send failed: %s", e)
        return False


def send_push_bulk(tokens: list[str], title: str, body: str,
                   data: dict | None = None) -> int:
    """Send to multiple tokens. Returns success count."""
    if not _ensure_firebase() or not tokens:
        return 0
    from firebase_admin import messaging
    msg = messaging.MulticastMessage(
        notification=messaging.Notification(title=title, body=body),
        data={k: str(v) for k, v in (data or {}).items()},
        tokens=tokens[:500],  # FCM hard limit
    )
    try:
        resp = messaging.send_each_for_multicast(msg)
        return resp.success_count
    except Exception as e:
        log.warning("FCM bulk send failed: %s", e)
        return 0


# ============================================================================
# REST endpoints
# ============================================================================

@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def register_fcm_token(request):
    """POST /api/auth/fcm/register/ — save user's FCM token.

    Body: {"token": "...", "platform": "android"|"ios"|"web"}
    """
    token = (request.data.get("token") or "").strip()
    platform = (request.data.get("platform") or "android").strip().lower()
    if not token:
        return Response({"detail": "token required"},
                        status=status.HTTP_400_BAD_REQUEST)
    if platform not in ("android", "ios", "web"):
        platform = "android"

    user = request.user
    user.fcm_token = token
    user.fcm_platform = platform
    user.save(update_fields=["fcm_token", "fcm_platform"])
    return Response({"ok": True, "platform": platform})


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def unregister_fcm_token(request):
    """POST /api/auth/fcm/unregister/ — clear FCM token (on logout)."""
    user = request.user
    user.fcm_token = ""
    user.fcm_platform = ""
    user.save(update_fields=["fcm_token", "fcm_platform"])
    return Response({"ok": True})
