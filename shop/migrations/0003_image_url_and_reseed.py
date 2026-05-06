"""Add Product.image_url + re-seed (with Unsplash URLs)."""
from django.db import migrations, models


def reseed(apps, schema_editor):
    from django.core.management import call_command
    try:
        # Mavjud demo seller mahsulotlarini o'chirib qaytadan to'ldirish
        call_command("seed_shop", "--reset")
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("seed_shop reset failed: %s", e)


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0002_seed_products"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="image_url",
            field=models.URLField(blank=True, help_text="Tashqi rasm URL", max_length=500),
        ),
        migrations.RunPython(reseed, reverse_noop),
    ]
