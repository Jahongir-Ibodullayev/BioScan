"""Lightweight Telegram webhook for OTP linking.

This bypasses python-telegram-bot polling entirely — Telegram pushes
updates to this endpoint, we parse them and:
- on /start or /login → reply with phone-share keyboard
- on contact share → save User.telegram_id ↔ phone

No conflict with other polling instances of the same bot — only ONE
webhook URL receives updates at a time (`setWebhook` overrides any
prior setting).
"""
import json
import logging
import re

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

log = logging.getLogger(__name__)
User = get_user_model()


def _bot_token() -> str | None:
    return (
        getattr(settings, "TELEGRAM_OTP_BOT_TOKEN", None)
        or getattr(settings, "TELEGRAM_BOT_TOKEN", None)
    )


def _api(method: str, **payload) -> dict:
    """Call Telegram Bot API."""
    token = _bot_token()
    if not token:
        return {}
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/{method}",
            json=payload,
            timeout=8,
        )
        return r.json()
    except Exception as e:
        log.exception("telegram api %s failed: %s", method, e)
        return {}


def _normalize_phone(raw: str) -> str:
    if not raw:
        return ""
    digits = re.sub(r"\D", "", raw)
    if not digits.startswith("998") and len(digits) in (9, 12):
        digits = "998" + digits[-9:]
    return f"+{digits}" if digits else ""


@csrf_exempt
@require_POST
def telegram_webhook(request):
    """Receive Telegram updates pushed to this URL.

    POST /api/bot/webhook/<secret>/
    Body: full Update JSON.
    """
    try:
        update = json.loads(request.body.decode("utf-8") or "{}")
    except Exception:
        return JsonResponse({"ok": False, "detail": "bad json"}, status=400)

    msg = update.get("message") or update.get("edited_message") or {}
    chat = msg.get("chat") or {}
    chat_id = chat.get("id")
    from_user = msg.get("from") or {}
    text = (msg.get("text") or "").strip()
    contact = msg.get("contact")

    if not chat_id:
        return HttpResponse("ok")

    # /start or /login → ask for phone
    if text.startswith("/start") or text.startswith("/login") or text.startswith("/help"):
        _api(
            "sendMessage",
            chat_id=chat_id,
            text=(
                "🔐 <b>Tog'AI hisobiga ulanish</b>\n\n"
                "Pastdagi tugmani bosib, telefon raqamingizni ulashing. "
                "Keyin webapp yoki APK'da shu raqam bilan kirayotganda, "
                "tasdiqlash kodi shu yerga keladi."
            ),
            parse_mode="HTML",
            reply_markup={
                "keyboard": [[{
                    "text": "📱 Raqamni ulashish",
                    "request_contact": True,
                }]],
                "resize_keyboard": True,
                "one_time_keyboard": True,
            },
        )
        return HttpResponse("ok")

    # Contact share — save phone ↔ telegram_id link
    if contact:
        phone = _normalize_phone(contact.get("phone_number", ""))
        if not phone:
            _api("sendMessage", chat_id=chat_id,
                 text="❌ Raqam noto'g'ri formatda.")
            return HttpResponse("ok")

        # Only allow user to share their OWN phone
        contact_uid = contact.get("user_id")
        from_uid = from_user.get("id")
        if contact_uid and from_uid and contact_uid != from_uid:
            _api("sendMessage", chat_id=chat_id,
                 text="⚠️ Faqat o'z raqamingizni ulashing.")
            return HttpResponse("ok")

        try:
            tg_id = from_uid
            tg_username = from_user.get("username", "")
            full_name = (
                f"{from_user.get('first_name','')} "
                f"{from_user.get('last_name','')}"
            ).strip()

            # Detach this telegram_id from any other phone
            User.objects.filter(telegram_id=tg_id).exclude(phone=phone).update(
                telegram_id=None, telegram_username="",
            )
            user, created = User.objects.get_or_create(
                phone=phone,
                defaults={
                    "full_name": full_name or "",
                    "telegram_id": tg_id,
                    "telegram_username": tg_username,
                },
            )
            if not created:
                changed = False
                if user.telegram_id != tg_id:
                    user.telegram_id = tg_id
                    changed = True
                if user.telegram_username != tg_username:
                    user.telegram_username = tg_username
                    changed = True
                if changed:
                    user.save(update_fields=["telegram_id", "telegram_username"])

            _api(
                "sendMessage",
                chat_id=chat_id,
                text=(
                    f"✅ <b>Raqam ulandi!</b>\n\n"
                    f"📱 {phone}\n"
                    f"{'Yangi hisob yaratildi.' if created else 'Mavjud hisobga ulandi.'}\n\n"
                    f"Endi webapp yoki APK'ga kirayotganda, "
                    f"6-xonali kod shu yerga keladi."
                ),
                parse_mode="HTML",
                reply_markup={"remove_keyboard": True},
            )
        except Exception as e:
            log.exception("link failed: %s", e)
            _api("sendMessage", chat_id=chat_id,
                 text="❌ Ulashda xato. Qayta urinib ko'ring.")
        return HttpResponse("ok")

    # Unknown message — guide user
    _api(
        "sendMessage",
        chat_id=chat_id,
        text="🔐 /start bosib, telefon raqamingizni ulashing.",
    )
    return HttpResponse("ok")
