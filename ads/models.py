"""Reklama (Ad) modeli — splash, banner, inline reklamalar.

Adminkadan boshqariladi. Webapp/APK/Bot uchun mos slot tanlanadi:
  - splash:  ilovaga kirgunda 3-5s ekran
  - banner:  Home pastida
  - inline:  postlar orasida
  - bot:     Telegram bot welcome ostida
"""
from __future__ import annotations

from django.db import models
from django.utils import timezone


class Ad(models.Model):
    SLOT_SPLASH = "splash"
    SLOT_BANNER = "banner"
    SLOT_INLINE = "inline"
    SLOT_BOT = "bot"
    SLOT_CHOICES = [
        (SLOT_SPLASH, "Splash (kirish ekrani)"),
        (SLOT_BANNER, "Banner (Home pastida)"),
        (SLOT_INLINE, "Inline (postlar orasida)"),
        (SLOT_BOT, "Telegram bot welcome"),
    ]

    PLATFORM_ALL = "all"
    PLATFORM_WEB = "web"
    PLATFORM_APK = "apk"
    PLATFORM_BOT = "bot"
    PLATFORM_CHOICES = [
        (PLATFORM_ALL, "Hammasiga"),
        (PLATFORM_WEB, "Faqat webapp"),
        (PLATFORM_APK, "Faqat APK"),
        (PLATFORM_BOT, "Faqat bot"),
    ]

    title = models.CharField("Sarlavha", max_length=140, help_text="Ichki nom — foydalanuvchi ko'rmaydi")

    # Tanasi
    image = models.ImageField(
        "Rasm", upload_to="ads/", null=True, blank=True,
        help_text="Tavsiya: 1080×1920 (splash), 800×400 (banner)",
    )
    image_url = models.URLField(
        "Tashqi rasm URL", max_length=600, blank=True,
        help_text="Yoki tashqi CDN'dan",
    )
    headline = models.CharField("Bosh matni", max_length=80, blank=True)
    body = models.CharField("Tana matni", max_length=200, blank=True)
    cta_text = models.CharField("Tugma matni", max_length=40, blank=True, default="Batafsil")
    target_url = models.URLField(
        "Bossa qaerga", blank=True,
        help_text="Foydalanuvchi tugmani bossa shu URL ochiladi",
    )

    # Joylashuv va platforma
    slot = models.CharField("Slot", max_length=12, choices=SLOT_CHOICES, default=SLOT_SPLASH)
    platform = models.CharField("Platforma", max_length=8, choices=PLATFORM_CHOICES, default=PLATFORM_ALL)

    # Vaqt va aktivlik
    is_active = models.BooleanField("Faol", default=True)
    starts_at = models.DateTimeField("Boshlanish", default=timezone.now)
    ends_at = models.DateTimeField("Tugash", null=True, blank=True, help_text="Bo'sh = cheksiz")
    priority = models.IntegerField("Ustuvorlik", default=0, help_text="Yuqori son birinchi ko'rinadi")

    # Splash uchun
    duration_seconds = models.IntegerField(
        "Ko'rsatish vaqti", default=4,
        help_text="Foydalanuvchi qancha sekund ko'radi (skip 2s'dan keyin)",
    )
    skippable_after = models.IntegerField("Skip vaqti", default=2)

    # Statistika
    impressions = models.IntegerField("Ko'rishlar", default=0)
    clicks = models.IntegerField("Bosishlar", default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Reklama"
        verbose_name_plural = "Reklamalar"
        ordering = ("-priority", "-created_at")
        indexes = [
            models.Index(fields=["slot", "is_active"], name="ads_slot_active_idx"),
            models.Index(fields=["platform", "is_active"], name="ads_platform_active_idx"),
        ]

    def __str__(self):
        return f"[{self.slot}] {self.title}"

    @property
    def ctr(self) -> float:
        """Click-through rate (foiz)."""
        if not self.impressions:
            return 0.0
        return round(self.clicks / self.impressions * 100, 2)

    def is_running(self) -> bool:
        """Ayni paytda faolmi (vaqt oralig'iga ko'ra)."""
        if not self.is_active:
            return False
        now = timezone.now()
        if self.starts_at and now < self.starts_at:
            return False
        if self.ends_at and now > self.ends_at:
            return False
        return True
