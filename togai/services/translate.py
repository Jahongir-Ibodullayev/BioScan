"""English/Russian → Uzbek tarjima xizmati.

Strategiya:
1. UZ vocab tekshir (instant, bepul) — search.uz_vocab.resolve_latin
2. Cache tekshir (instant, bepul) — Django cache, 30 kun TTL
3. Groq LLM batch tarjima (sekin, lekin keng qamrovli)

Cache key: SHA1(name + latin) — bir xil ingliz nom turli organizmlarga tegishli bo'lishi mumkin.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re

from django.conf import settings
from django.core.cache import cache

log = logging.getLogger(__name__)

CACHE_NS = "tr:uz:v2"
CACHE_TTL = 60 * 60 * 24 * 30  # 30 kun
NEG_TTL = 60 * 60 * 24  # tarjima topilmasa 1 kun cache

# O'zbek-spec apostrofli bo'g'inlar (g', o', n') — faqat shular bor bo'lsa = uz
_UZ_DIGRAPHS = re.compile(r"(g'|o'|G'|O')")
# Cyrillic uzbek belgilari
_CYRILLIC_UZ = re.compile(r"[ўғҳқйшғҳЎҒҲҚЙШ]")
# Ingliz so'zlari ('s, 'd, 'll)
_EN_CONTRACT = re.compile(r"[a-zA-Z]'(s|d|t|ll|re|ve|m)\b")
_LATIN_RE = re.compile(r"^[A-Z][a-z]+\s+[a-z]+$")


def _is_already_uz(text: str) -> bool:
    """Heuristik: matn allaqachon o'zbekchami?

    Faqat aniq UZ-spec belgilari bo'lganda True (g'/o'/cyrillic).
    "Turk's cap" kabi inglizcha apostroflar tarjimaga yuboriladi.
    """
    if not text:
        return True
    # Cyrillic Uzbek — bemalol UZ
    if _CYRILLIC_UZ.search(text):
        return True
    # Ingliz contraction (Turk's, doesn't, etc.) — UZ EMAS
    if _EN_CONTRACT.search(text):
        return False
    # Latin Uzbek apostroflar (g', o', n') — UZ
    if _UZ_DIGRAPHS.search(text):
        return True
    return False


def _is_latin_binomial(text: str) -> bool:
    """Lotincha ilmiy nom bo'lsa tarjima kerak emas."""
    return bool(_LATIN_RE.match(text or ""))


def _cache_key(name: str, latin: str = "") -> str:
    raw = f"{name}|{latin}".lower().strip()
    return f"{CACHE_NS}:{hashlib.sha1(raw.encode()).hexdigest()[:14]}"


def _normalize(text: str) -> str:
    return (text or "").strip()


def translate_one(name: str, latin: str = "") -> str:
    """Bitta nomni tarjima qil. Topilmasa originalni qaytaradi."""
    name = _normalize(name)
    if not name:
        return name

    # 0. Allaqachon o'zbekcha yoki latin — qaytar
    if _is_already_uz(name) or _is_latin_binomial(name):
        return name

    # 1. UZ vocab tekshir
    if latin:
        try:
            from search.uz_vocab import resolve_latin
            ov = resolve_latin(latin)
            if ov:
                return ov["uz"].title() if ov["uz"].islower() else ov["uz"]
        except Exception:
            pass

    # 2. Cache tekshir
    key = _cache_key(name, latin)
    cached = cache.get(key)
    if cached is not None:
        return cached or name

    # 3. AI tarjima
    try:
        translated = _ai_translate_single(name, latin)
        if translated and translated != name:
            cache.set(key, translated, CACHE_TTL)
            return translated
        cache.set(key, "", NEG_TTL)
    except Exception as e:
        log.warning("translate_one(%s) failed: %s", name, e)
        cache.set(key, "", NEG_TTL)

    return name


def translate_batch(items: list[tuple[str, str]]) -> dict[str, str]:
    """Ko'p nomlarni birgalikda tarjima qilish — bitta LLM call.

    items: [(name, latin), ...]
    return: {name: uz_name}
    """
    out: dict[str, str] = {}
    pending: list[tuple[str, str]] = []

    for name, latin in items:
        name_n = _normalize(name)
        if not name_n:
            continue
        if _is_already_uz(name_n) or _is_latin_binomial(name_n):
            out[name] = name_n
            continue

        # UZ vocab
        if latin:
            try:
                from search.uz_vocab import resolve_latin
                ov = resolve_latin(latin)
                if ov:
                    out[name] = ov["uz"].title() if ov["uz"].islower() else ov["uz"]
                    continue
            except Exception:
                pass

        # Cache
        key = _cache_key(name_n, latin)
        cached = cache.get(key)
        if cached is not None:
            out[name] = cached or name_n
            continue

        pending.append((name_n, latin))

    # AI batch
    if pending:
        try:
            ai_map = _ai_translate_batch(pending)
            for orig_name, _ in pending:
                tr = ai_map.get(orig_name) or ""
                key = _cache_key(orig_name, "")
                if tr and tr != orig_name:
                    cache.set(key, tr, CACHE_TTL)
                    out[orig_name] = tr
                else:
                    cache.set(key, "", NEG_TTL)
                    out[orig_name] = orig_name
        except Exception as e:
            log.warning("translate_batch failed (%d items): %s", len(pending), e)
            for orig_name, _ in pending:
                out[orig_name] = orig_name

    return out


def _ai_translate_single(name: str, latin: str = "") -> str:
    """Groq LLM bilan bitta nomni tarjima qil."""
    if not getattr(settings, "GROQ_API_KEY", None):
        return name

    import requests
    sys_prompt = (
        "Siz biolog tarjimon. Ingliz/rus nomidan o'zbek tabiiy nomiga tarjima qiling. "
        "FAQAT bitta o'zbek so'z yoki ibora qaytaring (1-3 so'z), izoh kerak emas. "
        "O'zbek tabiat nomi bo'lmasa, lotincha jinslar (Genus) qaytaring."
    )
    hint = f" (lotincha: {latin})" if latin else ""
    user_prompt = f"Tarjima: {name}{hint}"

    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 30,
        },
        timeout=15,
    )
    r.raise_for_status()
    text = r.json()["choices"][0]["message"]["content"].strip()
    # Strip quotes/punctuation
    text = re.sub(r'^["\'`]|["\'`.]$', "", text).strip()
    return text


def _ai_translate_batch(items: list[tuple[str, str]]) -> dict[str, str]:
    """Groq LLM bilan ko'p nomlarni bitta call ichida."""
    if not getattr(settings, "GROQ_API_KEY", None):
        return {}
    if not items:
        return {}

    import requests

    # Prompt: list of objects, expect list back
    body_items = [{"name": n, "latin": l} for n, l in items[:40]]  # max 40 per call
    sys_prompt = (
        "Siz biolog tarjimon. Sizga ingliz/rus turlar nomi ro'yxati keladi. "
        "Har birini o'zbek tabiat nomiga tarjima qiling (1-3 so'z). "
        "O'zbek nomi bo'lmasa — lotincha jins nomidan foydalaning. "
        "FAQAT JSON qaytaring: {\"results\": [{\"name\":\"...\", \"uz\":\"...\"}]}. Boshqa matn yo'q."
    )

    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": json.dumps({"items": body_items}, ensure_ascii=False)},
            ],
            "temperature": 0.1,
            "max_tokens": 1500,
            "response_format": {"type": "json_object"},
        },
        timeout=25,
    )
    r.raise_for_status()
    raw = r.json()["choices"][0]["message"]["content"]
    parsed = json.loads(raw)
    results = parsed.get("results") or []
    out: dict[str, str] = {}
    for row in results:
        if not isinstance(row, dict):
            continue
        n = (row.get("name") or "").strip()
        uz = (row.get("uz") or "").strip()
        uz = re.sub(r'^["\'`]|["\'`.]$', "", uz).strip()
        if n and uz:
            out[n] = uz
    return out
