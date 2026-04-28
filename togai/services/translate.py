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

CACHE_NS = "tr:uz:v4"
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


# Inglizcha "telltale" so'zlari — bunday so'z bo'lsa = ingliz qoldig'i
_EN_FILLER = re.compile(r"\b(american|asian|african|european|common|wild|northern|southern|tree|flower|bird|black|white|red|green|blue|grass|leaf|water|tit|warbler|finch|sparrow|stork|crane|eagle|hawk|swan|owl|gull|tern|dove|pigeon|the|of|and)\b", re.IGNORECASE)


def _looks_english(text: str) -> bool:
    """Tarjima inglizcha qoldigan bo'lishi mumkinmi?"""
    if not text:
        return False
    # UZ belgisi bo'lsa — ingliz emas
    if _CYRILLIC_UZ.search(text) or _UZ_DIGRAPHS.search(text):
        return False
    # ASCII bo'lib, ingliz so'zlari tarkibida bo'lsa — ingliz
    if all(c.isascii() for c in text) and _EN_FILLER.search(text):
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

    # 2. Cache tekshir (English qoldiqlarni bypass qiladi)
    key = _cache_key(name, latin)
    cached = cache.get(key)
    if cached is not None and cached != "":
        if _looks_english(cached):
            cache.delete(key)
        else:
            return cached
    elif cached == "":
        return name

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

        # Cache (lekin cache'da inglizcha qoldiq bo'lsa qaytadan tarjima qil)
        key = _cache_key(name_n, latin)
        cached = cache.get(key)
        if cached is not None and cached != "":
            if _looks_english(cached):
                # eski stale cache — tashlamiz va qaytadan tarjima qilamiz
                cache.delete(key)
            else:
                out[name] = cached
                continue
        elif cached == "":
            # negative cache — original
            out[name] = name_n
            continue

        pending.append((name_n, latin))

    # AI batch
    if pending:
        try:
            ai_map = _ai_translate_batch(pending)
            ai_map_lc = {k.lower(): v for k, v in ai_map.items()}
            for orig_name, latin in pending:
                tr = (ai_map.get(orig_name) or ai_map_lc.get(orig_name.lower()) or "").strip()
                key = _cache_key(orig_name, latin)

                # 1) Bo'sh yoki orig'ga teng → genus
                if not tr or tr.lower() == orig_name.lower():
                    if latin:
                        tr = latin.split()[0].lower()

                # 2) Tarjima HALI HAM ingliz ko'rinishida → genus (final safety)
                if tr and _looks_english(tr) and latin:
                    log.info("post-fallback: %r still looks english → genus", tr)
                    tr = latin.split()[0].lower()

                if tr and tr.lower() != orig_name.lower():
                    cache.set(key, tr, CACHE_TTL)
                    out[orig_name] = tr
                else:
                    cache.set(key, "", NEG_TTL)
                    out[orig_name] = orig_name
        except Exception as e:
            log.warning("translate_batch failed (%d items): %s", len(pending), e)
            for orig_name, _ in pending:
                out[orig_name] = orig_name

    # FINAL SAFETY NET: agar har qanday output hali ham `_looks_english` bo'lsa,
    # uni latin genus bilan almashtir
    for orig_name, latin in items:
        val = out.get(orig_name)
        if val and _looks_english(val) and latin:
            out[orig_name] = latin.split()[0].lower()

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
        "Siz biolog tarjimon. Sizga ingliz/rus turlar nomi ro'yxati keladi.\n"
        "VAZIFA: Har bir nomni o'zbek tabiat nomiga AYLANTIRING (1-3 so'z, kichik harf bilan).\n"
        "QOIDA:\n"
        "1. NIKADI ingliz/rus nomni QAYTARMA — har doim O'zbek so'z bering\n"
        "2. O'zbek tabiat nomi bo'lmasa: lotincha jins nomi (Liriodendron → 'liriodendron')\n"
        "3. Yoki tipini bering: 'tuliptree' bo'lsa → 'lola daraxti'; 'sparrow' → 'chumchuq turi'\n"
        "4. Bir necha so'zli inglizcha bo'lsa: 'American tuliptree' → 'amerika lola daraxti'\n"
        "FAQAT JSON: {\"results\":[{\"name\":\"input nom\",\"uz\":\"o'zbekcha\"}]}. Boshqa matn yo'q."
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
