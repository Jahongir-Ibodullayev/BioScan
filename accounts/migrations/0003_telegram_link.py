"""Telegram bot OTP — User'ga telegram_id va telegram_username qo'shish."""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_account_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="telegram_id",
            field=models.BigIntegerField(
                blank=True, db_index=True, null=True, unique=True,
                verbose_name="Telegram ID",
                help_text="Telegram chat_id — bot orqali OTP yuborish uchun",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="telegram_username",
            field=models.CharField(
                blank=True, max_length=64,
                verbose_name="Telegram username",
            ),
        ),
    ]
