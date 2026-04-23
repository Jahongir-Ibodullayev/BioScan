"""iNaturalist client — typed wrapper around api.inaturalist.org/v1.

Docs: https://api.inaturalist.org/v1/docs/
Rate limit: 10k req/day, no auth required.

Responsibility: HTTP + parsing. No business logic.
"""
from __future__ import annotations

from togai.core.cache import get_or_set
from togai.core.schemas import Category, Photo, SpeciesRef

from ._http import get_json

BASE = "https://api.inaturalist.org/v1"
PLACE_UZ = 7352

# iconic_taxon_name → our Category
_ICONIC_MAP: dict[str, Category] = {
    "Plantae":         "giyoh",
    "Mammalia":        "jonivor",
    "Animalia":        "jonivor",
    "Aves":            "qush",
    "Reptilia":        "ilon",
    "Amphibia":        "jonivor",
    "Insecta":         "hasharot",
    "Arachnida":       "hasharot",
    "Actinopterygii":  "baliq",
    "Fungi":           "qoziqorin",
    "Mollusca":        "jonivor",
}

# Our internal category → iconic taxa used by iNat
CATEGORY_TO_ICONIC: dict[str, str] = {
    "plant": "Plantae", "giyoh": "Plantae", "daraxt": "Plantae", "gul": "Plantae",
    "animal": "Mammalia", "jonivor": "Mammalia",
    "bird": "Aves", "qush": "Aves",
    "reptile": "Reptilia", "ilon": "Reptilia",
    "insect": "Insecta", "hasharot": "Insecta",
    "fish": "Actinopterygii", "baliq": "Actinopterygii",
    "fungi": "Fungi", "qoziqorin": "Fungi",
}


def _to_ref(raw: dict, *, source_id_field: str = "id") -> SpeciesRef:
    photo_obj = raw.get("default_photo") or {}
    cs = raw.get("conservation_status") or {}
    status = (cs.get("status") or "").upper() or None
    iconic = raw.get("iconic_taxon_name") or ""
    photo: Photo | None = None
    if photo_obj.get("medium_url") or photo_obj.get("original_url"):
        photo = Photo(
            url=photo_obj.get("medium_url") or photo_obj.get("original_url"),
            thumb=photo_obj.get("square_url") or photo_obj.get("medium_url"),
            attribution=photo_obj.get("attribution"),
        )
    return SpeciesRef(
        source="inat",
        source_id=str(raw.get(source_id_field)),
        name=(raw.get("preferred_common_name")
              or raw.get("english_common_name")
              or raw.get("name", "")),
        latin=raw.get("name", ""),
        category=_ICONIC_MAP.get(iconic, "other"),
        rank=raw.get("rank"),
        photo=photo,
        iucn_status=status if status in ("CR", "EN", "VU", "NT", "LC", "DD", "NE") else None,
        observations_count=raw.get("observations_count"),
        redbook=bool(status and status in ("CR", "EN", "VU", "NT")),
    )


def search_taxa(q: str, *, per_page: int = 20, locale: str = "uz") -> list[SpeciesRef]:
    def _load():
        data = get_json(f"{BASE}/taxa", params={
            "q": q, "per_page": min(per_page, 50),
            "locale": locale, "is_active": "true", "all_names": "true",
        })
        return [_to_ref(r) for r in data.get("results", [])]

    return get_or_set("inat:taxa", (q, per_page, locale), _load, ttl=60 * 30)


def get_taxon(taxon_id: int, *, locale: str = "uz") -> dict:
    def _load():
        return get_json(f"{BASE}/taxa/{taxon_id}", params={"locale": locale})
    return get_or_set("inat:taxon", (taxon_id, locale), _load, ttl=60 * 60)


def browse(
    *,
    category: str | None = None,
    redbook: bool = False,
    place_uz: bool = False,
    q: str | None = None,
    per_page: int = 30,
    locale: str = "uz",
) -> tuple[int, list[SpeciesRef]]:
    """Unified browse — auto-picks right iNat endpoint."""
    iconic = CATEGORY_TO_ICONIC.get(category or "")
    cache_parts = (category, redbook, place_uz, q, per_page, locale)

    def _load():
        if redbook or place_uz:
            # species_counts — by observations
            params: dict = {
                "per_page": min(per_page, 50),
                "locale": locale,
                "quality_grade": "research,needs_id",
            }
            if redbook:
                params["threatened"] = "true"
            if place_uz:
                params["place_id"] = PLACE_UZ
            if iconic:
                params["iconic_taxa"] = iconic
            if q:
                params["q"] = q
            data = get_json(f"{BASE}/observations/species_counts", params=params)
            refs = []
            for row in data.get("results", []):
                t = row.get("taxon") or {}
                ref = _to_ref(t)
                ref.observations_count = row.get("count")
                if redbook:
                    ref.redbook = True
                refs.append(ref)
            return data.get("total_results") or len(refs), refs
        else:
            params = {
                "per_page": min(per_page, 50),
                "locale": locale,
                "all_names": "true", "is_active": "true",
                "rank": "species",
                "order_by": "observations_count", "order": "desc",
            }
            if iconic:
                params["iconic_taxa"] = iconic
            if q:
                params["q"] = q
            data = get_json(f"{BASE}/taxa", params=params)
            refs = [_to_ref(r) for r in data.get("results", [])]
            return data.get("total_results") or len(refs), refs

    return get_or_set("inat:browse", cache_parts, _load, ttl=60 * 30)


def find_photo_for(canonical_name: str) -> Photo | None:
    """Lookup a photo for a scientific name. Tries exact, then genus fallback."""
    if not canonical_name:
        return None

    def _load() -> Photo | None:
        candidates = [canonical_name]
        parts = canonical_name.split()
        if len(parts) >= 2:
            candidates.append(parts[0])  # genus fallback
        for q in candidates:
            try:
                results = get_json(f"{BASE}/taxa", params={
                    "q": q, "per_page": 1, "is_active": "true"
                }).get("results") or []
            except Exception:
                continue
            if results and results[0].get("default_photo"):
                po = results[0]["default_photo"]
                url = po.get("medium_url") or po.get("original_url")
                if url:
                    return Photo(
                        url=url,
                        thumb=po.get("square_url") or url,
                        attribution=po.get("attribution"),
                    )
        return None

    return get_or_set("inat:photo", (canonical_name.lower(),), _load, ttl=60 * 60 * 24)


def nearest_observations(taxon_id: int, *, lat: float, lng: float,
                         radius_km: int = 500, per_page: int = 30) -> list[dict]:
    def _load():
        data = get_json(f"{BASE}/observations", params={
            "taxon_id": taxon_id,
            "lat": lat, "lng": lng, "radius": radius_km,
            "per_page": min(per_page, 100),
            "photos": "true", "geo": "true",
            "order_by": "observed_on", "order": "desc",
            "quality_grade": "research,needs_id",
        })
        obs = []
        for o in data.get("results", []):
            loc = o.get("location") or ""
            try:
                olat, olng = [float(x) for x in loc.split(",")]
            except (ValueError, AttributeError):
                continue
            photos = o.get("photos") or []
            obs.append({
                "id": o.get("id"),
                "lat": olat, "lng": olng,
                "observed_on": o.get("observed_on"),
                "place_guess": o.get("place_guess"),
                "user": (o.get("user") or {}).get("login"),
                "photo": (photos[0].get("url", "").replace("square", "medium")
                          if photos else None),
                "quality_grade": o.get("quality_grade"),
                "url": f"https://www.inaturalist.org/observations/{o.get('id')}",
            })
        return obs

    return get_or_set("inat:obs", (taxon_id, lat, lng, radius_km, per_page), _load, ttl=60 * 15)
