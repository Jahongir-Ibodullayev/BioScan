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


# ============================================================
# TFLite offline model — APK ichida ishlaydigan AI
# ============================================================
class TFLiteModel(models.Model):
    """TFLite model versiyalari — admin yuklab qo'yadi, APK ilk ishga tushganda yuklab oladi."""

    name = models.CharField("Nomi", max_length=40, unique=True)
    version = models.CharField("Versiya", max_length=20)
    file = models.FileField("Fayl (.tflite)", upload_to="tflite/")
    size_bytes = models.BigIntegerField("Hajm (bayt)", default=0)
    sha256 = models.CharField("SHA-256", max_length=64, blank=True)
    classes_url = models.URLField(
        "Sinflar JSON URL", max_length=600, blank=True,
        help_text="Sinflar ro'yxati: {id: species_slug}",
    )
    accuracy = models.FloatField("Aniqlik", default=0.85)
    is_active = models.BooleanField("Faol", default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "TFLite model"
        verbose_name_plural = "TFLite modellar"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.name} v{self.version}"


class ScanFeedback(models.Model):
    """Foydalanuvchi scan natijasiga rating/correction beradi.

    Bu ma'lumotlar TFLite modelni qayta o'rgatish uchun ishlatiladi.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="scan_feedback",
    )
    observation = models.ForeignKey(
        Observation, on_delete=models.CASCADE, related_name="feedback",
        null=True, blank=True,
    )
    predicted_slug = models.CharField("Predicted", max_length=140, blank=True)
    correct_slug = models.CharField("Foydalanuvchi tuzatdi", max_length=140, blank=True)
    is_correct = models.BooleanField("To'g'rimi?", default=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Scan feedback"
        verbose_name_plural = "Scan feedbacks"
        ordering = ("-created_at",)

    def __str__(self):
        ok = "✓" if self.is_correct else "✗"
        return f"{ok} {self.predicted_slug} → {self.correct_slug}"
