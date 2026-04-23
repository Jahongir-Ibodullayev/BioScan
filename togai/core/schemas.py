"""Typed DTOs — single source of truth for data flowing through the app.

Rule: clients return these; services combine these; views serialize these.
No leaky dicts crossing layer boundaries.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Literal, Optional


# ======================================================================
# Shared primitives
# ======================================================================

Category = Literal[
    "giyoh", "daraxt", "gul",
    "jonivor", "qush", "ilon", "hasharot", "baliq",
    "qoziqorin", "other",
]

IUCNStatus = Literal["CR", "EN", "VU", "NT", "LC", "DD", "NE"]


@dataclass(slots=True)
class Photo:
    url: str
    thumb: str | None = None
    attribution: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class Taxonomy:
    kingdom: str | None = None
    phylum: str | None = None
    class_: str | None = None
    order: str | None = None
    family: str | None = None
    genus: str | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["class"] = d.pop("class_")
        return d


# ======================================================================
# Species — canonical representation across the app
# ======================================================================

@dataclass(slots=True)
class SpeciesRef:
    """Minimal species reference — from any source."""
    source: Literal["local", "inat", "gbif"]
    source_id: str
    name: str                           # o'zbekcha / common
    latin: str                          # scientific
    category: Category = "other"
    rank: str | None = None
    photo: Photo | None = None
    iucn_status: IUCNStatus | None = None
    observations_count: int | None = None
    redbook: bool = False

    def to_dict(self) -> dict:
        d = asdict(self)
        if self.photo:
            d["photo"] = self.photo.to_dict()
        return d


@dataclass(slots=True)
class SpeciesDetail(SpeciesRef):
    """Full species card — descriptions + taxonomy + safety."""
    description: str = ""
    uses: str = ""
    warnings: str = ""
    first_aid: str = ""
    habitat: str = ""
    regions: str = ""
    taxonomy: Taxonomy = field(default_factory=Taxonomy)
    photos: list[Photo] = field(default_factory=list)
    wikipedia_url: str | None = None
    fine_bhm_min: int | None = None
    fine_bhm_max: int | None = None
    law_article: str | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        if self.photo:
            d["photo"] = self.photo.to_dict()
        d["photos"] = [p.to_dict() for p in (self.photos or [])]
        d["taxonomy"] = self.taxonomy.to_dict()
        return d


# ======================================================================
# Identification (scan) result
# ======================================================================

@dataclass(slots=True)
class IdCandidate:
    name: str
    latin: str
    confidence: float
    why: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class IdentificationResult:
    found: bool
    primary: SpeciesDetail | None = None
    confidence: float = 0.0
    alternatives: list[IdCandidate] = field(default_factory=list)
    key_features: str = ""
    reason: str = ""        # if not found
    model_used: str = ""    # which vision model produced result
    fallback: bool = False  # did we fall back to local DB pick?

    def to_dict(self) -> dict:
        return {
            "found": self.found,
            "fallback": self.fallback,
            "confidence": self.confidence,
            "key_features": self.key_features,
            "species": self.primary.to_dict() if self.primary else None,
            "alternatives": [a.to_dict() for a in self.alternatives],
            "reason": self.reason or None,
            "model": self.model_used or None,
        }


# ======================================================================
# Enrichment (chat + wiki + AI)
# ======================================================================

@dataclass(slots=True)
class WikiSummary:
    title: str
    extract: str
    url: str
    lang: str
    thumbnail: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class EnrichmentResult:
    """Merged info — Wikipedia + AI for a species."""
    name: str
    latin: str
    description: str = ""
    uses: str = ""
    warnings: str = ""
    first_aid: str = ""
    wikipedia: WikiSummary | None = None

    def to_dict(self) -> dict:
        d = {
            "name": self.name,
            "latin": self.latin,
            "description": self.description,
            "uses": self.uses,
            "warnings": self.warnings,
            "first_aid": self.first_aid,
            "wikipedia": self.wikipedia.to_dict() if self.wikipedia else None,
        }
        return d
