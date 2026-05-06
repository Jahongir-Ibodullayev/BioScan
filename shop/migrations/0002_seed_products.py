"""Auto-seed: 100+ generik mahsulotlarni har deployda yaratadi (idempotent).

Foydalanish: avtomatik — `migrate` paytida ishlaydi.
Reset uchun: python manage.py seed_shop --reset
"""
from django.db import migrations


def forwards(apps, schema_editor):
    """Seed shop with products by calling the management command logic."""
    from django.core.management import call_command
    try:
        call_command("seed_shop")
    except Exception as e:
        # Migrationda xato bo'lsa logga yozamiz, lekin deploy buzmaymiz
        import logging
        logging.getLogger(__name__).warning("seed_shop failed: %s", e)


def reverse(apps, schema_editor):
    # Reverse — yaratilgan demo seller'lar mahsulotlarini o'chirib tashlash
    Product = apps.get_model("shop", "Product")
    Product.objects.filter(seller__phone__startswith="+99890000").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(forwards, reverse),
    ]
