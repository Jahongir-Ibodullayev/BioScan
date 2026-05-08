"""TFLite offline model — versiya boshqaruvi va active model API.

Flutter ilk ishga tushganda bu endpoint orqali joriy faol model URL'ini oladi:
  GET /api/observations/tflite/active/

Yangi model chiqsa version oshadi va Flutter avtomatik yangilanadi.
"""
from __future__ import annotations

from django.db import models
from rest_framework import permissions, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response


class TFLiteModel(models.Model):
    """TFLite model versiyalari — admin yuklab qo'yadi."""

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
        app_label = "observations"
        verbose_name = "TFLite model"
        verbose_name_plural = "TFLite modellar"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.name} v{self.version}"


class TFLiteSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = TFLiteModel
        fields = (
            "id", "name", "version", "size_bytes", "sha256",
            "classes_url", "accuracy", "is_active", "created_at", "file_url",
        )

    def get_file_url(self, obj):
        if not obj.file:
            return None
        req = self.context.get("request")
        url = obj.file.url
        return req.build_absolute_uri(url) if req else url


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def active_tflite_model(request):
    """GET /api/observations/tflite/active/ — joriy faol model.

    Yo'q bo'lsa 204 qaytaradi (Flutter cloud AI'dan foydalanadi).
    """
    model = TFLiteModel.objects.filter(is_active=True).order_by("-created_at").first()
    if not model:
        return Response(status=204)
    ser = TFLiteSerializer(model, context={"request": request})
    return Response(ser.data)
