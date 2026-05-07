"""Import O'zbekiston Red Book species from iNaturalist into local DB.

Usage:
    python manage.py import_inat_redbook [--limit N] [--update]

Fetches threatened species observed in Uzbekistan (place_id=7352) via iNat
/observations/species_counts endpoint, then upserts into catalog.Species.
"""
from __future__ import annotations

import time

import requests
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from catalog.models import Species

INAT = "https://api.inaturalist.org/v1"
PLACE_UZ = 7352
UA = "BioScan/1.0 (https://togai.uz; info@togai.uz)"

ICONIC_TO_CAT = {
    "Plantae":         "giyoh",
    "Animalia":        "jonivor",
    "Mammalia":        "jonivor",
    "Aves":            "qush",
    "Reptilia":        "ilon",
    "Amphibia":        "jonivor",
    "Insecta":         "hasharot",
    "Arachnida":       "hasharot",
    "Actinopterygii":  "baliq",
    "Fungi":           "qoziqorin",
    "Mollusca":        "jonivor",
}

# IUCN → BHM fine ranges (bizning taxminiy tarif)
FINE_BY_IUCN = {
    "CR": (2000, 5000),
    "EN": (1000, 3000),
    "VU": (500, 1500),
    "NT": (100, 500),
    "LC": (0, 100),
}


class Command(BaseCommand):
    help = "Import UZ Red Book species from iNaturalist"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=200, help="Max species to import")
        parser.add_argument("--update", action="store_true", help="Update existing rows too")
        parser.add_argument("--dry", action="store_true", help="Don't write — just print")

    def handle(self, *args, **opts):
        limit = opts["limit"]
        update = opts["update"]
        dry = opts["dry"]

        self.stdout.write(f"Fetching {limit} threatened species for UZ from iNaturalist...")

        all_species = self._fetch_all(limit)
        self.stdout.write(f"Got {len(all_species)} species from iNat\n")

        created = 0
        updated = 0
        skipped = 0
        for row in all_species:
            taxon = row.get("taxon") or {}
            latin = (taxon.get("name") or "").strip()
            if not latin:
                skipped += 1
                continue

            slug = slugify(latin)
            photo_obj = taxon.get("default_photo") or {}
            cs = taxon.get("conservation_status") or {}
            iucn = (cs.get("status") or "").upper()[:4] or "NE"
            iconic = taxon.get("iconic_taxon_name") or ""

            defaults = {
                "name": (taxon.get("preferred_common_name") or taxon.get("english_common_name") or latin),
                "latin": latin,
                "category": ICONIC_TO_CAT.get(iconic, "giyoh"),
                "summary": cs.get("status_name") or f"IUCN: {iucn}",
                "description": f"iNaturalist'dan import qilindi · Taxon ID {taxon.get('id')}",
                "habitat": "O'zbekiston",
                "regions": "O'zbekiston",
                "image_url": photo_obj.get("medium_url") or photo_obj.get("original_url") or "",
                "red_book": iucn in ("CR", "EN", "VU", "NT"),
                "iucn_status": iucn,
            }
            # Optional extra fields if they exist on model
            for field_name in ("icon_name", "color_class"):
                if hasattr(Species, field_name):
                    defaults.setdefault(field_name, "leaf" if field_name == "icon_name" else "")

            if hasattr(Species, "fine_bhm_min"):
                fmin, fmax = FINE_BY_IUCN.get(iucn, (0, 0))
                defaults["fine_bhm_min"] = fmin
                defaults["fine_bhm_max"] = fmax
            if hasattr(Species, "law_article"):
                defaults["law_article"] = "O'zbekiston Qizil kitobi (2019)"

            if dry:
                self.stdout.write(f"  [dry] {iucn:3s} · {latin:40s} · {defaults['category']}")
                continue

            existing = Species.objects.filter(slug=slug).first()
            if existing:
                if update:
                    for k, v in defaults.items():
                        setattr(existing, k, v)
                    existing.save()
                    updated += 1
                else:
                    skipped += 1
            else:
                Species.objects.create(slug=slug, **defaults)
                created += 1

        self.stdout.write(self.style.SUCCESS(
            f"\n✓ Done: {created} created · {updated} updated · {skipped} skipped"
        ))

    def _fetch_all(self, limit: int):
        per_page = min(limit, 100)
        fetched: list = []
        page = 1
        while len(fetched) < limit:
            params = {
                "place_id": PLACE_UZ,
                "threatened": "true",
                "per_page": per_page,
                "page": page,
                "locale": "uz",
            }
            r = requests.get(
                f"{INAT}/observations/species_counts",
                params=params,
                headers={"User-Agent": UA},
                timeout=20,
            )
            r.raise_for_status()
            data = r.json()
            results = data.get("results") or []
            if not results:
                break
            fetched.extend(results)
            if len(results) < per_page:
                break
            page += 1
            time.sleep(0.5)  # be nice to iNat
        return fetched[:limit]
