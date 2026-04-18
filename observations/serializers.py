from rest_framework import serializers

from catalog.serializers import SpeciesListSerializer

from .models import Observation


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
