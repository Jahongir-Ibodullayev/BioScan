"""External services (stubs — qulay prod-ready skeleton).

Har bir servis kaliti yo'q bo'lsa — mock ishlatadi, bo'lsa — real API.
"""
from __future__ import annotations

import base64
import io
import json
import logging

import requests
from django.conf import settings
from PIL import Image

log = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Universal AI client (OpenRouter > Groq fallback)
# ------------------------------------------------------------------
# OpenRouter Groq bilan to'la mos OpenAI formatida ishlaydi.
# Agar OPENROUTER_API_KEY mavjud bo'lsa — OpenRouter, bo'lmasa — Groq.

def ai_provider() -> tuple[str, str, dict]:
    """Returns (base_url, api_key, extra_headers) — OpenRouter > Groq."""
    or_key = getattr(settings, "OPENROUTER_API_KEY", "")
    if or_key:
        return (
            "https://openrouter.ai/api/v1",
            or_key,
            {
                "HTTP-Referer": getattr(settings, "OPENROUTER_REFERER", "https://togai.uz"),
                "X-Title": getattr(settings, "OPENROUTER_TITLE", "Tog'AI"),
            },
        )
    return ("https://api.groq.com/openai/v1", getattr(settings, "GROQ_API_KEY", ""), {})


def ai_has_key() -> bool:
    return bool(getattr(settings, "OPENROUTER_API_KEY", "") or getattr(settings, "GROQ_API_KEY", ""))


# Model ro'yxati — provider-dependent. OpenRouter'da provider/model formatda.
def vision_models() -> list[str]:
    """Vision-capable models — verified to work with current OpenRouter key.

    Ordered cheap → expensive. First successful response wins.
    """
    if getattr(settings, "OPENROUTER_API_KEY", ""):
        # Faqat ishonchli ishlovchi modellar — 404 bo'layotganlar olib tashlandi.
        # Birinchi muvaffaqiyatli javob g'oliblik qiladi → AI sekinligi minimal.
        return [
            # Cheap & accurate, vision-capable — Azure-backed, ishonchli
            "openai/gpt-4o-mini",
            # Google Gemini Flash 1.5 — vision, fast, cheap
            "google/gemini-flash-1.5",
            # Mistral Pixtral 12B — vision, fast
            "mistralai/pixtral-12b",
        ]
    # Groq fallback
    return [
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "meta-llama/llama-4-maverick-17b-128e-instruct",
        "llama-3.2-90b-vision-preview",
        "llama-3.2-11b-vision-preview",
    ]


def chat_model() -> str:
    if getattr(settings, "OPENROUTER_API_KEY", ""):
        return "meta-llama/llama-3.3-70b-instruct"
    return "llama-3.3-70b-versatile"


def _compress_image(image_bytes: bytes, max_dim: int = 1024, quality: int = 82) -> bytes:
    """Rasmni Groq uchun kichraytirish: JPEG, max 1024×1024, ~150-300KB."""
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()


# ------------------------------------------------------------------
# Groq Vision — rasmdan tur aniqlash + to'liq ma'lumot
# ------------------------------------------------------------------
GROQ_VISION_PROMPT = """Siz Markaziy Osiyo flora/faunasi bo'yicha ekspert biologsiz.

=== AVVAL — RASMDAGI NIMANI ANIQLA ===
Bu rasm quyidagilardan qaysi biri?
  (A) Tirik organizm: o'simlik, hayvon, qush, hasharot, qo'ziqorin, baliq, ilon
  (B) BIOLOGIK BO'LMAGAN: hujjat, matn, ekran skrinshot, telefon, kompyuter,
      mashina, bino, mebel, kiyim, tayyor ovqat, odam yuzi, logo, illustratsiya
  (C) Sifatsiz/qorong'i/buzilgan rasm

(B) yoki (C) bo'lsa — XATO! Hech qanday tur nomi BERMA. Quyidagini qaytar:
  {"found": false, "reason": "Rasmda biologik tur topilmadi"}
yoki
  {"found": false, "reason": "Hujjat/matn rasmi — biologik tur emas"}
yoki
  {"found": false, "reason": "Rasm sifati past — qaytadan urinib ko'ring"}

ISHONCHSIZ BO'LSA HAM (confidence < 0.40) — found=false qaytar.
TAXMIN QILMA. ISHONMASANG — TAN OL!

=== #1 QOIDA — HAMMA MATN O'ZBEK TILIDA! ===

JSON dagi HAR BIR matn maydoni (name, summary, description, habitat, uses,
warnings, first_aid, regions, key_features, alternatives.name, alternatives.why)
— FAQAT O'ZBEK TILIDA yoziladi. Ingliz, rus, fors so'zlar MUTLAQO man etiladi.

Agar turning o'zbek nomi yo'q bo'lsa:
  • Lotin nomidan translitatsiya qiling ("Aloe vera" → "Aloe")
  • Yoki "Noma'lum tur" deb yozing
  • lekin HECH QACHON Ingliz nomini yozmang

Qo'llanishi mumkin bo'lgan so'zlar: o'simlik, daraxt, gul, hayvon, qush, ilon,
hasharot, qo'ziqorin, tikan, barg, gul, meva, poya, tik, keng, ingichka,
oq, qora, qizil, yashil, sariq, pushti, zaharli, dorivor, foydali, Markaziy
Osiyo, O'zbekiston, Toshkent, Chimgan, cho'l, dasht, tog', o'rmon.

lotincha nom (latin) — faqat latin maydonida, u ham ilmiy format:
  Genus species (masalan "Alhagi pseudalhagi")

=== QOIDA #2 — BEPUL TAXMIN QILMA! ===

1. Avval rasmdagi XUSUSIYATLARNI o'zbek tilida sanab bering
   (barg shakli, gul rangi, meva, tikan, o'lchami)

2. KEYIN xususiyatlarga mos keladigan turni tanlang.

3. Agar rasm PAST sifatli yoki noaniq bo'lsa:
   - Confidence PAST (0.4-0.7)
   - alternatives'da 2-3 muqobil bering

4. confidence = 0.9+ faqat xususiyatlar TO'LIQ mos kelganda!

=== MUHIM FARQLAR (o'xshash o'simliklar) ===

ISIRIQ (Peganum harmala):
  - Ingichka, ikki qayta patsimon barg
  - OQ 5-bargli gul, sariq chang markazda
  - Dumaloq yashil-sariq meva
  - Bo'yi 20-70cm, tikansiz
  - Tutatish/hazorasfand uchun mashhur

SHUVOQ (Artemisia):
  - Kulrang-yashil PAXTASIMON barg (isiriq emas!)
  - Achchiq hid, kichik sariq gullar gajakda
  - ARALASHTIRMA isiriq bilan!

SALSOLA (saltwort):
  - Suvchil cho'l o'simligi, BARGSIZ bo'g'imli poya

YANTOQ (Alhagi pseudalhagi):
  - TIKANLI buta, PUSHTI-QIZIL gul
  - Dukkakdoshlar oilasi, kichkina yashil barg

NA'MATAK (Rosa canina):
  - Tikanli buta, QIZIL MEVA (juda aniq belgi)

ARCHA (Juniperus):
  - IGNABARG daraxt, KO'K MEVA
  - Hech qanday keng barg yo'q

SAKSOVUL (Haloxylon):
  - Tikansiz shoxli cho'l daraxti, bo'g'imli

YALPIZ (Mentha):
  - Tuxumsimon tishli barg, xushbo'y hid

SEDANA (Nigella):
  - KO'K/OQ chiroyli gul, ingichka baraglar, qora urug'

=== FORMAT — faqat JSON, BARCHA MATN O'ZBEK TILIDA ===

{
  "found": true/false,
  "key_features": "Rasmda ko'rgan narsalarni sanab o'ting (nima ko'rdingiz?)",
  "name": "O'zbekcha nomi",
  "latin": "Lotincha ilmiy nomi",
  "category": "giyoh | daraxt | gul | jonivor | hasharot | qush | qoziqorin",
  "confidence": 0.0-1.0,
  "alternatives": [
    {"name": "O'zbekcha nom 2", "latin": "Latin 2", "confidence": 0.0-1.0, "why": "nima uchun"},
    {"name": "O'zbekcha nom 3", "latin": "Latin 3", "confidence": 0.0-1.0, "why": "nima uchun"}
  ],
  "summary": "1-2 jumla tavsif",
  "description": "3-5 jumla to'liq tavsif",
  "habitat": "Qayerda o'sadi",
  "uses": "Foydasi",
  "warnings": "Xavfi",
  "first_aid": "Xavf bo'lsa yordam, yo'q bo'lsa bo'sh",
  "red_book": true/false,
  "iucn_status": "LC/NT/VU/EN/CR/NE",
  "regions": "Qayerda tarqalgan"
}

Aniqlanmasa (rasmda o'simlik/hayvon ko'rinmasa): {"found": false, "reason": "sabab"}
Faqat JSON, boshqa matn yo'q."""


def identify_species_from_image(image_bytes: bytes, mime: str = "image/jpeg") -> dict:
    """Vision orqali rasmdan turni aniqlash.

    OpenRouter (asosiy) yoki Groq (fallback) — bir nechta model'ni navbatma-navbat sinaydi.
    """
    if not ai_has_key():
        return {"found": False, "reason": "AI kalit sozlanmagan (OPENROUTER_API_KEY/GROQ_API_KEY)"}

    # 1. Rasmni siqish — Groq limit: 4MB base64 (~3MB faylga to'g'ri keladi)
    try:
        compressed = _compress_image(image_bytes, max_dim=1024, quality=82)
    except Exception as e:
        log.exception("Image compress error: %s", e)
        return {"found": False, "reason": "Rasmni qayta ishlashda xatolik"}

    b64 = base64.b64encode(compressed).decode()
    size_kb = len(b64) / 1024
    log.info("Groq vision: uploading %.0f KB base64", size_kb)

    # 2. Provider'ga qarab modellar — OpenRouter yoki Groq
    base_url, api_key, extra_headers = ai_provider()
    MODELS = vision_models()

    last_err = None
    for model in MODELS:
        try:
            r = requests.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    **extra_headers,
                },
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": GROQ_VISION_PROMPT},
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                                },
                            ],
                        }
                    ],
                    "temperature": 0.1,
                    "max_tokens": 1500,
                    # response_format'siz — ba'zi modellar (Pixtral, Gemini)
                    # uni qo'llab-quvvatlamaydi va 400 qaytaradi.
                    # Promptda "Faqat JSON" deyilgan, model itoat qiladi.
                },
                timeout=12,  # tez fail — keyingi modelga o'tish uchun
            )
            if r.status_code >= 400:
                body = r.text[:300]
                log.warning("AI %s → %s: %s", model, r.status_code, body)
                last_err = f"{r.status_code}: {body}"
                continue

            data = r.json()
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            log.info("✓ Groq (%s) identified: %s (conf=%.2f)", model, parsed.get("latin"), parsed.get("confidence", 0))

            # GUARD: confidence floor — past confidence past = "topilmadi"
            if parsed.get("found"):
                conf = float(parsed.get("confidence") or 0.0)
                if conf < 0.40:
                    log.info("rejecting low-confidence (%.2f) AI guess: %s", conf, parsed.get("latin"))
                    return {
                        "found": False,
                        "reason": f"Aniq tanib bo'lmadi (ishonch {int(conf*100)}%) — yaxshiroq rasm kerak",
                    }
                # GUARD: kategoriya biologik bo'lishi shart
                cat = (parsed.get("category") or "").lower().strip()
                valid_cats = {"giyoh", "daraxt", "gul", "jonivor", "qush", "ilon", "hasharot", "qoziqorin", "baliq"}
                if cat and cat not in valid_cats:
                    return {"found": False, "reason": "Bu biologik tur emas"}
                # GUARD: lotincha nom haqiqiy ko'rinishda bo'lishi kerak
                latin = (parsed.get("latin") or "").strip()
                if not latin or len(latin) < 4:
                    return {"found": False, "reason": "Tur nomi aniq emas — boshqa rakurs bilan urinib ko'ring"}
            return parsed
        except (requests.RequestException, KeyError, json.JSONDecodeError) as e:
            log.exception("Groq %s error: %s", model, e)
            last_err = str(e)
            continue

    return {"found": False, "reason": f"Barcha modellar ishlamadi. Oxirgi xato: {last_err}"}


def groq_chat(
    prompt: str,
    system: str = "",
    model: str = "",
    *,
    max_tokens: int = 600,
    temperature: float = 0.4,
) -> str:
    """LLM chat — OpenRouter (asosiy) yoki Groq (fallback). Nom legacy."""
    if not ai_has_key():
        return "AI hozir mavjud emas. Kelajakda javob beraman."
    base_url, api_key, extra_headers = ai_provider()
    if not model:
        model = chat_model()
    try:
        r = requests.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                **extra_headers,
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system or "Sen Tog'AI yordamchisisan. O'zbek tilida, qisqa va aniq javob ber."},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
            timeout=30,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except requests.RequestException as e:
        log.exception("AI chat error: %s", e)
        return "Hozir javob bera olmadim. Qayta urinib ko'ring."


# ------------------------------------------------------------------
# SMS gateway (Eskiz / Play Mobile)
# ------------------------------------------------------------------
def send_sms(phone: str, text: str) -> bool:
    """Foydalanuvchiga SMS yuborish. True = muvaffaqiyatli."""
    provider = settings.SMS_PROVIDER

    if provider == "console" or not provider:
        log.info("SMS [dev] → %s: %s", phone, text)
        return True

    if provider == "eskiz":
        if not settings.SMS_ESKIZ_EMAIL or not settings.SMS_ESKIZ_PASSWORD:
            log.warning("Eskiz: credentials yo'q")
            return False
        try:
            # 1. Auth token olish
            auth = requests.post(
                "https://notify.eskiz.uz/api/auth/login",
                data={"email": settings.SMS_ESKIZ_EMAIL, "password": settings.SMS_ESKIZ_PASSWORD},
                timeout=10,
            ).json()
            token = auth.get("data", {}).get("token")
            if not token:
                log.warning("Eskiz auth failed: %s", auth)
                return False
            # 2. SMS yuborish
            r = requests.post(
                "https://notify.eskiz.uz/api/message/sms/send",
                headers={"Authorization": f"Bearer {token}"},
                data={"mobile_phone": phone.lstrip("+"), "message": text, "from": "4546"},
                timeout=10,
            )
            return r.status_code == 200
        except requests.RequestException as e:
            log.exception("Eskiz SMS error: %s", e)
            return False

    log.warning("Unknown SMS provider: %s", provider)
    return False


# ------------------------------------------------------------------
# AI chat (OpenAI yoki Anthropic) — legacy fallback, hozirda groq_chat ishlatiladi
# ------------------------------------------------------------------
def ai_reply(prompt: str, context: str = "") -> str:
    """Suhbat javobi. API key yo'q bo'lsa — canned."""
    system = (
        "Sen Tog'AI yordamchisiman. Markaziy Osiyo tabiati, o'simlik, jonivor, hasharot "
        "bo'yicha yordam berasan. Javobni qisqa, aniq, o'zbek tilida ber."
    )

    # OpenAI (birinchi)
    if settings.OPENAI_API_KEY:
        try:
            r = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": f"{context}\n\n{prompt}" if context else prompt},
                    ],
                    "max_tokens": 400,
                },
                timeout=30,
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
        except requests.RequestException as e:
            log.exception("OpenAI error: %s", e)

    # Anthropic (fallback)
    if settings.ANTHROPIC_API_KEY:
        try:
            r = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 400,
                    "system": system,
                    "messages": [{"role": "user", "content": f"{context}\n\n{prompt}" if context else prompt}],
                },
                timeout=30,
            )
            r.raise_for_status()
            return r.json()["content"][0]["text"].strip()
        except requests.RequestException as e:
            log.exception("Anthropic error: %s", e)

    # Fallback — canned
    return "Savolingiz uchun rahmat! Bu mavzuni hozir o'rganyapman. Batafsilroq javob uchun /app/chat'dan foydalaning."


# ------------------------------------------------------------------
# Telegram bot OTP (SMS o'rniga — bepul, bizniki)
# ------------------------------------------------------------------
def send_otp_via_telegram(telegram_id: int, code: str) -> bool:
    """Foydalanuvchining Telegram chat'iga OTP kodini yuboradi.

    Alohida OTP bot (TELEGRAM_OTP_BOT_TOKEN) ishlatadi — asosiy bot
    (skaner, chat) bilan aralashmasligi uchun. Agar OTP token yo'q bo'lsa,
    asosiy botga fallback qiladi.

    Sinxron `requests` chaqiruv (bot API HTTP endpoint orqali).
    True = muvaffaqiyatli.
    """
    token = (
        getattr(settings, "TELEGRAM_OTP_BOT_TOKEN", None)
        or getattr(settings, "TELEGRAM_BOT_TOKEN", None)
    )
    if not token:
        log.warning("TELEGRAM_OTP_BOT_TOKEN yo'q — OTP yuborib bo'lmadi")
        return False
    if not telegram_id:
        return False

    text = (
        f"🔐 <b>Tog'AI tasdiqlash kodi</b>\n\n"
        f"<code>{code}</code>\n\n"
        f"Kod 2 daqiqa amal qiladi. Kodni hech kimga bermang."
    )
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": telegram_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=10,
        )
        if r.status_code == 200 and r.json().get("ok"):
            return True
        log.warning("Telegram OTP send failed: %s %s", r.status_code, r.text[:200])
        return False
    except requests.RequestException as e:
        log.exception("Telegram OTP send error: %s", e)
        return False
