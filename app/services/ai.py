"""OpenRouter chat + vision — Django'ning togai/integrations.py async portasi."""
from __future__ import annotations

import base64
import json
import logging
from typing import Optional

import httpx

from app.core.config import settings

log = logging.getLogger(__name__)


async def _provider(url: str, key: str, model: str, msgs: list, mt: int, tp: float) -> Optional[str]:
    if not key:
        return None
    try:
        async with httpx.AsyncClient(timeout=30.0) as c:
            r = await c.post(url, headers={"Authorization": f"Bearer {key}"},
                             json={"model": model, "messages": msgs, "max_tokens": mt, "temperature": tp})
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        log.warning("provider %s/%s failed: %s", url.split("/")[2], model, e)
        return None


async def openrouter_chat(prompt: str, system: str = "", max_tokens: int = 600,
                          temperature: float = 0.4, model: Optional[str] = None) -> str:
    """Groq (asosiy) → OpenRouter (fallback). OpenRouter eski model'lar 404."""
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    # Groq — Llama 3.3 70B versatile (ishonchli)
    txt = await _provider("https://api.groq.com/openai/v1/chat/completions",
                          settings.GROQ_API_KEY, "llama-3.3-70b-versatile", msgs, max_tokens, temperature)
    if txt:
        return txt
    # OpenRouter fallback — bepul model
    txt = await _provider(f"{settings.OPENROUTER_BASE}/chat/completions",
                          settings.OPENROUTER_API_KEY, "meta-llama/llama-3.1-70b-instruct:free",
                          msgs, max_tokens, temperature)
    if txt:
        return txt
    return "Hozir javob bera olmadim — qaytadan urinib ko'ring."


async def identify_species_from_image(image_bytes: bytes, mime: str = "image/jpeg") -> dict:
    """Vision API — rasmda turni aniqlash.

    Django integrations.identify_species_from_image bilan teng struktura.
    Return: {found, name, latin, category, summary, description, ...} yoki
            {found: False, reason: "..."}
    """
    # Groq vision birinchi (ishonchli), OpenRouter fallback
    if not (settings.GROQ_API_KEY or settings.OPENROUTER_API_KEY):
        return {"found": False, "reason": "AI mavjud emas"}

    b64 = base64.b64encode(image_bytes).decode()
    data_url = f"data:{mime};base64,{b64}"

    prompt = (
        "Quyidagi rasmni ko'rib, bittagina biologik turni aniqlang. Faqat JSON qaytaring:\n"
        '{"found": bool, "name": "...", "latin": "...", "category": "giyoh|daraxt|gul|jonivor|hasharot|qush|qoziqorin",'
        ' "summary": "...", "description": "...", "habitat": "...", "uses": "...", "warnings": "...", "first_aid": "...",'
        ' "regions": "...", "confidence": 0.0-1.0}'
        "Agar rasmda tur ko'rinmasa: {\"found\": false, \"reason\": \"...\"}. Faqat o'zbek tilida yozing."
    )

    # Provider tanlash: Groq → OpenRouter fallback (model 404 muammosi)
    if settings.GROQ_API_KEY:
        api_url = "https://api.groq.com/openai/v1/chat/completions"
        api_key = settings.GROQ_API_KEY
        vision_model = "llama-3.2-90b-vision-preview"
    else:
        api_url = f"{settings.OPENROUTER_BASE}/chat/completions"
        api_key = settings.OPENROUTER_API_KEY
        vision_model = "meta-llama/llama-3.2-11b-vision-instruct:free"
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(
                api_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": vision_model,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {"type": "image_url", "image_url": {"url": data_url}},
                            ],
                        }
                    ],
                    "max_tokens": 700,
                    "temperature": 0.2,
                },
            )
            r.raise_for_status()
            data = r.json()
        text = data["choices"][0]["message"]["content"]
        return json.loads(text)
    except (httpx.HTTPError, KeyError, IndexError, json.JSONDecodeError) as e:
        log.warning("vision identify failed: %s", e)
        return {"found": False, "reason": "AI xato bilan javob qaytardi"}
