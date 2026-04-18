from django.conf import settings
from django.db import models


class IncidentCategory(models.TextChoices):
    SNAKE = "ilon", "Ilon / chayon"
    PREDATOR = "yirtqich", "Yirtqich jonivor"
    FALL = "yiqilish", "Qoyadan yiqilish"
    FIRE = "yongin", "Yong'in"
    POISONING = "zaharlanish", "Zaharlanish"
    OTHER = "boshqa", "Boshqa"


class Severity(models.TextChoices):
    LOW = "past", "Past"
    MEDIUM = "orta", "O'rta"
    HIGH = "yuqori", "Yuqori"


class IncidentStatus(models.TextChoices):
    NEW = "yangi", "Yangi"
    REVIEWING = "korib_chiqilmoqda", "Ko'rib chiqilmoqda"
    RESOLVED = "yechildi", "Yechildi"


class Incident(models.Model):
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incidents",
    )
    code = models.CharField(max_length=12, unique=True, blank=True)
    category = models.CharField(max_length=20, choices=IncidentCategory.choices)
    severity = models.CharField(
        max_length=8, choices=Severity.choices, default=Severity.MEDIUM
    )
    status = models.CharField(
        max_length=20, choices=IncidentStatus.choices, default=IncidentStatus.NEW
    )
    note = models.TextField(blank=True)
    photo = models.ImageField(upload_to="incidents/", null=True, blank=True)

    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    place_name = models.CharField(max_length=200, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Hodisa"
        verbose_name_plural = "Hodisalar"

    def save(self, *args, **kwargs):
        if not self.code:
            import random
            self.code = f"TAI-{random.randint(10000, 99999)}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} · {self.get_category_display()}"
