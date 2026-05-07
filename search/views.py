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
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response

from togai.throttles import AIEnrichThrottle, AIHelpThrottle

from .uz_vocab import resolve_uz

INAT = "https://api.inaturalist.org/v1"
GBIF = "https://api.gbif.org/v1"
WIKI_UZ = "https://uz.wikipedia.org/api/rest_v1"
WIKI_EN = "https://en.wikipedia.org/api/rest_v1"
UA = "BioScan/1.0 (https://togai.uz; info@togai.uz)"
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


def _int_query(query_params, name: str, default: int, *, min_value: int = 1,
               max_value: int | None = None) -> int:
    raw = query_params.get(name, default)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ValueError(f"{name} butun son bo'lishi kerak")
    if value < min_value:
        raise ValueError(f"{name} {min_value} dan kichik bo'lmasin")
    if max_value is not None:
        value = min(value, max_value)
    return value


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

    try:
        # 10 ta natija — chiroyli grid uchun (oldin 20 edi)
        per_page = _int_query(request.GET, "per_page", 10, max_value=20)
    except ValueError as e:
        return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    locale = request.GET.get("locale", "uz")

    # ===== DB-first search =====
    # Foydalanuvchi skan qilgan turlar lokal DB'da. Avval shu yerdan qidiramiz.
    # Topsa darhol qaytaramiz — iNat'ga so'rov yubormaymiz (tezroq + arzonroq).
    # 4+ harfli so'rovlardagina icontains, kalta so'rovlarda exact bo'lishi shart
    # (chunki "ot" — apricot, Otis, Bota, etc bilan urinmasin)
    try:
        from catalog.models import Species
        from django.db.models import Q
        if len(q_original) < 4:
            local = Species.objects.filter(
                Q(name__iexact=q_original) | Q(latin__iexact=q_original) | Q(slug__iexact=q_original)
            ).order_by("name")[:per_page]
        else:
            local = Species.objects.filter(
                Q(name__icontains=q_original)
                | Q(latin__icontains=q_original)
                | Q(slug__icontains=q_original)
            ).order_by("name")[:per_page]
        if local.exists():
            local_results = [
                {
                    "id": s.id,
                    "name": s.latin or s.name,
                    "preferred_common_name": s.name,
                    "rank": "species",
                    "iconic_taxon_name": "",
                    "observations_count": 0,
                    "wikipedia_url": s.external_ref or None,
                    "thumb": s.image_url or (s.image.url if s.image else None),
                    "photo": s.image_url or (s.image.url if s.image else None),
                    "attribution": "BioScan mahalliy bazasi",
                    "_source": "local",
                }
                for s in local
            ]
            return Response({
                "total": local.count(),
                "translated": False,
                "query_effective": q_original,
                "source": "local-db",
                "results": local_results,
            })
    except Exception:
        # Local DB ishlamasa — iNat'ga o'tamiz
        pass

    # 1) Uzbek → Latin translation: vocab + AI fallback
    resolved = resolve_uz(q_original)
    q_effective = resolved["latin"] if resolved else q_original
    is_uz_translated = bool(resolved)
    ai_translated = False

    # Vocab'da yo'q + so'rov o'zbekchaga o'xshasa → AI tarjimon
    if not resolved:
        try:
            from search.uz_vocab import looks_uzbek
            from togai.services.translate import uz_to_scientific
            if looks_uzbek(q_original):
                ai = uz_to_scientific(q_original)
                if ai:
                    # Ilmiy nom bo'lsa undan, bo'lmasa inglizcha umumiy nomdan
                    candidate = ai.get("scientific") or ai.get("english")
                    if candidate:
                        q_effective = candidate
                        is_uz_translated = True
                        ai_translated = True
        except Exception:
            pass

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

    # AI tarjima: faqat CACHE'dan o'qiymiz, yangi AI call qilmaymiz (tezlik!)
    # Detail sahifasida (taxon_detail) AI tarjima qilinadi va cache to'ldiriladi.
    try:
        from togai.services.translate import _cache_key, _looks_english
        from django.core.cache import cache as _cache
        for r in results:
            cn = r.get("preferred_common_name")
            if not cn:
                continue
            cached = _cache.get(_cache_key(cn, r.get("name") or ""))
            if cached and not _looks_english(cached):
                r["preferred_common_name"] = cached
            elif _looks_english(cn) and r.get("name"):
                # Cache yo'q + ingliz nom → Latin genus'ga tushiramiz (instant)
                r["preferred_common_name"] = r["name"].split()[0].lower()
    except Exception:
        pass

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

    # 10 tagacha — gridda chiroyli ko'rinishi uchun
    results = results[:per_page]

    # ===== 4) Wikipedia — 3-manba sifatida natija oz bo'lsa to'ldiradi =====
    # iNat har doim ham hamma narsani topavermaydi (mahalliy taom, urf-odat,
    # arxaik o'zbek atamalari). Wikipedia keng qamrovli — 3-manba.
    wiki_extras: list[dict] = []
    try:
        if len(results) < per_page:
            need = per_page - len(results)
            wiki_query = q_original  # asl o'zbek so'z bilan UZ wiki'da qidiramiz
            wiki_hits = _wiki_search_with_thumbs(wiki_query, limit=need)
            # Inglizcha tarjima ham bor bo'lsa — qo'shamiz (ko'proq variant)
            if ai_translated and len(wiki_hits) < need and q_effective != q_original:
                more = _wiki_search_with_thumbs(q_effective, limit=need - len(wiki_hits))
                seen = {h["title"].lower() for h in wiki_hits}
                for m in more:
                    if m["title"].lower() not in seen:
                        wiki_hits.append(m)

            # iNat bilan dedupe — title iNat natijalari nomi bilan bir xil bo'lsa yo'q
            inat_names = {(r.get("name") or "").lower() for r in results}
            inat_names |= {(r.get("preferred_common_name") or "").lower() for r in results}
            existing_ids: set[int] = set()
            for w in wiki_hits:
                if w["title"].lower() in inat_names:
                    continue
                wid = abs(hash(w.get("url") or w["title"])) % (10**9)
                if wid in existing_ids:
                    continue
                existing_ids.add(wid)
                wiki_extras.append({
                    "id": -wid,  # manfiy — Wikipedia kelib chiqishi belgisi
                    "name": w["title"],
                    "preferred_common_name": w["title"],
                    "rank": "wikipedia",
                    "iconic_taxon_name": "Wikipedia",
                    "observations_count": 0,
                    "wikipedia_url": w.get("url"),
                    "thumb": w.get("thumbnail"),
                    "photo": w.get("thumbnail"),
                    "extract": (w.get("extract") or "")[:160],
                    "_source": "wikipedia",
                    "_lang": w.get("lang"),
                })
            results = (results + wiki_extras)[:per_page]
    except Exception:
        # Wikipedia ishlamasa — katta gap emas, iNat natijalarini qaytaramiz
        pass

    return Response({
        "total": len(results),
        "translated": is_uz_translated,
        "ai_translated": ai_translated,
        "query_effective": q_effective,
        "sources": ["inat"] + (["wikipedia"] if wiki_extras else []),
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

    # UZ name resolution: vocab → AI translate fallback
    latin_n = t.get("name") or ""
    raw_common = t.get("preferred_common_name") or t.get("english_common_name")
    raw_summary = t.get("wikipedia_summary") or ""
    uz_common = raw_common
    uz_summary = raw_summary
    try:
        from .uz_vocab import resolve_latin
        from togai.services.translate import translate_one, ensure_uz, _looks_english
        ov = resolve_latin(latin_n)
        if ov:
            uz_common = ov["uz"]
        elif raw_common:
            uz_common = translate_one(raw_common, latin_n)
        # FINAL SAFETY: agar uz_common hali ham _looks_english → genus
        if uz_common and _looks_english(uz_common) and latin_n:
            uz_common = latin_n.split()[0].lower()

        # Wikipedia summary: iNat ingliz tilidagi summary'ni qaytaradi.
        # Yaxshiroq: UZ/RU/EN cascade orqali yaxshi extract topamiz.
        wiki_best = _fetch_wikipedia_best(latin_n, uz_common or raw_common or "")
        if wiki_best and wiki_best.get("extract"):
            extract = wiki_best["extract"]
            # Agar UZ emas bo'lsa, AI bilan tarjima
            if wiki_best.get("lang") != "uz":
                extract = ensure_uz(extract, kind="block")
            uz_summary = extract
        elif raw_summary:
            uz_summary = ensure_uz(raw_summary, kind="block")
            if uz_summary and _looks_english(uz_summary[:120]):
                uz_summary = ""
    except Exception:
        pass

    return Response({
        "id": t.get("id"),
        "name": latin_n,
        "preferred_common_name": uz_common,
        "rank": t.get("rank"),
        "iconic_taxon_name": t.get("iconic_taxon_name"),
        "observations_count": t.get("observations_count"),
        "conservation_status": (t.get("conservation_status") or {}).get("status_name"),
        "wikipedia_url": t.get("wikipedia_url"),
        "wikipedia_summary": uz_summary,
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
        "order_by": "observed_on",
        "order": "desc",
        "photos": "true",
        "geo": "true",
        "quality_grade": "research,needs_id",
    }
    try:
        params["per_page"] = _int_query(request.GET, "per_page", 30, max_value=100)
    except ValueError as e:
        return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    lat = request.GET.get("lat")
    lng = request.GET.get("lng")
    radius = request.GET.get("radius")  # km
    if lat and lng:
        params["lat"] = lat
        params["lng"] = lng
        if radius:
            params["radius"] = radius
    else:
        # Default UZ — boshqa hudud ishlatilmaganda Markaziy Osiyoga cheklanadi
        # (Ruddy Turnstone Iceland'da emas, Uzbekistan'da chiqsin)
        place = (request.GET.get("place") or "uz").lower()
        if place in ("uz", "uzbekistan"):
            params["place_id"] = UZBEKISTAN_PLACE_ID

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
    from .uz_vocab import resolve_uz, resolve_latin

    try:
        per_page = _int_query(request.GET, "per_page", 30, max_value=50)
    except ValueError as e:
        return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    locale = request.GET.get("locale", "uz")
    cat = (request.GET.get("category") or "").lower().strip()
    iconic = CATEGORY_MAP.get(cat)
    is_redbook = (request.GET.get("redbook") or "").lower() in ("true", "1", "yes")
    is_uz = (request.GET.get("place") or "").lower() in ("uz", "uzbekistan")
    q_original = (request.GET.get("q") or "").strip()

    # UZ-first: agar foydalanuvchi o'zbekcha so'rasa (lola, isiriq) — Latin nomga aylantiramiz
    resolved = resolve_uz(q_original) if q_original else None
    q = resolved["latin"] if resolved else q_original

    iconic_to_cat = {v: k for k, v in CATEGORY_MAP.items()
                     if k in ("plant", "animal", "bird", "reptile", "insect", "fish", "fungi")}

    def _uz_common(latin_name: str, fallback: str | None) -> str | None:
        """Latin → UZ common name (Peganum harmala → Isiriq). Topilmasa fallback'ni qaytaradi."""
        if not latin_name:
            return fallback
        ov = resolve_latin(latin_name)
        if ov:
            return ov["uz"]
        return fallback

    def _post_translate_results(rows: list[dict]) -> None:
        """Vocab'da topilmagan ingliz nomlarini AI orqali toplab tarjima qil (in-place)."""
        try:
            from togai.services.translate import translate_batch
        except Exception:
            return
        items = [(r.get("common_name") or "", r.get("name") or "")
                 for r in rows if r.get("common_name")]
        if not items:
            return
        try:
            tr = translate_batch(items)
            for r in rows:
                cn = r.get("common_name")
                if cn and cn in tr:
                    r["common_name"] = tr[cn]
        except Exception as e:
            import logging as _lg
            _lg.getLogger(__name__).warning("post-translate failed: %s", e)

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
            latin = t.get("name") or ""
            common = _uz_common(latin, t.get("preferred_common_name") or t.get("english_common_name"))
            results.append({
                "id": t.get("id"),
                "name": latin,
                "common_name": common,
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
        _post_translate_results(results)
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
        latin = t.get("name") or ""
        common = _uz_common(latin, t.get("preferred_common_name") or t.get("english_common_name"))
        results.append({
            "id": t.get("id"),
            "name": latin,
            "common_name": common,
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
    _post_translate_results(results)
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
    try:
        limit = _int_query(request.GET, "limit", 30, max_value=100)
        offset = _int_query(request.GET, "offset", 0, min_value=0)
    except ValueError as e:
        return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    cat = (request.GET.get("category") or "").lower().strip()

    params = {
        "q": q,
        "rank": request.GET.get("rank", "species"),
        "limit": limit,
        "offset": offset,
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
    try:
        limit = _int_query(request.GET, "limit", 30, max_value=100)
    except ValueError as e:
        return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    params = {
        "taxonKey": request.GET.get("taxonKey"),
        "country": (request.GET.get("country") or "UZ").upper(),
        "hasCoordinate": "true",
        "hasGeospatialIssue": "false",
        "limit": limit,
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


def _wiki_search(lang: str, query: str) -> str | None:
    """Wikipedia search API — bitta nomdan eng yaxshi article title topadi.

    `Arenaria interpres` → API qaytaradi: 'Ruddy turnstone' (sahifa nomi)
    """
    if not query:
        return None
    key = _safe_cache_key("wikisearch", f"{lang}:{query}", {})
    cached = cache.get(key)
    if cached is not None:
        return cached or None
    try:
        host = "https://uz.wikipedia.org" if lang == "uz" else f"https://{lang}.wikipedia.org"
        r = requests.get(
            f"{host}/w/api.php",
            params={
                "action": "query",
                "list": "search",
                "srsearch": query,
                "srlimit": 1,
                "format": "json",
            },
            headers={"User-Agent": UA},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        hits = data.get("query", {}).get("search") or []
        if hits:
            title = hits[0].get("title")
            if title:
                cache.set(key, title, 60 * 60 * 24)
                return title
        cache.set(key, "", 60 * 60)
        return None
    except requests.RequestException:
        return None


def _wiki_opensearch(lang: str, query: str, limit: int = 8) -> list[dict]:
    """Wikipedia opensearch — bir nechta titles qaytaradi, keyin har biriga summary.

    Tez: bitta API call bilan top-N titles, keyin parallel summary'lar.
    Faqat tabiat/biologiyaga oid sahifalarni qaytaradi (qisqa filter).
    """
    if not query or len(query) < 2:
        return []
    cache_key = _safe_cache_key("wikiopen", f"{lang}:{query}:{limit}", {})
    cached = cache.get(cache_key)
    if cached is not None:
        return cached or []
    try:
        host = "https://uz.wikipedia.org" if lang == "uz" else f"https://{lang}.wikipedia.org"
        # opensearch: 4 ta array — [query, titles, descriptions, urls]
        r = requests.get(
            f"{host}/w/api.php",
            params={
                "action": "opensearch",
                "search": query,
                "limit": limit,
                "format": "json",
                "namespace": 0,
            },
            headers={"User-Agent": UA},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, list) or len(data) < 4:
            cache.set(cache_key, [], 60 * 60)
            return []
        titles = data[1] or []
        descs = data[2] or []
        urls = data[3] or []
        results = []
        for i, title in enumerate(titles):
            results.append({
                "title": title,
                "desc": descs[i] if i < len(descs) else "",
                "url": urls[i] if i < len(urls) else "",
                "lang": lang,
            })
        cache.set(cache_key, results, 60 * 60 * 6)
        return results
    except requests.RequestException:
        return []


def _wiki_search_with_thumbs(query: str, limit: int = 5) -> list[dict]:
    """Wikipedia title + rasm + qisqa tavsif — UZ → RU → EN tartibida.

    Faqat birinchi til 2+ natija qaytarsa shu yerda to'xtaydi.
    """
    if not query:
        return []
    out: list[dict] = []
    seen_titles: set[str] = set()
    for lang in ("uz", "ru", "en"):
        if len(out) >= limit:
            break
        opensearch = _wiki_opensearch(lang, query, limit=limit)
        if not opensearch:
            continue
        # Har bir titleni cached summary bilan (rasm) boyitamiz
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=4) as ex:
            summaries = list(ex.map(lambda h: _wiki_one(lang, h["title"]), opensearch))
        for hit, summary in zip(opensearch, summaries):
            if len(out) >= limit:
                break
            tkey = hit["title"].lower()
            if tkey in seen_titles:
                continue
            seen_titles.add(tkey)
            out.append({
                "title": hit["title"],
                "extract": (summary or {}).get("extract") if summary else hit.get("desc"),
                "thumbnail": (summary or {}).get("thumbnail") if summary else None,
                "url": hit.get("url") or ((summary or {}).get("url") if summary else None),
                "lang": lang,
            })
    return out


def _fetch_wikipedia_best(name: str, common: str = "") -> dict | None:
    """Multi-strategy Wikipedia fetch: UZ → RU → EN, har xil title variantlari + search API.

    1. Try direct page lookup with common name + latin (UZ then RU then EN)
    2. If all fail, use Wikipedia search API to find best title
    3. Return first non-empty extract
    """
    candidates = []
    if common:
        candidates.append(common)
    if name:
        candidates.append(name)
        # Genus-only fallback (e.g., 'Arenaria' from 'Arenaria interpres')
        genus = name.split()[0]
        if genus and genus != name:
            candidates.append(genus)

    # Strategy 1: direct title lookup
    for lang in ["uz", "ru", "en"]:
        for title in candidates:
            if not title:
                continue
            w = _wiki_one(lang, title.replace(" ", "_"))
            if w and w.get("extract"):
                return w

    # Strategy 2: search API to find correct title, then fetch
    for lang in ["uz", "ru", "en"]:
        for q in candidates:
            if not q:
                continue
            found_title = _wiki_search(lang, q)
            if not found_title:
                continue
            w = _wiki_one(lang, found_title.replace(" ", "_"))
            if w and w.get("extract"):
                return w

    return None


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
@throttle_classes([AIHelpThrottle])
def ai_help(request):
    """GET /api/search/ai-help/?q=lola

    AI-powered search assistant. Called when main search returns empty/poor results.
    Returns Uzbek explanation + suggested Latin names + likely taxa.
    """
    q = (request.GET.get("q") or "").strip()
    if not q:
        return Response({"detail": "q majburiy"}, status=status.HTTP_400_BAD_REQUEST)

    # Check UZ vocab first (cheap)
    resolved = resolve_uz(q)
    if resolved:
        return Response({
            "source": "vocab",
            "query": q,
            "latin": resolved["latin"],
            "category": resolved["category"],
            "english": resolved["english"],
            "answer": f"«{q.title()}» — bu o'zbek xalq nomi. Ilmiy nomi: {resolved['latin']} "
                      f"({resolved['english']}). Kategoriyasi: {resolved['category']}.",
        })

    # Fallback to LLM — let AI try to identify the Uzbek name
    from togai.integrations import groq_chat

    cache_parts = ("aihelp", q.lower())
    cached = cache.get(_safe_cache_key(*cache_parts, {}))
    if cached:
        return Response(cached)

    system = (
        "Sen Markaziy Osiyo flora/faunasi ekspertisan. Foydalanuvchi o'zbek yoki boshqa tilda "
        "tur nomini yozdi. Sen JSON qaytar: {latin, category, english, answer}. "
        "'answer' — 2-3 jumla o'zbek tilida tavsif. Bilmasang answer: 'Aniq ma'lumot topilmadi'."
    )
    prompt = (
        f"Foydalanuvchi qidirayapti: «{q}»\n\n"
        f"Bu qaysi o'simlik yoki jonivor bo'lishi mumkin? Faqat JSON qaytar:\n"
        f'{{"latin": "Ilmiy lotin nomi", "category": "giyoh|daraxt|gul|jonivor|qush|ilon|hasharot|qoziqorin", '
        f'"english": "English common name", "answer": "2-3 jumla o\'zbekcha tavsif"}}'
    )
    try:
        raw = groq_chat(prompt, system=system, temperature=0.2, max_tokens=400)
        import json as _json
        # Extract JSON from response
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            parsed = _json.loads(raw[start:end])
            result = {"source": "ai", "query": q, **parsed}
            cache.set(_safe_cache_key(*cache_parts, {}), result, 60 * 60 * 24)
            return Response(result)
    except Exception:
        pass

    return Response({
        "source": "none",
        "query": q,
        "answer": f"«{q}» haqida aniq ma'lumot topilmadi. Boshqa nom yoki rasm yuboring.",
    })


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
@throttle_classes([AIEnrichThrottle])
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

    # 1. Wikipedia (multi-strategy: UZ → RU → EN + search API fallback)
    wiki = _fetch_wikipedia_best(name, common)

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
        "Sen BioScan yordamchisisan — FAQAT biologiya/tabiat ekspertisan. "
        "BIOLOGIK TURLAR haqida yozasan — o'simlik, hayvon, qush, baliq, hasharot, qo'ziqorin. "
        "Asosiy QOIDA: Quyida berilgan Wikipedia matnidan foydalan. "
        "Wikipedia'da yo'q narsani O'YLAB CHIQARMA. "
        "Foydalanuvchining xavfsizligi muhim — zaharli/xavfli xususiyatlarni faqat asosli bo'lsa yoz. "
        "HECH QACHON texnika/mashina/poyezd/brend haqida yozma — bu jonzot. "
        "Bilmasang — 'Ma'lumot yetarli emas' deb yoz. Yolg'on yozish FOYDALANUVCHILAR HAYOTIGA XAVFLI."
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

    # Description: AI'ning TAVSIF bo'limi → Wikipedia extract → "Ma'lumot kam"
    ai_desc = sections.get("tavsif") or ""
    wiki_extract = wiki.get("extract") if wiki else ""

    # AI bo'sh yoki "yetarli emas" desa, Wikipedia matnini birinchi tanlanadigan qil
    if not ai_desc or "yetarli emas" in ai_desc.lower() or "ma'lumot yo'q" in ai_desc.lower():
        description = wiki_extract or ai_desc
    else:
        # AI tavsif + Wikipedia kontekst (agar Wiki uzunroq bo'lsa)
        description = ai_desc
        if wiki_extract and len(wiki_extract) > len(ai_desc) * 1.5:
            description = wiki_extract  # Wikipedia ko'proq ma'lumotli

    if not description:
        description = f"Bu {category_hint.lower()} haqida hozircha to'liq ma'lumot to'planmagan. Ilmiy nomi: {name}."

    uses = sections.get("foydasi") or ""
    warnings = sections.get("xavfi") or ""
    first_aid = sections.get("birinchi_yordam") or ""
    common_uz = common

    # Universal Uzbek garant: agar biror maydon ingliz/rus bo'lsa, AI tarjima
    try:
        from togai.services.translate import ensure_uz
        if description:
            description = ensure_uz(description, kind="block")
        if uses:
            uses = ensure_uz(uses, kind="auto")
        if warnings:
            warnings = ensure_uz(warnings, kind="auto")
        if first_aid:
            first_aid = ensure_uz(first_aid, kind="auto")
        if common_uz:
            common_uz = ensure_uz(common_uz, kind="name")
    except Exception:
        pass

    result = {
        "name": name,
        "common_name": common_uz,
        "category": category,
        "wikipedia": wiki,
        "description": description,
        "uses": uses,
        "warnings": warnings,
        "first_aid": first_aid,
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
    if lang not in {"uz", "ru", "en"}:
        return Response({"detail": "lang faqat uz, ru yoki en bo'lishi mumkin"}, status=status.HTTP_400_BAD_REQUEST)

    base = WIKI_UZ if lang == "uz" else (WIKI_EN if lang == "en" else "https://ru.wikipedia.org/api/rest_v1")
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
