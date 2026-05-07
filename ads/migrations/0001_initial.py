from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Ad",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("title", models.CharField(help_text="Ichki nom — foydalanuvchi ko'rmaydi", max_length=140, verbose_name="Sarlavha")),
                ("image", models.ImageField(blank=True, help_text="Tavsiya: 1080×1920 (splash), 800×400 (banner)", null=True, upload_to="ads/", verbose_name="Rasm")),
                ("image_url", models.URLField(blank=True, help_text="Yoki tashqi CDN'dan", max_length=600, verbose_name="Tashqi rasm URL")),
                ("headline", models.CharField(blank=True, max_length=80, verbose_name="Bosh matni")),
                ("body", models.CharField(blank=True, max_length=200, verbose_name="Tana matni")),
                ("cta_text", models.CharField(blank=True, default="Batafsil", max_length=40, verbose_name="Tugma matni")),
                ("target_url", models.URLField(blank=True, help_text="Foydalanuvchi tugmani bossa shu URL ochiladi", verbose_name="Bossa qaerga")),
                ("slot", models.CharField(choices=[("splash", "Splash (kirish ekrani)"), ("banner", "Banner (Home pastida)"), ("inline", "Inline (postlar orasida)"), ("bot", "Telegram bot welcome")], default="splash", max_length=12, verbose_name="Slot")),
                ("platform", models.CharField(choices=[("all", "Hammasiga"), ("web", "Faqat webapp"), ("apk", "Faqat APK"), ("bot", "Faqat bot")], default="all", max_length=8, verbose_name="Platforma")),
                ("is_active", models.BooleanField(default=True, verbose_name="Faol")),
                ("starts_at", models.DateTimeField(default=django.utils.timezone.now, verbose_name="Boshlanish")),
                ("ends_at", models.DateTimeField(blank=True, help_text="Bo'sh = cheksiz", null=True, verbose_name="Tugash")),
                ("priority", models.IntegerField(default=0, help_text="Yuqori son birinchi ko'rinadi", verbose_name="Ustuvorlik")),
                ("duration_seconds", models.IntegerField(default=4, help_text="Foydalanuvchi qancha sekund ko'radi (skip 2s'dan keyin)", verbose_name="Ko'rsatish vaqti")),
                ("skippable_after", models.IntegerField(default=2, verbose_name="Skip vaqti")),
                ("impressions", models.IntegerField(default=0, verbose_name="Ko'rishlar")),
                ("clicks", models.IntegerField(default=0, verbose_name="Bosishlar")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Reklama",
                "verbose_name_plural": "Reklamalar",
                "ordering": ("-priority", "-created_at"),
                "indexes": [
                    models.Index(fields=["slot", "is_active"], name="ads_slot_active_idx"),
                    models.Index(fields=["platform", "is_active"], name="ads_platform_active_idx"),
                ],
            },
        ),
    ]
