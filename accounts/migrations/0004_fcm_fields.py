"""User'ga FCM (Firebase Cloud Messaging) maydonlari qo'shish."""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_telegram_link"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="fcm_token",
            field=models.CharField(
                blank=True, db_index=True, max_length=255,
                verbose_name="FCM token",
                help_text="Firebase Cloud Messaging — push xabarlari uchun",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="fcm_platform",
            field=models.CharField(
                blank=True, max_length=20,
                verbose_name="Qurilma platformasi",
                help_text="android | ios | web",
            ),
        ),
    ]
