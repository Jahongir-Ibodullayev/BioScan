"""Species enrichment service — Wikipedia + AI → structured Uzbek info.

Composition:
  Wikipedia (uz → ru → en cascade) → raw extract
  LLM (with safety prompt) → TAVSIF / FOYDASI / XAVFI / BIRINCHI YORDAM

Result is cached 24h — same species rarely changes its biology.
"""
from __future__ import annotations

import logging

from togai.clients import llm, wikipedia
from togai.core.cache import get_or_set
from togai.core.schemas import EnrichmentResult

log = logging.getLogger(__name__)


_CATEGORY_HINT = {
    "Aves":             "QUSH (bird)",
    "Mammalia":         "SUTEMIZUVCHI (mammal)",
    "Reptilia":         "SUDRALIB YURUVCHI (reptile)",
    "Amphibia":         "SUV-QURUQLIK (amphibian)",
    "Actinopterygii":   "BALIQ (fish)",
    "Insecta":          "HASHAROT (insect)",
    "Arachnida":        "O'RGIMCHAKSIMON (arachnid)",
    "Plantae":          "O'SIMLIK (plant)",
    "Fungi":            "QO'ZIQORIN (fungus)",
    "Mollusca":         "MOLLYUSKA (mollusk)",
    "Animalia":         "HAYVON (animal)",
}

_SYSTEM_PROMPT = (
    "Sen BioScan yordamchisisan — FAQAT biologiya/tabiat ekspertisan. "
    "Sen BIOLOGIK TURLAR haqida yozasan — o'simlik, hayvon, qush, baliq, hasharot, qo'ziqorin. "
    "HECH QACHON texnika, mashina, poyezd, mahsulot, brend haqida yozma — "
    "xalq nomi poyezd/mashina bilan bir xil bo'lsa ham, bu BIOLOGIK TUR haqida gap ketyapti. "
    "Faqat Wikipedia'dagi haqiqiy biologik ma'lumotdan foydalan. "
    "Bilmasang — 'Ma'lumot yetarli emas' deb yoz. Yolg'on/taxmin yozma."
)


def _parse_sections(text: str) -> dict:
    """Parse TAVSIF:/FOYDASI:/XAVFI:/BIRINCHI YORDAM: blocks from LLM output."""
    if not text:
        return {}
    sections: dict[str, str] = {}
    markers = {
        "TAVSIF": "description",
        "FOYDASI": "uses",
        "XAVFI": "warnings",
        "BIRINCHI YORDAM": "first_aid",
    }
    current: str | None = None
    buf: list[str] = []
    for line in text.split("\n"):
        stripped = line.strip()
        up = stripped.upper()
        matched = None
        for marker, key in markers.items():
            if up.startswith(marker + ":") or up.startswith(marker):
                matched = key
                rest = stripped.split(":", 1)[1].strip() if ":" in stripped else ""
                break
        if matched:
            if current and buf:
                sections[current] = "\n".join(buf).strip()
            current = matched
            buf = [rest] if rest else []
        elif current:
            buf.append(line)
    if current and buf:
        sections[current] = "\n".join(buf).strip()
    return sections


def enrich(
    *,
    latin: str,
    common: str = "",
    category: str = "",
    ttl: int = 24 * 60 * 60,
) -> EnrichmentResult:
    """Get Wikipedia summary + AI structured info for a species."""
    cache_parts = (latin, common, category)

    def _load() -> EnrichmentResult:
        # 1. Wikipedia cascade
        wiki = wikipedia.get_cascade(
            (common or latin, "uz"),
            (common or latin, "ru"),
            (latin, "en"),
            (common, "en") if common else (latin, "en"),
        )

        # 2. Build LLM context
        cat_hint = _CATEGORY_HINT.get(category, category or "JONZOT")
        ctx_lines = [
            f"Ilmiy (lotincha) nom: {latin}",
            f"Taksonomik kategoriya: {cat_hint}",
        ]
        if common and common.lower() != latin.lower():
            ctx_lines.append(f"Ingliz/xalq nomi: {common}")
        if wiki and wiki.extract:
            ctx_lines.append(f"\nWikipedia'dan olingan ma'lumot:\n{wiki.extract[:1000]}")

        prompt = (
            f"Quyidagi BIOLOGIK TUR haqida O'ZBEK tilida yoz:\n\n"
            + "\n".join(ctx_lines) + "\n\n"
            "=== FORMAT ===\n"
            "4 bo'limda (har biri 2-3 jumla). Sarlavhalarni KATTA HARFDA yoz:\n\n"
            "TAVSIF: bu nima, qayerda yashaydi/o'sadi, qanday ko'rinadi\n"
            "FOYDASI: odamga/tabiatga foydasi\n"
            "XAVFI: zaharli/yirtqich/allergen bo'lsa; xavf yo'q bo'lsa 'Xavf aniqlanmagan'\n"
            "BIRINCHI YORDAM: xavfli bo'lsa yordam; yo'q bo'lsa 'Kerak emas'\n\n"
            f"MUHIM: {latin} — BIOLOGIK TUR. Texnika/brend nomi bilan aralashtirma."
        )

        # 3. Run LLM
        try:
            ai_text = llm.chat(prompt, system=_SYSTEM_PROMPT)
        except Exception as e:
            log.warning("enrichment llm failed: %s", e)
            ai_text = ""

        sections = _parse_sections(ai_text)

        return EnrichmentResult(
            name=common or latin,
            latin=latin,
            description=sections.get("description") or (wiki.extract if wiki else ""),
            uses=sections.get("uses", ""),
            warnings=sections.get("warnings", ""),
            first_aid=sections.get("first_aid", ""),
            wikipedia=wiki,
        )

    return get_or_set("enrich", cache_parts, _load, ttl=ttl)
