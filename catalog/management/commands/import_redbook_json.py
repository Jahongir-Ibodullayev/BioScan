"""`python manage.py import_redbook_json <file.json>` — Qizil kitob turlarini JSON'dan import.

JSON format: ro'yxat (list) elementlar, har biri Species maydonlari bilan.
Mavjud turlar update qilinadi (slug bo'yicha), yangilari yaratiladi.
"""
import json
from django.core.management.base import BaseCommand, CommandError

from catalog.models import Species


# Species modelidagi haqiqiy maydonlar — bularga noma'lum kalitlar bermasdan filtrlaymiz
ALLOWED_FIELDS = {
    "slug", "name", "latin", "category", "icon_name", "color_class",
    "summary", "description", "habitat", "uses", "warnings", "first_aid",
    "image_url", "red_book", "iucn_status", "regions", "external_ref",
    "halal_status", "is_medicinal", "is_honey_plant", "livestock_danger",
    "is_edible", "bloom_months", "harvest_months",
    "fine_bhm_min", "fine_bhm_max", "law_article",
}


class Command(BaseCommand):
    help = "Qizil kitob turlarini JSON fayldan import qilish (100+ tur uchun)"

    def add_arguments(self, parser):
        parser.add_argument("file", help="JSON fayl yo'li (list of species dicts)")
        parser.add_argument("--dry-run", action="store_true",
                            help="DB'ga yozmasdan, faqat sanayman")

    def handle(self, *args, **opts):
        path = opts["file"]
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            raise CommandError(f"Fayl topilmadi: {path}")
        except json.JSONDecodeError as e:
            raise CommandError(f"JSON xato: {e}")

        if not isinstance(data, list):
            raise CommandError("JSON ro'yxat (list) bo'lishi shart")

        created = updated = skipped = 0
        for i, item in enumerate(data, 1):
            if not isinstance(item, dict):
                self.stdout.write(self.style.WARNING(f"  [{i}] dict emas, o'tkazib yuboramiz"))
                skipped += 1
                continue
            slug = item.get("slug")
            if not slug:
                self.stdout.write(self.style.WARNING(f"  [{i}] slug yo'q, o'tkazib yuboramiz"))
                skipped += 1
                continue

            # Faqat ruxsat etilgan maydonlarni qoldiramiz
            payload = {k: v for k, v in item.items() if k in ALLOWED_FIELDS and k != "slug"}
            # red_book har doim True (bu Qizil kitob import)
            payload.setdefault("red_book", True)

            if opts["dry_run"]:
                exists = Species.objects.filter(slug=slug).exists()
                self.stdout.write(f"  [{i}] {'UPDATE' if exists else 'CREATE'} {slug}")
                continue

            obj, was_created = Species.objects.update_or_create(
                slug=slug, defaults=payload,
            )
            if was_created:
                created += 1
            else:
                updated += 1

        if opts["dry_run"]:
            self.stdout.write(self.style.SUCCESS(
                f"DRY-RUN: {len(data)} ta yozuv tahlil qilindi, hech narsa yozilmadi"
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"✓ Import: {created} yangi, {updated} yangilangan, {skipped} o'tkazilgan"
            ))
            total = Species.objects.filter(red_book=True).count()
            self.stdout.write(f"  Bazada jami Qizil kitob turlari: {total}")
