"""TZ §3.3 — Speed optimization: partial indekslar.

Kataloga eng ko'p so'rov red_book=true filter bilan keladi (Qizil kitob).
Partial index — faqat red_book=true rows uchun, juda kichik (~100 rows) va tez.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0004_alter_species_category_alter_species_halal_status_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                "CREATE INDEX IF NOT EXISTS idx_species_red_book_partial ON catalog_species(red_book) WHERE red_book = true;",
                "CREATE INDEX IF NOT EXISTS idx_species_category_active ON catalog_species(category);",
                "CREATE INDEX IF NOT EXISTS idx_species_iucn_status ON catalog_species(iucn_status);",
            ],
            reverse_sql=[
                "DROP INDEX IF EXISTS idx_species_red_book_partial;",
                "DROP INDEX IF EXISTS idx_species_category_active;",
                "DROP INDEX IF EXISTS idx_species_iucn_status;",
            ],
        ),
    ]
