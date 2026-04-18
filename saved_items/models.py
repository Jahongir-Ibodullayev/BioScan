from django.conf import settings
from django.db import models

from catalog.models import Species


class SavedSpecies(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_species"
    )
    species = models.ForeignKey(Species, on_delete=models.CASCADE, related_name="saved_by")
    note = models.CharField(max_length=240, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "species")
        ordering = ("-created_at",)
        verbose_name = "Saqlangan tur"
        verbose_name_plural = "Saqlangan turlar"
