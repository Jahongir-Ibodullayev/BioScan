"""Reseed shop with outdoor-only catalog after external_url field added."""
from django.db import migrations


def reseed(apps, schema_editor):
    from django.core.management import call_command
    try:
        call_command("seed_shop", "--reset")
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("outdoor reseed failed: %s", e)


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0004_add_external_url"),
    ]

    operations = [
        migrations.RunPython(reseed, reverse_noop),
    ]
