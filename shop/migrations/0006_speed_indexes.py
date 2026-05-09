"""TZ §3.3 — Shop speed indekslar."""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0005_reseed_outdoor"),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                "CREATE INDEX IF NOT EXISTS idx_shop_active_featured ON shop_product(status, is_featured) WHERE status = 'active';",
                "CREATE INDEX IF NOT EXISTS idx_shop_active_category ON shop_product(category_id) WHERE status = 'active';",
            ],
            reverse_sql=[
                "DROP INDEX IF EXISTS idx_shop_active_featured;",
                "DROP INDEX IF EXISTS idx_shop_active_category;",
            ],
        ),
    ]
