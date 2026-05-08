"""TFLite offline model API — version, active model, scan feedback.

Endpoints:
  GET  /api/observations/tflite/active/      — joriy faol model
  POST /api/observations/scan/feedback/      — foydalanuvchi rating

Model TFLiteModel observations/models.py'da.
"""
from __future__ import annotations

from rest_framework import permissions, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import Observation, ScanFeedback, TFLiteModel


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
    """GET /api/observations/tflite/active/

    Yo'q bo'lsa 204 — APK cloud AI'ga fallback qiladi.
    """
    model = (
        TFLiteModel.objects.filter(is_active=True)
        .order_by("-created_at").first()
    )
    if not model:
        return Response(status=204)
    ser = TFLiteSerializer(model, context={"request": request})
    return Response(ser.data)


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def scan_feedback(request):
    """POST /api/observations/scan/feedback/

    Body: {observation_id?, predicted_slug, correct_slug?, is_correct, note?}
    Hech qanday majburiy kalit yo'q — barcha ixtiyoriy.
    """
    data = request.data or {}
    obs_id = data.get("observation_id")
    obs = Observation.objects.filter(pk=obs_id).first() if obs_id else None
    fb = ScanFeedback.objects.create(
        user=request.user if request.user.is_authenticated else None,
        observation=obs,
        predicted_slug=(data.get("predicted_slug") or "")[:140],
        correct_slug=(data.get("correct_slug") or "")[:140],
        is_correct=bool(data.get("is_correct", True)),
        note=(data.get("note") or "")[:500],
    )
    return Response({"id": fb.id, "ok": True})
