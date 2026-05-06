"""Vision AI client — Groq Llama-4 vision models with 4-model fallback chain.

Contract: takes raw image bytes → returns parsed dict (or raises VisionModelError).
Does NOT know about Django models, DB, or business rules.
"""
from __future__ import annotations

import base64
import io
import json
import logging

from PIL import Image

from togai.core.exceptions import (
    ImageProcessingError,
    UpstreamBadResponseError,
    UpstreamUnavailableError,
    VisionModelError,
)
from togai.integrations import ai_has_key, ai_provider, vision_models

from ._http import post_json

log = logging.getLogger(__name__)

PROMPT = """Siz Markaziy Osiyo flora/faunasi bo'yicha ekspert biologsiz.

=== AVVAL — RASMNI TAHLIL QIL ===
Bu rasmda nima bor? Quyidagilardan qaysisi?
  A) Tirik organizm (o'simlik, hayvon, qush, hasharot, qoziqorin, baliq, ilon)
  B) BIOLOGIK BO'LMAGAN: hujjat, matn, ekran skrinshot, kompyuter, telefon, mashina,
     bino, mebel, kiyim, ovqat (tayyor), odam yuzi, logotip, rasm/illustratsiya, va h.k.
  C) Sifatsiz/qorong'i/buzilgan rasm

=== AGAR (B) yoki (C) BO'LSA — KESKIN RAD ET! ===
TAXMIN QILMA. Hech qanday tur nomi BERMA. Quyidagi javobni qaytar:
{"found": false, "reason": "Rasmda tirik organizm topilmadi"}
yoki
{"found": false, "reason": "Hujjat/matn rasmi — biologik tur emas"}
yoki
{"found": false, "reason": "Rasm sifati past — qaytadan urinib ko'ring"}

=== AGAR (A) BO'LSA — QOIDA ===
1. Avval xususiyatlarni kuzating (barg, gul, tikan, pat, tana shakli)
2. KEYIN nom bering
3. Ishonchsiz bo'lsa — confidence past (0.4-0.7), alternatives bering
4. ISHONCH < 0.40 BO'LSA: {"found": false, "reason": "Aniq tanib bo'lmadi — yaxshiroq rasm kerak"}

=== MUHIM FARQLAR ===
ISIRIQ (Peganum harmala) — ingichka ikki qayta patsimon barg, OQ 5-bargli gul, dumaloq meva
SHUVOQ (Artemisia) — kulrang-yashil paxtasimon barg, sariq gajak gullar (isiriq EMAS!)
YANTOQ (Alhagi) — TIKANLI buta, pushti-qizil gul
NA'MATAK (Rosa canina) — tikanli + QIZIL MEVA
ARCHA (Juniperus) — IGNABARG + KO'K MEVA
SAKSOVUL (Haloxylon) — tikansiz bo'g'imli cho'l daraxti

=== FORMAT — faqat JSON ===
Topilsa:
{
  "found": true,
  "key_features": "Nimani ko'rdingiz? (barg/gul/pat/...)",
  "name": "O'zbekcha nomi",
  "latin": "Lotincha",
  "category": "giyoh | daraxt | gul | jonivor | qush | ilon | hasharot | qoziqorin",
  "confidence": 0.0-1.0,
  "alternatives": [{"name":"...","latin":"...","confidence":0.0-1.0,"why":"..."}],
  "summary": "1-2 jumla",
  "description": "3-5 jumla",
  "habitat": "...",
  "uses": "...",
  "warnings": "...",
  "first_aid": "xavf bo'lsa yordam, yo'q bo'lsa bo'sh",
  "red_book": true/false,
  "iucn_status": "LC/NT/VU/EN/CR/NE",
  "regions": "..."
}
Topilmasa:
{"found": false, "reason": "aniq sabab — nima edi rasmda"}"""


def _compress(image_bytes: bytes, max_dim: int = 1024, quality: int = 82) -> bytes:
    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        return buf.getvalue()
    except Exception as e:
        raise ImageProcessingError("compress failed") from e


def _call_one(model: str, b64: str, mime: str) -> dict:
    base_url, api_key, extra_headers = ai_provider()
    payload = {
        "model": model,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": PROMPT},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
            ],
        }],
        "max_tokens": 1500,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    data = post_json(
        f"{base_url}/chat/completions",
        payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            **extra_headers,
        },
        timeout=45,
    )
    raw = data["choices"][0]["message"]["content"]
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise UpstreamBadResponseError(f"{model}: invalid JSON from vision model") from e


def identify(image_bytes: bytes, *, mime: str = "image/jpeg") -> tuple[dict, str]:
    """Run vision AI against image. Returns (parsed_json, model_used).

    Raises VisionModelError if all models fail.
    """
    if not ai_has_key():
        raise VisionModelError("AI key not configured (OPENROUTER_API_KEY/GROQ_API_KEY)")

    compressed = _compress(image_bytes)
    b64 = base64.b64encode(compressed).decode()
    size_kb = len(b64) / 1024
    log.info("vision.identify: %.0f KB base64", size_kb)

    last_err: Exception | None = None
    for model in vision_models():
        try:
            result = _call_one(model, b64, mime)
        except (UpstreamUnavailableError, UpstreamBadResponseError) as e:
            last_err = e
            log.warning("vision model %s failed: %s", model, e)
            continue
        except Exception as e:
            last_err = e
            log.exception("vision model %s unexpected error", model)
            continue

        log.info("vision.identified model=%s latin=%s conf=%.2f",
                 model, result.get("latin"), result.get("confidence", 0))
        return result, model

    raise VisionModelError(f"all vision models failed — last: {last_err}")
