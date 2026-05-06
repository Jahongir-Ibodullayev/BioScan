from rest_framework import serializers

from catalog.serializers import SpeciesListSerializer

from .models import Observation

MAX_SCAN_IMAGE_BYTES = 8 * 1024 * 1024
ALLOWED_SCAN_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


class ObservationSerializer(serializers.ModelSerializer):
    species_detail = SpeciesListSerializer(source="species", read_only=True)

    class Meta:
        model = Observation
        fields = (
            "id",
            "species",
            "species_detail",
            "photo",
            "ai_confidence",
            "note",
            "latitude",
            "longitude",
            "place_name",
            "created_at",
        )
        read_only_fields = ("id", "created_at", "species_detail")


class ScanRequestSerializer(serializers.Serializer):
    """POST /api/observations/scan/  — rasmni AI aniqlaydi.
    Hozir mock — eng birinchi Species'ni qaytaradi yoki 'no-match'.
    """

    photo = serializers.ImageField()
    latitude = serializers.FloatField(required=False)
    longitude = serializers.FloatField(required=False)

    def validate_photo(self, value):
        if getattr(value, "size", 0) > MAX_SCAN_IMAGE_BYTES:
            raise serializers.ValidationError("Rasm hajmi 8 MB dan oshmasin.")

        content_type = (getattr(value, "content_type", "") or "").lower()
        if content_type and content_type not in ALLOWED_SCAN_CONTENT_TYPES:
            raise serializers.ValidationError("Faqat JPEG, PNG yoki WebP rasm yuboring.")
        return value
