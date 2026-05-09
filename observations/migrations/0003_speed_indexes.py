"""TZ §3.3 — Observations speed indekslar (xarita uchun)."""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("observations", "0002_tflitemodel_scanfeedback"),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                "CREATE INDEX IF NOT EXISTS idx_obs_geo ON observations_observation(latitude, longitude, created_at DESC);",
                "CREATE INDEX IF NOT EXISTS idx_obs_user_recent ON observations_observation(user_id, created_at DESC);",
            ],
            reverse_sql=[
                "DROP INDEX IF EXISTS idx_obs_geo;",
                "DROP INDEX IF EXISTS idx_obs_user_recent;",
            ],
        ),
    ]
