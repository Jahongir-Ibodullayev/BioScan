from django.conf import settings
from django.db import models

from catalog.models import Species


class Observation(models.Model):
    """Foydalanuvchining AI-scan natijasi / qo'l bilan qo'shilgan kuzatuv."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="observations"
    )
    species = models.ForeignKey(
        Species, on_delete=models.SET_NULL, null=True, blank=True, related_name="observations"
    )
    photo = models.ImageField(upload_to="observations/", null=True, blank=True)
    ai_confidence = models.FloatField(default=0.0, help_text="0.0 - 1.0")
    note = models.TextField(blank=True)

    # Joylashuv
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    place_name = models.CharField(max_length=200, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Kuzatuv"
        verbose_name_plural = "Kuzatuvlar"

    def __str__(self):
        return f"{self.user} · {self.species or '—'} · {self.created_at:%Y-%m-%d}"
