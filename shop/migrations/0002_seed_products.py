"""Auto-seed: 100+ generik mahsulotlarni har deployda yaratadi (idempotent).

Foydalanish: avtomatik — `migrate` paytida ishlaydi.
Reset uchun: python manage.py seed_shop --reset
"""
from django.db import migrations


def forwards(apps, schema_editor):
    """Kept for migration history.

    Real demo seed runs in 0003 after Product.image_url exists. Calling the
    current seed command here breaks fresh installs because that column is not
    present yet.
    """
    pass


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
