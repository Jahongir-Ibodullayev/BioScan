from rest_framework import serializers

from catalog.serializers import SpeciesListSerializer

from .models import SavedSpecies


class SavedSpeciesSerializer(serializers.ModelSerializer):
    species_detail = SpeciesListSerializer(source="species", read_only=True)

    class Meta:
        model = SavedSpecies
        fields = ("id", "species", "species_detail", "note", "created_at")
        read_only_fields = ("id", "species_detail", "created_at")
