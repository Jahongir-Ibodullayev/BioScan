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

CACHE_NS = "tr:uz:v6"
CACHE_TTL = 60 * 60 * 24 * 30  # 30 kun
NEG_TTL = 60 * 60 * 24  # tarjima topilmasa 1 kun cache

# O'zbek-spec apostrofli bo'g'inlar (g', o', n') — faqat shular bor bo'lsa = uz
_UZ_DIGRAPHS = re.compile(r"(g'|o'|G'|O')")
# Cyrillic uzbek-spec belgilari (Russian'da YO'Q)
_CYRILLIC_UZ_ONLY = re.compile(r"[ўғҳқЎҒҲҚ]")
# Russian-spec belgilar (Uzbek'da YO'Q) — bularni topsa = Russian → tarjima
_CYRILLIC_RU_ONLY = re.compile(r"[ыэЫЭъЪ]")
# Cyrillic umuman bormi (har qanday slavyan)
_CYRILLIC_ANY = re.compile(r"[Ѐ-ӿ]")
# Ingliz so'zlari ('s, 'd, 'll)
_EN_CONTRACT = re.compile(r"[a-zA-Z]'(s|d|t|ll|re|ve|m)\b")
_LATIN_RE = re.compile(r"^[A-Z][a-z]+\s+[a-z]+$")


def _is_already_uz(text: str) -> bool:
    """Heuristik: matn allaqachon o'zbekchami?

    - ы/э/ъ topilsa → Russian (UZ EMAS — tarjima qilinadi)
    - ў/ғ/ҳ/қ topilsa → UZ Cyrillic
    - g'/o' digraflari topilsa → UZ Latin
    - Inglizcha 's/'d/'ll → UZ EMAS
    """
    if not text:
        return True
    # Russian belgisi → UZ emas
    if _CYRILLIC_RU_ONLY.search(text):
        return False
    # UZ Cyrillic belgisi → UZ
    if _CYRILLIC_UZ_ONLY.search(text):
        return True
    # Cyrillic bor lekin UZ-spec yo'q → ehtimol Russian (zaif belgi)
    # Ingliz contraction (Turk's, doesn't, etc.) — UZ EMAS
    if _EN_CONTRACT.search(text):
        return False
    # Latin Uzbek apostroflar (g', o', n') — UZ
    if _UZ_DIGRAPHS.search(text):
        return True
    # Hech qanday belgi yo'q — Latin alifbosida bo'lsa, ingliz/uzlatin bo'lishi mumkin
    # Cyrillic bor bo'lib UZ-spec yo'q bo'lsa — Russian deb hisoblaymiz (tarjima qilamiz)
    if _CYRILLIC_ANY.search(text):
        return False
    return False


# Inglizcha "telltale" so'zlari — bunday so'z bo'lsa = ingliz qoldig'i
_EN_FILLER = re.compile(r"\b(american|asian|african|european|common|wild|northern|southern|tree|flower|bird|black|white|red|green|blue|grass|leaf|water|tit|warbler|finch|sparrow|stork|crane|eagle|hawk|swan|owl|gull|tern|dove|pigeon|the|of|and)\b", re.IGNORECASE)


def _looks_english(text: str) -> bool:
    """Tarjima inglizcha qoldigan bo'lishi mumkinmi?"""
    if not text:
        return False
    # UZ belgisi bo'lsa — ingliz emas
    if _CYRILLIC_UZ_ONLY.search(text) or _UZ_DIGRAPHS.search(text):
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

    # 2. Cache tekshir (English qoldiqlarni bypass qiladi, negative cache ham)
    key = _cache_key(name, latin)
    cached = cache.get(key)
    if cached:
        if _looks_english(cached):
            cache.delete(key)
        else:
            return cached
    # cached == "" yoki None → AI'ga o'tamiz (negative cache shortcut yo'q)

    # 3. AI tarjima
    try:
        translated = _ai_translate_single(name, latin)
        # Safety net: AI tarjimasi hali ham ingliz ko'rinishida bo'lsa → genus
        if translated and (translated.lower() == name.lower() or _looks_english(translated)):
            translated = latin.split()[0].lower() if latin else ""
        if translated and translated.lower() != name.lower() and not _looks_english(translated):
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


def ensure_uz(text: str, *, kind: str = "auto") -> str:
    """Universal: matn ingliz/rus bo'lsa, AI orqali O'zbekchaga aylantir.

    kind: "name" (1-3 so'z, qisqa) yoki "block" (paragraf) yoki "auto"
    """
    text = _normalize(text)
    if not text:
        return text
    # Allaqachon o'zbekcha — qaytar
    if _is_already_uz(text):
        return text
    # Latin binomial — qaytar
    if _is_latin_binomial(text):
        return text

    # Auto: uzunlik bilan tanlash
    if kind == "auto":
        kind = "block" if len(text) > 80 else "name"

    if kind == "name":
        return translate_one(text)

    # block: cache + AI bilan paragraf tarjima
    key = _cache_key(text[:200], "block")
    cached = cache.get(key)
    if cached is not None and cached != "":
        if _looks_english(cached[:120]):
            cache.delete(key)
        else:
            return cached
    elif cached == "":
        return text

    try:
        translated = _ai_translate_block(text)
        if translated and translated != text and not _looks_english(translated[:120]):
            cache.set(key, translated, CACHE_TTL)
            return translated
        cache.set(key, "", NEG_TTL)
    except Exception as e:
        log.warning("ensure_uz block translation failed: %s", e)
        cache.set(key, "", NEG_TTL)
    return text


def _ai_translate_block(text: str) -> str:
    """Groq LLM bilan paragraf tarjima."""
    if not getattr(settings, "GROQ_API_KEY", None):
        return text

    import requests
    sys_prompt = (
        "Siz biologiya/tabiat sohasidagi tarjimon. "
        "Sizga ingliz yoki rus tilidagi matn keladi — uni TABIIY o'zbek tiliga tarjima qiling. "
        "Ilmiy lotin nomlarini O'ZGARTIRMASDAN qoldiring. "
        "Faqat tarjima matnini qaytaring, hech qanday izoh yoki sarlavha yo'q."
    )
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": text[:3000]},
            ],
            "temperature": 0.2,
            "max_tokens": 1200,
        },
        timeout=25,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


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


# ============================================================
# UZ → Latin/English (qidiruv uchun)
# ============================================================
UZ_TO_SCI_NS = "uz2sci:v1"
UZ_TO_SCI_TTL = 60 * 60 * 24 * 30  # 30 kun


def uz_to_scientific(query: str) -> dict | None:
    """O'zbek qidiruv so'zini ilmiy (Latin) yoki inglizcha umumiy nomga o'giradi.

    Cache + Groq LLM. Topa olmasa None qaytaradi.

    Qaytariladi:
      {
        "scientific": "Camelus bactrianus",   # iNat'ga yuboriladigan asosiy
        "english":    "bactrian camel",       # fallback
        "category":   "animal" | "plant" | "bird" | "insect" | "reptile" | "fungi" | None,
      }
    """
    q = (query or "").strip()
    if not q or len(q) > 60:
        return None
    if not getattr(settings, "GROQ_API_KEY", None):
        return None

    key = f"{UZ_TO_SCI_NS}:{hashlib.sha1(q.lower().encode()).hexdigest()[:14]}"
    cached = cache.get(key)
    if cached is not None:
        return cached or None  # bo'sh dict → None

    import requests

    sys_prompt = (
        "Siz biolog-eksperti. Foydalanuvchi o'zbek tilida tabiat ob'ektini qidiryapti "
        "(o'simlik, hayvon, qush, hasharot, baliq, gul, daraxt, qo'ziqorin va h.k.). "
        "Vazifa: o'zbek nomdan iNaturalist/GBIF bazasi tushunadigan ILMIY (Latin) nom va "
        "INGLIZCHA umumiy nomni qaytaring.\n"
        "QOIDALAR:\n"
        "1. Aniq tur bo'lsa: binomial Latin (masalan 'tuya' → 'Camelus')\n"
        "2. Familiya/turkum bo'lsa: bitta so'z (Genus yoki Family)\n"
        "3. Belgilamasa: bo'sh qoldiring\n"
        "4. category: plant | animal | bird | insect | reptile | fungi | (yoki bo'sh)\n"
        "FAQAT JSON, izoh yo'q: "
        '{"scientific":"...","english":"...","category":"..."}'
    )

    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": q},
                ],
                "temperature": 0.0,
                "max_tokens": 80,
                "response_format": {"type": "json_object"},
            },
            timeout=12,
        )
        r.raise_for_status()
        raw = r.json()["choices"][0]["message"]["content"]
        data = json.loads(raw)
    except Exception as e:
        log.warning("uz_to_scientific failed for %r: %s", q, e)
        cache.set(key, {}, NEG_TTL)
        return None

    scientific = (data.get("scientific") or "").strip()
    english = (data.get("english") or "").strip()
    category = (data.get("category") or "").strip().lower() or None

    # Tozalash: faqat Latin ASCII bo'lishi kerak
    if scientific and not re.match(r"^[A-Za-z][A-Za-z\s\-]+$", scientific):
        scientific = ""

    if not (scientific or english):
        cache.set(key, {}, NEG_TTL)
        return None

    result = {
        "scientific": scientific,
        "english": english,
        "category": category,
    }
    cache.set(key, result, UZ_TO_SCI_TTL)
    return result
