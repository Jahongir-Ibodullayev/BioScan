"""Business logic — real AI vision + DB lookup."""
from __future__ import annotations

import logging
from asgiref.sync import sync_to_async
from django.utils.text import slugify

from catalog.models import Species
from togai.integrations import identify_species_from_image

log = logging.getLogger(__name__)


@sync_to_async
def _sync_identify(photo_bytes: bytes, mime: str) -> tuple[Species | None, float]:
    """Synchronous helper — runs AI vision + upserts Species in DB."""
    if not photo_bytes:
        return None, 0.0

    try:
        result = identify_species_from_image(photo_bytes, mime=mime)
    except Exception as e:
        log.exception("Vision AI failed: %s", e)
        return None, 0.0

    if not result.get("found"):
        log.warning("AI couldn't identify: %s", result.get("reason"))
        return None, 0.0

    latin = (result.get("latin") or "").strip()
    name = (result.get("name") or "").strip() or latin

    # Override name from UZ vocab (authoritative Uzbek name)
    from search.uz_vocab import resolve_latin
    uz_lookup = resolve_latin(latin)
    if uz_lookup:
        name = uz_lookup["uz"]
        latin = uz_lookup["latin"]
    else:
        # Vocab'da yo'q — agar AI ingliz nom bergan bo'lsa, AI tarjima qil
        try:
            from togai.services.translate import translate_one
            tr = translate_one(name, latin)
            if tr and tr != name:
                name = tr
        except Exception:
            pass

    if not latin and not name:
        return None, 0.0

    slug = slugify(latin or name) or "unknown-species"

    species, _created = Species.objects.update_or_create(
        slug=slug,
        defaults={
            "name": name or latin,
            "latin": latin,
            "category": result.get("category") or "giyoh",
            "icon_name": {
                "giyoh": "leaf", "daraxt": "tree", "gul": "flower",
                "jonivor": "paw", "hasharot": "paw", "qush": "paw",
                "ilon": "paw", "baliq": "paw", "qoziqorin": "mushroom",
            }.get(result.get("category") or "giyoh", "leaf"),
            "summary": (result.get("summary") or "")[:280],
            "description": result.get("description") or "",
            "habitat": result.get("habitat") or "",
            "uses": result.get("uses") or "",
            "warnings": result.get("warnings") or "",
            "first_aid": result.get("first_aid") or "",
            "red_book": bool(result.get("red_book")),
            "iucn_status": (result.get("iucn_status") or "NE")[:4],
            "regions": result.get("regions") or "",
        },
    )

    # If AI returned no image_url on species row, try to enrich from iNat later
    if not species.image_url:
        try:
            import requests
            r = requests.get(
                "https://api.inaturalist.org/v1/taxa",
                params={"q": latin, "per_page": 1, "is_active": "true"},
                headers={"User-Agent": "TogAI-Bot/1.0"},
                timeout=6,
            )
            if r.ok:
                results = (r.json() or {}).get("results") or []
                if results:
                    photo = (results[0].get("default_photo") or {})
                    url = photo.get("medium_url") or photo.get("original_url")
                    if url:
                        species.image_url = url
                        species.save(update_fields=["image_url"])
        except Exception:
            pass  # non-fatal

    confidence = float(result.get("confidence") or 0.8)
    return species, confidence


async def pick_species_for_photo(
    photo_bytes: bytes | None = None,
    mime: str = "image/jpeg",
) -> tuple[Species | None, float]:
    """Real AI identification — replaces old mock.

    Calls Groq Vision → overrides name from UZ vocab → upserts Species row.
    """
    if not photo_bytes:
        return None, 0.0
    return await _sync_identify(photo_bytes, mime)


@sync_to_async
def get_species(slug: str) -> Species | None:
    return Species.objects.filter(slug=slug).first()
