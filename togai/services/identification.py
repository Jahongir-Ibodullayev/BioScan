"""Species identification service — orchestrates vision + DB.

Responsibility:
  1. Call vision AI (togai.clients.vision)
  2. Upsert Species in DB from AI result
  3. Persist Observation if user is authenticated
  4. Return typed IdentificationResult

This is the ONLY layer that mutates DB after a scan.
"""
from __future__ import annotations

import logging
from typing import Any

from django.utils.text import slugify

from togai.core.exceptions import ImageProcessingError, VisionModelError
from togai.core.schemas import (
    IdCandidate,
    IdentificationResult,
    Photo,
    SpeciesDetail,
    Taxonomy,
)

log = logging.getLogger(__name__)


def _icon_for_category(cat: str) -> str:
    return {
        "giyoh": "leaf", "daraxt": "tree", "gul": "flower",
        "jonivor": "paw", "hasharot": "paw", "qush": "paw",
        "ilon": "paw", "baliq": "paw", "qoziqorin": "mushroom",
    }.get(cat, "leaf")


def _upsert_species_from_ai(ai: dict) -> Any:
    """Create or update catalog.Species from AI response. Returns model instance."""
    from catalog.models import Species  # lazy import to avoid app-loading issues

    latin = (ai.get("latin") or "").strip()
    name = (ai.get("name") or "").strip() or latin
    slug = slugify(latin or name) or f"tur-{abs(hash(name))}"[:20]

    defaults = {
        "name": name or latin,
        "latin": latin,
        "category": ai.get("category") or "giyoh",
        "icon_name": _icon_for_category(ai.get("category") or ""),
        "summary": (ai.get("summary") or "")[:280],
        "description": ai.get("description") or "",
        "habitat": ai.get("habitat") or "",
        "uses": ai.get("uses") or "",
        "warnings": ai.get("warnings") or "",
        "first_aid": ai.get("first_aid") or "",
        "red_book": bool(ai.get("red_book")),
        "iucn_status": (ai.get("iucn_status") or "NE")[:4],
        "regions": ai.get("regions") or "",
    }
    species, _created = Species.objects.update_or_create(slug=slug, defaults=defaults)
    return species


def _to_detail(species: Any, preview_url: str | None = None) -> SpeciesDetail:
    """Map catalog.Species → SpeciesDetail DTO."""
    photo: Photo | None = None
    url = preview_url
    if not url:
        url = species.image_url or (species.image.url if species.image else None)
    if url:
        photo = Photo(url=url)

    return SpeciesDetail(
        source="local",
        source_id=species.slug,
        name=species.name,
        latin=species.latin,
        category=species.category or "other",
        rank="species",
        photo=photo,
        iucn_status=(species.iucn_status or None) if species.iucn_status in (
            "CR", "EN", "VU", "NT", "LC", "DD", "NE") else None,
        redbook=bool(species.red_book),
        description=species.description or "",
        uses=species.uses or "",
        warnings=species.warnings or "",
        first_aid=species.first_aid or "",
        habitat=species.habitat or "",
        regions=species.regions or "",
        taxonomy=Taxonomy(),
        photos=[photo] if photo else [],
        fine_bhm_min=getattr(species, "fine_bhm_min", None),
        fine_bhm_max=getattr(species, "fine_bhm_max", None),
        law_article=getattr(species, "law_article", None),
    )


def _random_fallback_detail() -> SpeciesDetail | None:
    """Pick a random species from local DB when vision fails."""
    import random
    from catalog.models import Species
    candidates = list(Species.objects.all()[:100])
    if not candidates:
        return None
    sp = random.choice(candidates)
    return _to_detail(sp)


def identify_from_image(
    image_bytes: bytes,
    *,
    mime: str = "image/jpeg",
    user=None,
    latitude: float | None = None,
    longitude: float | None = None,
) -> IdentificationResult:
    """Main entry point — runs the full scan pipeline.

    Returns IdentificationResult (never raises to caller — errors become `found=false`).
    """
    from togai.clients import vision

    # 1. Vision AI call
    try:
        ai, model_used = vision.identify(image_bytes, mime=mime)
    except (VisionModelError, ImageProcessingError) as e:
        log.warning("identify: vision failed (%s) — falling back to local random", e)
        fallback = _random_fallback_detail()
        return IdentificationResult(
            found=bool(fallback),
            primary=fallback,
            fallback=True,
            confidence=0.6 if fallback else 0.0,
            reason=str(e) if not fallback else "",
            model_used="",
        )

    if not ai.get("found"):
        return IdentificationResult(
            found=False,
            reason=ai.get("reason") or "AI tanib olmadi",
            model_used=model_used,
        )

    # 2. Upsert Species row in DB
    try:
        species = _upsert_species_from_ai(ai)
    except Exception as e:
        log.exception("identify: species upsert failed")
        return IdentificationResult(
            found=False, reason=f"DB error: {e}", model_used=model_used,
        )

    # 3. Build detail DTO
    detail = _to_detail(species)
    detail.description = ai.get("description") or detail.description
    detail.uses = ai.get("uses") or detail.uses
    detail.warnings = ai.get("warnings") or detail.warnings
    detail.first_aid = ai.get("first_aid") or detail.first_aid

    # 4. Observation (only if logged in)
    confidence = float(ai.get("confidence") or 0.8)
    if user is not None and getattr(user, "is_authenticated", False):
        try:
            from observations.models import Observation
            Observation.objects.create(
                user=user,
                species=species,
                ai_confidence=confidence,
                latitude=latitude,
                longitude=longitude,
            )
        except Exception:
            log.exception("identify: observation save failed (non-fatal)")

    # 5. Alternatives
    alts: list[IdCandidate] = []
    for raw_alt in (ai.get("alternatives") or [])[:5]:
        if not isinstance(raw_alt, dict):
            continue
        alts.append(IdCandidate(
            name=raw_alt.get("name") or "",
            latin=raw_alt.get("latin") or "",
            confidence=float(raw_alt.get("confidence") or 0.0),
            why=raw_alt.get("why") or "",
        ))

    return IdentificationResult(
        found=True,
        primary=detail,
        confidence=confidence,
        alternatives=alts,
        key_features=ai.get("key_features") or "",
        model_used=model_used,
        fallback=False,
    )
