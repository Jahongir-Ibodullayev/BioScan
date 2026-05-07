"""Image URL maxlength 200 → 600 (Wikipedia URL'lari uzun)."""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0002_species_bloom_months_species_fine_bhm_max_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="species",
            name="image_url",
            field=models.URLField(
                blank=True, max_length=600,
                help_text="Optional external image (Unsplash, Wikipedia)",
            ),
        ),
    ]
