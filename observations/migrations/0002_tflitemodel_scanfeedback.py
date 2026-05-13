"""TFLite model + scan feedback — chain'ni tiklash uchun qayta yozildi."""
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("observations", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TFLiteModel",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=40, unique=True, verbose_name="Nomi")),
                ("version", models.CharField(max_length=20, verbose_name="Versiya")),
                ("file", models.FileField(upload_to="tflite/", verbose_name="Fayl (.tflite)")),
                ("size_bytes", models.BigIntegerField(default=0, verbose_name="Hajm (bayt)")),
                ("sha256", models.CharField(blank=True, max_length=64, verbose_name="SHA-256")),
                ("classes_url", models.URLField(blank=True, help_text="Sinflar ro'yxati: {id: species_slug}", max_length=600, verbose_name="Sinflar JSON URL")),
                ("accuracy", models.FloatField(default=0.85, verbose_name="Aniqlik")),
                ("is_active", models.BooleanField(db_index=True, default=False, verbose_name="Faol")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "TFLite model",
                "verbose_name_plural": "TFLite modellar",
                "ordering": ("-created_at",),
            },
        ),
        migrations.CreateModel(
            name="ScanFeedback",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("predicted_slug", models.CharField(blank=True, max_length=140, verbose_name="Predicted")),
                ("correct_slug", models.CharField(blank=True, max_length=140, verbose_name="Foydalanuvchi tuzatdi")),
                ("is_correct", models.BooleanField(default=True, verbose_name="To'g'rimi?")),
                ("note", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("observation", models.ForeignKey(blank=True, null=True, on_delete=models.deletion.CASCADE, related_name="feedback", to="observations.observation")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, related_name="scan_feedback", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Scan feedback",
                "verbose_name_plural": "Scan feedbacks",
                "ordering": ("-created_at",),
            },
        ),
    ]
