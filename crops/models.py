"""Crop Advisor — ekin ma'lumotlar bazasi, viloyatlar, foydalanuvchi rejalari."""
from __future__ import annotations

from django.conf import settings
from django.db import models


class Crop(models.Model):
    """Bitta ekin/o'simlik haqida ma'lumot bazasi."""

    slug = models.SlugField("Slug", max_length=80, unique=True)
    name_uz = models.CharField("Nomi (UZ)", max_length=80)
    name_ru = models.CharField("Nomi (RU)", max_length=80, blank=True)
    name_lat = models.CharField("Lotincha nom", max_length=120, blank=True)
    category = models.CharField(
        "Kategoriya", max_length=20, default="sabzavot",
        help_text="sabzavot | meva | don | gul | dorivor",
    )
    icon_name = models.CharField(
        "Icon", max_length=40, default="leaf",
        help_text="Lucide icon kalit: leaf | carrot | apple | wheat | flower | sprout | tree-deciduous",
    )

    # Ekish parametrlari
    min_soil_temp_c = models.IntegerField("Min tuproq harorati °C", default=0)
    optimal_soil_temp_c = models.IntegerField("Optimal tuproq harorati °C", default=0)
    frost_sensitive = models.BooleanField("Sovuqdan zaif", default=False)
    plant_window_start_month = models.IntegerField("Ekish davri boshi (oy)", default=3)
    plant_window_end_month = models.IntegerField("Ekish davri oxiri", default=5)
    days_to_harvest_min = models.IntegerField("Hosilgacha kun (min)", default=80)
    days_to_harvest_max = models.IntegerField("Hosilgacha kun (max)", default=120)

    # Sug'orish
    water_freq_days = models.IntegerField("Sug'orish chastotasi (kun)", default=5)
    drought_tolerant = models.BooleanField("Quruqlikka chidamli", default=False)
    flood_tolerant = models.BooleanField("Suvga chidamli", default=False)

    # Tuproq va sharoit
    soil_type = models.CharField("Tuproq turi", max_length=80, default="qum-tuproq")
    ph_min = models.DecimalField("pH min", max_digits=3, decimal_places=1, default=6.0)
    ph_max = models.DecimalField("pH max", max_digits=3, decimal_places=1, default=7.0)
    sun_hours_min = models.IntegerField("Quyosh soatlari (min)", default=6)

    # Ko'rsatmalar
    soil_prep_uz = models.TextField("Tuproqni tayyorlash", blank=True)
    planting_method_uz = models.TextField("Ekish usuli", blank=True)
    care_tips_uz = models.TextField("Parvarish maslahati", blank=True)
    common_pests = models.TextField("Asosiy zararkunandalar", blank=True)

    # Naviar
    common_varieties = models.JSONField("Navlar", default=list, blank=True)

    image_url = models.URLField("Rasm URL", blank=True, max_length=600)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ekin"
        verbose_name_plural = "Ekinlar"
        ordering = ("name_uz",)
        indexes = [models.Index(fields=["category"])]

    def __str__(self):
        return f"{self.icon_emoji} {self.name_uz}"


class Region(models.Model):
    """O'zbekiston viloyati + iqlim normalari."""

    slug = models.SlugField(max_length=40, unique=True)
    name_uz = models.CharField("Nomi (UZ)", max_length=40)
    name_ru = models.CharField("Nomi (RU)", max_length=40, blank=True)
    # Bbox (lat min, lat max, lon min, lon max)
    lat_min = models.DecimalField(max_digits=8, decimal_places=4)
    lat_max = models.DecimalField(max_digits=8, decimal_places=4)
    lon_min = models.DecimalField(max_digits=8, decimal_places=4)
    lon_max = models.DecimalField(max_digits=8, decimal_places=4)
    # Climate norms
    avg_last_frost_doy = models.IntegerField(
        "Bahorgi oxirgi sovuq (yil kuni)", default=80,
    )
    avg_first_frost_doy = models.IntegerField(
        "Kuzgi birinchi sovuq (yil kuni)", default=290,
    )
    annual_rainfall_mm = models.IntegerField("Yillik yog'ingarchilik (mm)", default=300)

    class Meta:
        verbose_name = "Viloyat"
        verbose_name_plural = "Viloyatlar"
        ordering = ("name_uz",)

    def __str__(self):
        return self.name_uz

    def contains(self, lat: float, lon: float) -> bool:
        return (
            float(self.lat_min) <= lat <= float(self.lat_max)
            and float(self.lon_min) <= lon <= float(self.lon_max)
        )


class CropPlan(models.Model):
    """Foydalanuvchining ekish rejasi — keyin eslatma yuborish uchun."""

    IRRIGATION_CHOICES = [
        ("drip", "Tomchi"),
        ("sprinkler", "Yomg'irlash"),
        ("manual", "Qo'l"),
        ("none", "Yo'q"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="crop_plans",
    )
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE)
    lat = models.DecimalField(max_digits=8, decimal_places=4)
    lon = models.DecimalField(max_digits=8, decimal_places=4)
    irrigation = models.CharField(max_length=20, choices=IRRIGATION_CHOICES, default="manual")
    plot_size_m2 = models.IntegerField(null=True, blank=True)
    planned_plant_date = models.DateField()
    expected_harvest_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    notify = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Ekish rejasi"
        verbose_name_plural = "Ekish rejalari"
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["user", "-created_at"])]

    def __str__(self):
        return f"{self.user.phone} · {self.crop.name_uz} · {self.planned_plant_date}"
