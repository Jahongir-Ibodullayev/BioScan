"""Global species search — iNaturalist + Wikipedia proxies.

iNaturalist API: https://api.inaturalist.org/v1/docs/
  - 150K+ tur, millionlab georeferenced rasmli kuzatuvlar
  - Auth kerak emas
  - Rate limit: 10K req/day

Wikipedia REST: https://en.wikipedia.org/api/rest_v1/
  - Tavsif + rasm
"""
from __future__ import annotations

import requests
from django.core.cache import cache
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .uz_vocab import resolve_uz

INAT = "https://api.inaturalist.org/v1"
GBIF = "https://api.gbif.org/v1"
WIKI_UZ = "https://uz.wikipedia.org/api/rest_v1"
WIKI_EN = "https://en.wikipedia.org/api/rest_v1"
UA = "TogAI/1.0 (https://togai.uz; info@togai.uz)"
TIMEOUT = 12

# GBIF Kingdom key'lari (taxonKey)
GBIF_KINGDOM = {
    "plant":  6,   # Plantae
    "animal": 1,   # Animalia
    "fungi":  5,   # Fungi
    "bact":   3,   # Bacteria
    "virus":  8,   # Viruses
    "chrom":  7,   # Chromista
    "proto":  2,   # Protozoa
    "arch":   4,   # Archaea
    "giyoh":  6, "daraxt": 6, "gul": 6,
    "jonivor":1, "qush": 1, "ilon": 1, "hasharot": 1, "baliq": 1,
    "qoziqorin": 5,
}

# O'zbekiston place_id iNaturalist'da
UZBEKISTAN_PLACE_ID = 7352

# Bizning kategoriyalar → iNaturalist iconic_taxa
CATEGORY_MAP = {
    "plant":    "Plantae",
    "giyoh":    "Plantae",
    "daraxt":   "Plantae",
    "gul":      "Plantae",
    "animal":   "Mammalia",
    "jonivor":  "Mammalia",
    "bird":     "Aves",
    "qush":     "Aves",
    "reptile":  "Reptilia",
    "ilon":     "Reptilia",
    "insect":   "Insecta",
    "hasharot": "Insecta",
    "fish":     "Actinopterygii",
    "baliq":    "Actinopterygii",
    "fungi":    "Fungi",
    "qoziqorin":"Fungi",
    "amphibia": "Amphibia",
    "spider":   "Arachnida",
}

# IUCN conservation status kodlari
IUCN_REDBOOK = ["CR", "EN", "VU", "NT"]  # Critically / Endangered / Vulnerable / Near Threatened


import hashlib as _hashlib
import json as _json


def _safe_cache_key(namespace: str, path: str, params: dict) -> str:
    """Memcached-safe cache key — hash long/complex parts, no spaces."""
    raw = _json.dumps([path, sorted(params.items())], sort_keys=True, default=str)
    return f"{namespace}:{_hashlib.sha1(raw.encode()).hexdigest()[:16]}"


def _inat_get(path: str, params: dict) -> dict:
    key = _safe_cache_key("inat", path, params)
    cached = cache.get(key)
    if cached:
        return cached
    r = requests.get(f"{INAT}{path}", params=params, headers={"User-Agent": UA}, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    cache.set(key, data, 60 * 30)  # 30 min
    return data


def _gbif_get(path: str, params: dict) -> dict:
    key = _safe_cache_key("gbif", path, params)
    cached = cache.get(key)
    if cached:
        return cached
    r = requests.get(f"{GBIF}{path}", params=params, headers={"User-Agent": UA}, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    cache.set(key, data, 60 * 60)  # 1 hour
    return data


def _inat_photo_for(canonical_name: str) -> tuple[str | None, str | None]:
    """Return (photo_url, thumb_url) for a scientific name via iNat lookup.
    Falls back to genus if species not found. Cached 24h."""
    if not canonical_name:
        return None, None
    key = _safe_cache_key("inatphoto", canonical_name.lower(), {})
    cached = cache.get(key)
    if cached is not None:
        return cached or (None, None)

    # Try exact, then genus fallback
    candidates = [canonical_name]
    parts = canonical_name.split()
    if len(parts) >= 2:
        candidates.append(parts[0])  # genus only

    for q in candidates:
        try:
            r = requests.get(
                f"{INAT}/taxa",
                params={"q": q, "per_page": 1, "is_active": "true"},
                headers={"User-Agent": UA},
                timeout=6,
            )
            r.raise_for_status()
            results = r.json().get("results") or []
            if results and results[0].get("default_photo"):
                photo_obj = results[0]["default_photo"]
                photo = photo_obj.get("medium_url") or photo_obj.get("original_url")
                thumb = photo_obj.get("square_url") or photo_obj.get("medium_url")
                if photo:
                    out = (photo, thumb)
                    cache.set(key, out, 60 * 60 * 24)
                    return out
        except requests.RequestException:
            continue

    cache.set(key, "", 60 * 60)  # negative cache 1h
    return None, None


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def taxa_search(request):
    """GET /api/search/taxa/?q=yantoq&per_page=20&locale=uz

    Uzbek-first search:
      1. If q is a Uzbek folk name (lola, yantoq, isiriq...) → translate to Latin
      2. Query iNaturalist with Latin OR rank=species filter to avoid bugs with 'lola' (species epithet)
      3. Override common_name with Uzbek from vocab
    """
    q_original = request.GET.get("q", "").strip()
    if not q_original:
        return Response({"detail": "q parametri majburiy"}, status=status.HTTP_400_BAD_REQUEST)

    per_page = min(int(request.GET.get("per_page", 20)), 50)
    locale = request.GET.get("locale", "uz")

    # 1) Uzbek → Latin translation
    resolved = resolve_uz(q_original)
    q_effective = resolved["latin"] if resolved else q_original
    is_uz_translated = bool(resolved)

    # 2) Query iNaturalist — if we translated, restrict to species rank to avoid
    #    random epithet collisions like "Antiblemma lola" when user searched "lola"
    params = {
        "q": q_effective,
        "per_page": per_page,
        "locale": locale,
        "all_names": "true",
        "is_active": "true",
    }
    if is_uz_translated:
        params["rank"] = "species,genus"

    try:
        data = _inat_get("/taxa", params)
    except requests.RequestException as e:
        return Response({"detail": f"iNaturalist: {e}"}, status=status.HTTP_502_BAD_GATEWAY)

    # Build a quick reverse-lookup dict from UZ vocab (latin → uz)
    from .uz_vocab import resolve_latin

    results = []
    for t in data.get("results", []):
        photo = t.get("default_photo") or {}
        latin_name = t.get("name") or ""

        # Override common name with Uzbek if available
        uz_override = resolve_latin(latin_name)
        common_uz = uz_override["uz"] if uz_override else None

        results.append({
            "id": t.get("id"),
            "name": latin_name,
            "preferred_common_name": common_uz or t.get("preferred_common_name") or t.get("english_common_name"),
            "rank": t.get("rank"),
            "iconic_taxon_name": t.get("iconic_taxon_name"),
            "observations_count": t.get("observations_count"),
            "wikipedia_url": t.get("wikipedia_url"),
            "thumb": photo.get("square_url") or photo.get("medium_url"),
            "photo": photo.get("medium_url") or photo.get("original_url"),
            "attribution": photo.get("attribution"),
        })

    # 3) Relevance filter: if UZ translated, keep only results where genus matches
    if is_uz_translated and q_effective:
        target_genus = q_effective.split()[0].lower()
        ranked = []
        others = []
        for r in results:
            if r["name"].split()[0].lower() == target_genus:
                ranked.append(r)
            else:
                others.append(r)
        # Sort by observations_count within ranked (popularity)
        ranked.sort(key=lambda r: r.get("observations_count") or 0, reverse=True)
        results = ranked + others

    return Response({
        "total": data.get("total_results"),
        "translated": is_uz_translated,
        "query_effective": q_effective,
        "results": results,
    })


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def taxon_detail(request, taxon_id: int):
    """GET /api/search/taxa/<id>/   — to'liq ma'lumot"""
    try:
        data = _inat_get(f"/taxa/{taxon_id}", {"locale": request.GET.get("locale", "uz")})
    except requests.RequestException as e:
        return Response({"detail": f"iNaturalist: {e}"}, status=status.HTTP_502_BAD_GATEWAY)

    results = data.get("results") or []
    if not results:
        return Response({"detail": "Topilmadi"}, status=status.HTTP_404_NOT_FOUND)

    t = results[0]
    photos = [
        {
            "url": p.get("photo", {}).get("medium_url") or p.get("photo", {}).get("original_url"),
            "attribution": p.get("photo", {}).get("attribution"),
        }
        for p in (t.get("taxon_photos") or [])[:8]
        if p.get("photo", {}).get("medium_url")
    ]
    default = t.get("default_photo") or {}
    return Response({
        "id": t.get("id"),
        "name": t.get("name"),
        "preferred_common_name": t.get("preferred_common_name") or t.get("english_common_name"),
        "rank": t.get("rank"),
        "iconic_taxon_name": t.get("iconic_taxon_name"),
        "observations_count": t.get("observations_count"),
        "conservation_status": (t.get("conservation_status") or {}).get("status_name"),
        "wikipedia_url": t.get("wikipedia_url"),
        "wikipedia_summary": t.get("wikipedia_summary"),
        "photo": default.get("medium_url") or default.get("original_url"),
        "photos": photos,
        "ancestors": [{"id": a.get("id"), "name": a.get("name"), "rank": a.get("rank")} for a in t.get("ancestors", [])],
    })


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def nearest_observations(request):
    """GET /api/search/observations/?taxon_id=X&lat=Y&lng=Z&radius=100&per_page=30

    iNaturalist'dan eng yaqin kuzatuvlarni qaytaradi (koordinatlar + rasm).
    """
    taxon_id = request.GET.get("taxon_id")
    if not taxon_id:
        return Response({"detail": "taxon_id majburiy"}, status=status.HTTP_400_BAD_REQUEST)

    params = {
        "taxon_id": taxon_id,
        "per_page": min(int(request.GET.get("per_page", 30)), 100),
        "order_by": "observed_on",
        "order": "desc",
        "photos": "true",
        "geo": "true",
        "quality_grade": "research,needs_id",
    }
    lat = request.GET.get("lat")
    lng = request.GET.get("lng")
    radius = request.GET.get("radius")  # km
    if lat and lng:
        params["lat"] = lat
        params["lng"] = lng
        if radius:
            params["radius"] = radius

    try:
        data = _inat_get("/observations", params)
    except requests.RequestException as e:
        return Response({"detail": f"iNaturalist: {e}"}, status=status.HTTP_502_BAD_GATEWAY)

    observations = []
    for o in data.get("results", []):
        # location: "lat,lng" string
        loc = o.get("location") or ""
        try:
            olat, olng = [float(x) for x in loc.split(",")]
        except (ValueError, AttributeError):
            continue
        photos = o.get("photos") or []
        observations.append({
            "id": o.get("id"),
            "lat": olat,
            "lng": olng,
            "observed_on": o.get("observed_on"),
            "place_guess": o.get("place_guess"),
            "user": ((o.get("user") or {}).get("login")),
            "photo": (photos[0].get("url", "").replace("square", "medium") if photos else None),
            "quality_grade": o.get("quality_grade"),
            "url": f"https://www.inaturalist.org/observations/{o.get('id')}",
        })
    return Response({"total": data.get("total_results"), "observations": observations})


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def browse(request):
    """GET /api/search/browse/?category=plant&redbook=true&place=uz&q=yantoq&per_page=30

    Yagona endpoint — iNaturalist'dan kategoriya/qizil kitob/joy bo'yicha turlarni qaytaradi.

    Parametrlar:
      category: plant | animal | bird | reptile | insect | fish | fungi
                yoki UZ: giyoh, jonivor, qush, ilon, hasharot, baliq, qoziqorin
      redbook:  "true" → faqat IUCN himoyalangan (CR/EN/VU/NT)
      place:    "uz" → faqat O'zbekiston turlarini
      q:        matnli qidiruv (ixtiyoriy)
      per_page: 1..50 (default 30)
      locale:   uz | ru | en (default uz)
    """
    per_page = min(int(request.GET.get("per_page", 30)), 50)
    locale = request.GET.get("locale", "uz")
    cat = (request.GET.get("category") or "").lower().strip()
    iconic = CATEGORY_MAP.get(cat)
    is_redbook = (request.GET.get("redbook") or "").lower() in ("true", "1", "yes")
    is_uz = (request.GET.get("place") or "").lower() in ("uz", "uzbekistan")
    q = (request.GET.get("q") or "").strip()

    iconic_to_cat = {v: k for k, v in CATEGORY_MAP.items()
                     if k in ("plant", "animal", "bird", "reptile", "insect", "fish", "fungi")}

    # Joy yoki Qizil kitob bo'lsa — /observations/species_counts (iNat shunday ishlaydi)
    if is_redbook or is_uz:
        params: dict = {
            "per_page": per_page,
            "locale": locale,
            "quality_grade": "research,needs_id",
        }
        if is_redbook:
            params["threatened"] = "true"
        if is_uz:
            params["place_id"] = UZBEKISTAN_PLACE_ID
        if iconic:
            params["iconic_taxa"] = iconic
        if q:
            params["q"] = q
        try:
            data = _inat_get("/observations/species_counts", params)
        except requests.RequestException as e:
            return Response({"detail": f"iNaturalist: {e}"}, status=status.HTTP_502_BAD_GATEWAY)

        results = []
        for row in data.get("results", []):
            t = row.get("taxon") or {}
            photo = t.get("default_photo") or {}
            cs = (t.get("conservation_status") or {})
            it = t.get("iconic_taxon_name") or ""
            results.append({
                "id": t.get("id"),
                "name": t.get("name"),
                "common_name": t.get("preferred_common_name") or t.get("english_common_name"),
                "rank": t.get("rank"),
                "iconic_taxon": it,
                "category": iconic_to_cat.get(it, "other"),
                "observations_count": row.get("count"),
                "iucn_status": (cs.get("status") or "").upper() or None,
                "iucn_label": cs.get("status_name") or None,
                "redbook": True,
                "wikipedia_url": t.get("wikipedia_url"),
                "thumb": photo.get("square_url") or photo.get("medium_url"),
                "photo": photo.get("medium_url") or photo.get("original_url"),
                "attribution": photo.get("attribution"),
            })
        return Response({
            "total": data.get("total_results"),
            "filters": {"category": cat or None, "redbook": is_redbook,
                        "place": "uz" if is_uz else None, "q": q or None},
            "source": "inat/observations/species_counts",
            "results": results,
        })

    # Umumiy: /taxa endpoint
    params = {
        "per_page": per_page,
        "locale": locale,
        "all_names": "true",
        "is_active": "true",
        "rank": request.GET.get("rank", "species"),
        "order_by": "observations_count",
        "order": "desc",
    }
    if iconic:
        params["iconic_taxa"] = iconic
    if is_uz:
        params["place_id"] = UZBEKISTAN_PLACE_ID
    if q:
        params["q"] = q

    try:
        data = _inat_get("/taxa", params)
    except requests.RequestException as e:
        return Response({"detail": f"iNaturalist: {e}"}, status=status.HTTP_502_BAD_GATEWAY)

    results = []
    for t in data.get("results", []):
        photo = t.get("default_photo") or {}
        cs = (t.get("conservation_status") or {})
        it = t.get("iconic_taxon_name") or ""
        status_code = (cs.get("status") or "").upper() or None
        results.append({
            "id": t.get("id"),
            "name": t.get("name"),
            "common_name": t.get("preferred_common_name") or t.get("english_common_name"),
            "rank": t.get("rank"),
            "iconic_taxon": it,
            "category": iconic_to_cat.get(it, "other"),
            "observations_count": t.get("observations_count"),
            "iucn_status": status_code,
            "iucn_label": cs.get("status_name") or None,
            "redbook": bool(status_code and status_code in IUCN_REDBOOK),
            "wikipedia_url": t.get("wikipedia_url"),
            "thumb": photo.get("square_url") or photo.get("medium_url"),
            "photo": photo.get("medium_url") or photo.get("original_url"),
            "attribution": photo.get("attribution"),
        })
    return Response({
        "total": data.get("total_results"),
        "filters": {"category": cat or None, "redbook": False,
                    "place": "uz" if is_uz else None, "q": q or None},
        "source": "inat/taxa",
        "results": results,
    })


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def gbif_search(request):
    """GET /api/search/gbif/?q=alhagi&category=plant&limit=30

    GBIF — eng yirik global taksonomiya bazasi (2.5M+ tur).
    iNaturalist'dan 6× katta, lekin foto kamroq.
    """
    q = (request.GET.get("q") or "").strip()
    limit = min(int(request.GET.get("limit", 30)), 100)
    cat = (request.GET.get("category") or "").lower().strip()

    params = {
        "q": q,
        "rank": request.GET.get("rank", "species"),
        "limit": limit,
        "offset": int(request.GET.get("offset", 0)),
        "status": "ACCEPTED",
    }
    if cat and cat in GBIF_KINGDOM:
        params["kingdomKey"] = GBIF_KINGDOM[cat]
    if not q:
        params.pop("q")

    try:
        data = _gbif_get("/species/search", params)
    except requests.RequestException as e:
        return Response({"detail": f"GBIF: {e}"}, status=status.HTTP_502_BAD_GATEWAY)

    results = []
    for t in data.get("results", []):
        vernaculars = t.get("vernacularNames") or []
        ver_uz = next((v.get("vernacularName") for v in vernaculars if v.get("language") == "uzb"), None)
        ver_ru = next((v.get("vernacularName") for v in vernaculars if v.get("language") == "rus"), None)
        ver_en = next((v.get("vernacularName") for v in vernaculars if v.get("language") == "eng"), None)
        canonical = t.get("canonicalName") or t.get("scientificName")

        # Enrich with iNaturalist photo (cached)
        photo, thumb = _inat_photo_for(canonical)

        results.append({
            "key": t.get("key") or t.get("nubKey"),
            "name": t.get("scientificName") or canonical,
            "canonical": canonical,
            "kingdom": t.get("kingdom"),
            "phylum": t.get("phylum"),
            "class": t.get("class"),
            "order": t.get("order"),
            "family": t.get("family"),
            "genus": t.get("genus"),
            "rank": t.get("rank"),
            "common_uz": ver_uz,
            "common_ru": ver_ru,
            "common_en": ver_en or t.get("vernacularName"),
            "authorship": t.get("authorship"),
            "num_occurrences": t.get("numOccurrences"),
            "taxonomic_status": t.get("taxonomicStatus"),
            "photo": photo,
            "thumb": thumb,
        })
    return Response({
        "total": data.get("count"),
        "limit": data.get("limit"),
        "offset": data.get("offset"),
        "source": "gbif/species/search",
        "results": results,
    })


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def gbif_detail(request, taxon_key: int):
    """GET /api/search/gbif/<key>/ — bitta turning barcha ma'lumotlari GBIF'dan."""
    try:
        sp = _gbif_get(f"/species/{taxon_key}", {})
        media = _gbif_get(f"/species/{taxon_key}/media", {"limit": 10})
        desc = _gbif_get(f"/species/{taxon_key}/descriptions", {"limit": 5})
        vernaculars = _gbif_get(f"/species/{taxon_key}/vernacularNames", {"limit": 30})
    except requests.RequestException as e:
        return Response({"detail": f"GBIF: {e}"}, status=status.HTTP_502_BAD_GATEWAY)

    ver_by_lang = {}
    for v in vernaculars.get("results", []):
        lang = v.get("language")
        if lang and lang not in ver_by_lang:
            ver_by_lang[lang] = v.get("vernacularName")

    return Response({
        "key": sp.get("key"),
        "name": sp.get("scientificName"),
        "canonical": sp.get("canonicalName"),
        "authorship": sp.get("authorship"),
        "rank": sp.get("rank"),
        "status": sp.get("taxonomicStatus"),
        "kingdom": sp.get("kingdom"),
        "phylum": sp.get("phylum"),
        "class": sp.get("class"),
        "order": sp.get("order"),
        "family": sp.get("family"),
        "genus": sp.get("genus"),
        "common_uz": ver_by_lang.get("uzb"),
        "common_ru": ver_by_lang.get("rus"),
        "common_en": ver_by_lang.get("eng"),
        "all_vernaculars": ver_by_lang,
        "descriptions": [
            {"source": r.get("source"), "type": r.get("type"), "text": r.get("description")}
            for r in (desc.get("results") or [])
        ],
        "photos": [
            {"url": m.get("identifier"), "title": m.get("title"),
             "creator": m.get("creator"), "license": m.get("license")}
            for m in (media.get("results") or []) if m.get("identifier")
        ],
    })


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def gbif_occurrences(request):
    """GET /api/search/gbif/occurrences/?taxonKey=X&country=UZ&limit=30"""
    params = {
        "taxonKey": request.GET.get("taxonKey"),
        "country": (request.GET.get("country") or "UZ").upper(),
        "hasCoordinate": "true",
        "hasGeospatialIssue": "false",
        "limit": min(int(request.GET.get("limit", 30)), 100),
        "mediaType": "StillImage",
    }
    if not params["taxonKey"]:
        return Response({"detail": "taxonKey majburiy"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        data = _gbif_get("/occurrence/search", params)
    except requests.RequestException as e:
        return Response({"detail": f"GBIF: {e}"}, status=status.HTTP_502_BAD_GATEWAY)

    occs = []
    for o in data.get("results", []):
        media = o.get("media") or []
        occs.append({
            "key": o.get("key"),
            "lat": o.get("decimalLatitude"),
            "lng": o.get("decimalLongitude"),
            "country": o.get("country"),
            "locality": o.get("locality") or o.get("stateProvince"),
            "eventDate": o.get("eventDate"),
            "photo": (media[0].get("identifier") if media else None),
            "basis": o.get("basisOfRecord"),
        })
    return Response({"total": data.get("count"), "results": occs})


def _wiki_one(lang: str, title: str) -> dict | None:
    """Fetch Wikipedia summary in one language."""
    base = WIKI_UZ if lang == "uz" else (WIKI_EN if lang == "en" else f"https://{lang}.wikipedia.org/api/rest_v1")
    key = _safe_cache_key("wiki", f"{lang}:{title}", {})
    cached = cache.get(key)
    if cached is not None:
        return cached or None
    try:
        r = requests.get(f"{base}/page/summary/{title}",
                         headers={"User-Agent": UA}, timeout=TIMEOUT)
        if r.status_code == 404:
            cache.set(key, "", 60 * 60)
            return None
        r.raise_for_status()
        w = r.json()
        data = {
            "title": w.get("title"),
            "extract": w.get("extract"),
            "thumbnail": (w.get("thumbnail") or {}).get("source"),
            "url": (w.get("content_urls", {}).get("desktop") or {}).get("page"),
            "lang": lang,
        }
        cache.set(key, data, 60 * 60 * 6)
        return data
    except requests.RequestException:
        return None


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def enrich(request):
    """GET /api/search/enrich/?name=Alhagi%20pseudalhagi&common=Yantoq

    Rich species info: Wikipedia (uz/ru/en cascade) + AI-generated
    structured summary (tavsif, foydasi, xavfi, birinchi yordam).
    """
    name = (request.GET.get("name") or "").strip()
    common = (request.GET.get("common") or "").strip()
    category = (request.GET.get("category") or "").strip()
    if not name:
        return Response({"detail": "name majburiy"}, status=status.HTTP_400_BAD_REQUEST)

    cache_key = _safe_cache_key("enrich", f"{name}|{common}|{category}", {})
    cached = cache.get(cache_key)
    if cached:
        return Response(cached)

    # 1. Wikipedia (multi-language cascade)
    wiki = None
    for lang, title in [("uz", common or name), ("ru", common or name),
                        ("en", name), ("en", common)]:
        if not title:
            continue
        w = _wiki_one(lang, title.replace(" ", "_"))
        if w and w.get("extract"):
            wiki = w
            break

    # 2. AI structured summary (tavsif/foydasi/xavfi/birinchi yordam)
    from togai.integrations import groq_chat

    # Strong taxonomic framing — prevents "Mallard = train" hallucinations
    category_hint = {
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
    }.get(category, category or "JONZOT (living organism)")

    context_lines = [
        f"Ilmiy (lotincha) nom: {name}",
        f"Taksonomik kategoriya: {category_hint}",
    ]
    if common and common.lower() != name.lower():
        context_lines.append(f"Ingliz/xalq nomi: {common}")
    if wiki and wiki.get("extract"):
        context_lines.append(f"\nWikipedia'dan olingan haqiqiy ma'lumot:\n{wiki['extract'][:1000]}")

    context = "\n".join(context_lines)

    system = (
        "Sen Tog'AI yordamchisisan — FAQAT biologiya/tabiat ekspertisan. "
        "Sen BIOLOGIK TURLAR haqida yozasan — o'simlik, hayvon, qush, baliq, hasharot, qo'ziqorin. "
        "HECH QACHON texnika, mashina, poyezd, mahsulot, brend haqida yozma — "
        "xalq nomi poyezd/mashina bilan bir xil bo'lsa ham, bu BIOLOGIK TUR haqida gap ketyapti. "
        "Faqat Wikipedia'dagi haqiqiy biologik ma'lumotdan foydalan. "
        "Bilmasang — 'Ma'lumot yetarli emas' deb yoz. Yolg'on/taxmin yozma."
    )

    prompt = (
        f"Quyidagi BIOLOGIK TUR (tabiat obyekti) haqida O'ZBEK tilida yoz:\n\n"
        f"{context}\n\n"
        "=== KERAKLI FORMAT ===\n"
        "4 bo'limda qisqa (2-3 jumla) javob yoz. Har bo'lim sarlavhasini aniq yoz:\n\n"
        "TAVSIF: bu tur nima (qanday jonzot), qayerda yashaydi/o'sadi, qanday ko'rinadi\n"
        "FOYDASI: odam yoki ekologiya uchun foydasi (ovqat, dori, iqtisod, tabiat muvozanati)\n"
        "XAVFI: zaharli? yirtqich? allergen? chorvaga xavfli? Agar xavf yo'q — 'Xavf aniqlanmagan' yoz\n"
        "BIRINCHI YORDAM: xavfli bo'lsa nima qilish kerak. Xavf yo'q bo'lsa — 'Kerak emas' yoz\n\n"
        "MUHIM: faqat BIOLOGIK ma'nosini ol. Agar lotincha nom {name} texnika nomi bilan bir xil bo'lsa, "
        "uni E'TIBORSIZ qoldir — bu tur biologik jonzot."
    )
    try:
        ai_text = groq_chat(prompt, system=system)
    except Exception:
        ai_text = ""

    sections = _parse_sections(ai_text)

    result = {
        "name": name,
        "common_name": common,
        "category": category,
        "wikipedia": wiki,
        "description": sections.get("tavsif") or (wiki.get("extract") if wiki else ""),
        "uses": sections.get("foydasi") or "",
        "warnings": sections.get("xavfi") or "",
        "first_aid": sections.get("birinchi_yordam") or "",
        "raw": ai_text,
    }
    cache.set(cache_key, result, 60 * 60 * 24)  # 24h — AI+Wiki data rarely changes
    return Response(result)


def _parse_sections(text: str) -> dict:
    """Parse AI response with TAVSIF: / FOYDASI: / XAVFI: / BIRINCHI YORDAM: markers."""
    if not text:
        return {}
    sections = {}
    current = None
    buf: list[str] = []
    markers = {
        "TAVSIF": "tavsif",
        "FOYDASI": "foydasi",
        "XAVFI": "xavfi",
        "BIRINCHI YORDAM": "birinchi_yordam",
    }
    for line in text.split("\n"):
        stripped = line.strip()
        found = None
        for m, key in markers.items():
            if stripped.upper().startswith(m + ":") or stripped.upper().startswith(m):
                found = key
                rest = stripped.split(":", 1)[1].strip() if ":" in stripped else ""
                break
        if found:
            if current and buf:
                sections[current] = "\n".join(buf).strip()
            current = found
            buf = [rest] if rest else []
        elif current:
            buf.append(line)
    if current and buf:
        sections[current] = "\n".join(buf).strip()
    return sections


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def wikipedia_summary(request):
    """GET /api/search/wiki/?title=Alhagi&lang=en"""
    title = request.GET.get("title", "").strip()
    lang = request.GET.get("lang", "en")
    if not title:
        return Response({"detail": "title majburiy"}, status=status.HTTP_400_BAD_REQUEST)

    base = WIKI_UZ if lang == "uz" else WIKI_EN
    key = _safe_cache_key("wiki", f"{lang}:{title}", {})
    cached = cache.get(key)
    if cached:
        return Response(cached)
    try:
        r = requests.get(f"{base}/page/summary/{title}", headers={"User-Agent": UA}, timeout=TIMEOUT)
        if r.status_code == 404:
            return Response({"detail": "Wikipedia'da topilmadi"}, status=status.HTTP_404_NOT_FOUND)
        r.raise_for_status()
        w = r.json()
    except requests.RequestException as e:
        return Response({"detail": f"Wikipedia: {e}"}, status=status.HTTP_502_BAD_GATEWAY)

    data = {
        "title": w.get("title"),
        "description": w.get("description"),
        "extract": w.get("extract"),
        "thumbnail": (w.get("thumbnail") or {}).get("source"),
        "original": (w.get("originalimage") or {}).get("source"),
        "url": (w.get("content_urls", {}).get("desktop") or {}).get("page"),
    }
    cache.set(key, data, 60 * 60 * 6)  # 6 hours
    return Response(data)
