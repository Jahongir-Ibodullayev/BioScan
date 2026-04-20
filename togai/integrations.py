"""External services (stubs — qulay prod-ready skeleton).

Har bir servis kaliti yo'q bo'lsa — mock ishlatadi, bo'lsa — real API.
"""
from __future__ import annotations

import base64
import io
import json
import logging
import random

import requests
from django.conf import settings
from PIL import Image

log = logging.getLogger(__name__)


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
Rasmdagi turni ANIQ aniqlang — o'xshash turlarni ARALASHTIRMANG.

=== MUHIM FARQLAR (tez-tez aralashtiriladigan o'simliklar) ===

ISIRIQ (Peganum harmala) — alohida!
  - Ingichka bargli o'simlik, bargi paporotniksimon ikki qayta patsimon
  - OQ gul, 5 bargli, o'rtasida sariq chang
  - Dumaloq, yashil-sariq meva (keyin jigarrang)
  - Bo'yi 20-70 cm, tikansiz
  - CO2 bilan yoqiladigan mashhur hazorasfand

SHUVOQ (Artemisia) — ISIRIQ EMAS!
  - Kulrang-yashil, paxta-may suvli barg
  - Achchiq hid, kichik sariq gullar gajak
  - Artemisia vulgaris — qora shuvoq

SALSOLA (saltwort) — ISIRIQ EMAS!
  - Shu'lali suvchil cho'l o'simligi
  - Tikansimon, bargsiz bo'g'imli poya

YANTOQ (Alhagi pseudalhagi)
  - Tikanli buta, pushti-qizil gul
  - Dukkakdoshlar oilasi, kich kichik yashil barglar

NA'MATAK (Rosa canina) — tikanli buta, qizil meva
ARCHA (Juniperus) — ignabargli daraxt, ko'k meva
SAKSOVUL (Haloxylon) — tikansiz shoxli cho'l daraxti
YALPIZ (Mentha) — xushbo'y, ya'lizli
SEDANA (Nigella) — ko'k gul, qora urug'

Avvaliga rasmdagi xususiyatlarni aniq kuzating, KEYIN nom bering.
Ishonch past bo'lsa, confidence'ni past qo'ying (0.5-0.7).
Taxmin qilish EMAS — kuzatishga asoslanib.

O'zbek tilida, FAQAT JSON qaytaring:

{
  "found": true/false,
  "name": "O'zbekcha nomi",
  "latin": "Ilmiy nom",
  "category": "giyoh | daraxt | gul | jonivor | hasharot | qush | qoziqorin",
  "confidence": 0.0-1.0,
  "key_features": "Rasmda ko'rgan asosiy xususiyatlar (qanday barglar, gullar, meva, rang...)",
  "summary": "1-2 jumla tavsif",
  "description": "3-5 jumla to'liq tavsif",
  "habitat": "Qayerda o'sadi/yashaydi",
  "uses": "Foydasi",
  "warnings": "Xavfi (zaharli, allergen)",
  "first_aid": "Xavf bo'lsa yordam, yo'q bo'lsa bo'sh",
  "red_book": true/false,
  "iucn_status": "LC/NT/VU/EN/CR/NE",
  "regions": "Qayerda tarqalgan",
  "similar_species": ["o'xshash tur 1", "o'xshash tur 2"]
}

Aniqlanmasa: {"found": false, "reason": "sabab"}
Faqat JSON, boshqa matn yo'q."""


def identify_species_from_image(image_bytes: bytes, mime: str = "image/jpeg") -> dict:
    """Groq Vision orqali rasmdan turni aniqlash.

    Bir nechta model'ni navbatma-navbat sinaydi.
    """
    if not settings.GROQ_API_KEY:
        return {"found": False, "reason": "GROQ_API_KEY sozlanmagan"}

    # 1. Rasmni siqish — Groq limit: 4MB base64 (~3MB faylga to'g'ri keladi)
    try:
        compressed = _compress_image(image_bytes, max_dim=1024, quality=82)
    except Exception as e:
        log.exception("Image compress error: %s", e)
        return {"found": False, "reason": "Rasmni qayta ishlashda xatolik"}

    b64 = base64.b64encode(compressed).decode()
    size_kb = len(b64) / 1024
    log.info("Groq vision: uploading %.0f KB base64", size_kb)

    # 2. Navbatda 3 model — biri ishlamasa, keyingisiga
    MODELS = [
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "meta-llama/llama-4-maverick-17b-128e-instruct",
        "llama-3.2-90b-vision-preview",
        "llama-3.2-11b-vision-preview",
    ]

    last_err = None
    for model in MODELS:
        try:
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                    "Content-Type": "application/json",
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
                    "response_format": {"type": "json_object"},
                },
                timeout=90,
            )
            if r.status_code >= 400:
                body = r.text[:500]
                log.warning("Groq %s → %s: %s", model, r.status_code, body)
                last_err = f"{r.status_code}: {body}"
                continue

            data = r.json()
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            log.info("✓ Groq (%s) identified: %s (conf=%.2f)", model, parsed.get("latin"), parsed.get("confidence", 0))
            return parsed
        except (requests.RequestException, KeyError, json.JSONDecodeError) as e:
            log.exception("Groq %s error: %s", model, e)
            last_err = str(e)
            continue

    return {"found": False, "reason": f"Barcha modellar ishlamadi. Oxirgi xato: {last_err}"}


def groq_chat(prompt: str, system: str = "", model: str = "llama-3.3-70b-versatile") -> str:
    """Groq tez LLM — AI chat uchun."""
    if not settings.GROQ_API_KEY:
        return "AI hozir mavjud emas. Kelajakda javob beraman."
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system or "Sen Tog'AI yordamchisisan. O'zbek tilida, qisqa va aniq javob ber."},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 600,
                "temperature": 0.4,
            },
            timeout=30,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except requests.RequestException as e:
        log.exception("Groq chat error: %s", e)
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
# Plant.id — AI image recognition
# ------------------------------------------------------------------
def identify_plant(image_bytes: bytes) -> dict:
    """Plant.id API orqali rasmdagi turni aniqlash.

    Return: {"species_name": str, "latin": str, "confidence": float, "meta": dict}
    """
    if not settings.PLANT_ID_API_KEY:
        # Mock — random confidence
        log.info("Plant.id key yo'q — mock javob")
        return {
            "species_name": None,
            "latin": None,
            "confidence": round(random.uniform(0.82, 0.99), 2),
            "meta": {"mock": True},
        }

    try:
        r = requests.post(
            "https://api.plant.id/v2/identify",
            json={
                "api_key": settings.PLANT_ID_API_KEY,
                "images": [base64.b64encode(image_bytes).decode()],
                "modifiers": ["crops_fast", "similar_images"],
                "plant_language": "en",
                "plant_details": ["common_names", "url", "wiki_description", "taxonomy"],
            },
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        suggestions = data.get("suggestions") or []
        if not suggestions:
            return {"species_name": None, "latin": None, "confidence": 0.0, "meta": {}}
        top = suggestions[0]
        return {
            "species_name": (top.get("plant_details", {}).get("common_names") or [None])[0],
            "latin": top.get("plant_name"),
            "confidence": top.get("probability", 0),
            "meta": top,
        }
    except requests.RequestException as e:
        log.exception("Plant.id error: %s", e)
        return {"species_name": None, "latin": None, "confidence": 0.0, "meta": {"error": str(e)}}


# ------------------------------------------------------------------
# AI chat (OpenAI yoki Anthropic)
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
