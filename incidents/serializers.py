from rest_framework import serializers

from .models import Incident


class IncidentSerializer(serializers.ModelSerializer):
    reporter_name = serializers.CharField(source="reporter.full_name", read_only=True)

    class Meta:
        model = Incident
        fields = (
            "id",
            "code",
            "category",
            "severity",
            "status",
            "note",
            "photo",
            "latitude",
            "longitude",
            "place_name",
            "reporter_name",
            "created_at",
        )
        read_only_fields = ("id", "code", "status", "reporter_name", "created_at")
