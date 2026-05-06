from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="account_type",
            field=models.CharField(
                choices=[
                    ("customer", "Mijoz"),
                    ("seller", "Sotuvchi"),
                    ("super_admin", "Super admin"),
                ],
                default="customer",
                max_length=20,
                verbose_name="Hisob turi",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="seller_name",
            field=models.CharField(blank=True, max_length=120, verbose_name="Do'kon nomi"),
        ),
        migrations.AddField(
            model_name="user",
            name="seller_bio",
            field=models.TextField(blank=True, verbose_name="Sotuvchi haqida"),
        ),
        migrations.AddField(
            model_name="user",
            name="seller_verified",
            field=models.BooleanField(default=False, verbose_name="Sotuvchi tasdiqlangan"),
        ),
    ]
