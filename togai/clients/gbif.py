"""GBIF client — api.gbif.org/v1

Docs: https://www.gbif.org/developer/summary
No auth required. Rate limits: lenient.

Responsibility: HTTP + parsing only.
"""
from __future__ import annotations

from togai.core.cache import get_or_set
from togai.core.schemas import Photo, SpeciesRef, Taxonomy

from . import inat
from ._http import get_json

BASE = "https://api.gbif.org/v1"

# GBIF kingdomKey → our category hint
KINGDOM_KEY = {
    "plant":  6,   # Plantae
    "giyoh":  6, "daraxt": 6, "gul": 6,
    "animal": 1, "jonivor": 1, "qush": 1, "ilon": 1, "hasharot": 1, "baliq": 1,
    "fungi":  5, "qoziqorin": 5,
    "bact":   3,
    "virus":  8,
    "proto":  2,
}


def _kingdom_to_category(kingdom: str | None) -> str:
    return {
        "Plantae": "giyoh",
        "Animalia": "jonivor",
        "Fungi": "qoziqorin",
    }.get(kingdom or "", "other")


def search(q: str, *, category: str | None = None, limit: int = 30,
           offset: int = 0, rank: str = "species") -> tuple[int, list[dict]]:
    """Raw GBIF search — returns (total, records). Use detail() for one.

    Returns dicts (not SpeciesRef) because GBIF has more taxonomic fields
    than our generic SpeciesRef can hold.
    """
    params: dict = {
        "rank": rank,
        "limit": min(limit, 100),
        "offset": offset,
        "status": "ACCEPTED",
    }
    if q:
        params["q"] = q
    if category and category in KINGDOM_KEY:
        params["kingdomKey"] = KINGDOM_KEY[category]

    def _load():
        return get_json(f"{BASE}/species/search", params=params)

    data = get_or_set("gbif:search", tuple(sorted(params.items())), _load, ttl=60 * 60)
    return data.get("count", 0), data.get("results", [])


def detail(taxon_key: int) -> dict:
    """Full species info — species + media + descriptions + vernacular."""
    def _load_species():
        return get_json(f"{BASE}/species/{taxon_key}")

    def _load_media():
        return get_json(f"{BASE}/species/{taxon_key}/media", params={"limit": 10})

    def _load_desc():
        return get_json(f"{BASE}/species/{taxon_key}/descriptions", params={"limit": 5})

    def _load_vern():
        return get_json(f"{BASE}/species/{taxon_key}/vernacularNames", params={"limit": 50})

    sp = get_or_set("gbif:species", (taxon_key,), _load_species, ttl=60 * 60 * 6)
    media = get_or_set("gbif:media", (taxon_key,), _load_media, ttl=60 * 60 * 6)
    desc = get_or_set("gbif:desc", (taxon_key,), _load_desc, ttl=60 * 60 * 6)
    vern = get_or_set("gbif:vern", (taxon_key,), _load_vern, ttl=60 * 60 * 6)

    return {"species": sp, "media": media, "descriptions": desc, "vernacular": vern}


def to_species_ref(raw: dict) -> SpeciesRef:
    """Map GBIF species dict → SpeciesRef. Photo enriched from iNat fallback."""
    canonical = raw.get("canonicalName") or raw.get("scientificName") or ""
    vernaculars = raw.get("vernacularNames") or []

    def _lang(code: str) -> str | None:
        return next((v.get("vernacularName") for v in vernaculars
                     if v.get("language") == code), None)

    name = _lang("uzb") or _lang("rus") or _lang("eng") or raw.get("vernacularName") or canonical

    photo = inat.find_photo_for(canonical)

    return SpeciesRef(
        source="gbif",
        source_id=str(raw.get("key") or raw.get("nubKey") or ""),
        name=name,
        latin=raw.get("scientificName") or canonical,
        category=_kingdom_to_category(raw.get("kingdom")),
        rank=raw.get("rank"),
        photo=photo,
        observations_count=raw.get("numOccurrences"),
    )


def to_taxonomy(raw: dict) -> Taxonomy:
    return Taxonomy(
        kingdom=raw.get("kingdom"),
        phylum=raw.get("phylum"),
        class_=raw.get("class"),
        order=raw.get("order"),
        family=raw.get("family"),
        genus=raw.get("genus"),
    )


def occurrences(taxon_key: int, *, country: str = "UZ", limit: int = 30) -> list[dict]:
    def _load():
        data = get_json(f"{BASE}/occurrence/search", params={
            "taxonKey": taxon_key,
            "country": country.upper(),
            "hasCoordinate": "true",
            "hasGeospatialIssue": "false",
            "limit": min(limit, 100),
            "mediaType": "StillImage",
        })
        results = []
        for o in data.get("results", []):
            media = o.get("media") or []
            results.append({
                "key": o.get("key"),
                "lat": o.get("decimalLatitude"),
                "lng": o.get("decimalLongitude"),
                "country": o.get("country"),
                "locality": o.get("locality") or o.get("stateProvince"),
                "eventDate": o.get("eventDate"),
                "photo": media[0].get("identifier") if media else None,
                "basis": o.get("basisOfRecord"),
            })
        return results

    return get_or_set("gbif:occ", (taxon_key, country, limit), _load, ttl=60 * 60)
