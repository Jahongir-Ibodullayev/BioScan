from django.db import models


class MarkerType(models.TextChoices):
    PLANT = "plant", "Giyoh"
    DANGER = "danger", "Xavf"
    CAMP = "camp", "Dam olish"
    WATER = "water", "Suv"
    VIEWPOINT = "viewpoint", "Manzara"
    ROAD = "road", "Yo'l"


class MapMarker(models.Model):
    type = models.CharField(max_length=12, choices=MarkerType.choices)
    label = models.CharField(max_length=160)
    description = models.CharField(max_length=280, blank=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    region = models.CharField(max_length=120, blank=True)
    active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Xarita markeri"
        verbose_name_plural = "Xarita markerlari"
        ordering = ("type", "label")

    def __str__(self):
        return f"{self.label} ({self.get_type_display()})"
