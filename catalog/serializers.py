from rest_framework import serializers

from .models import Species


class SpeciesListSerializer(serializers.ModelSerializer):
    picture = serializers.SerializerMethodField()

    class Meta:
        model = Species
        fields = (
            "id",
            "slug",
            "name",
            "latin",
            "category",
            "icon_name",
            "color_class",
            "summary",
            "red_book",
            "iucn_status",
            "picture",
        )

    def get_picture(self, obj) -> str | None:
        request = self.context.get("request")
        if obj.image:
            url = obj.image.url
            return request.build_absolute_uri(url) if request else url
        return obj.image_url or None


class SpeciesDetailSerializer(SpeciesListSerializer):
    class Meta(SpeciesListSerializer.Meta):
        fields = SpeciesListSerializer.Meta.fields + (
            "description",
            "habitat",
            "uses",
            "warnings",
            "first_aid",
            "regions",
            "external_ref",
            "halal_status",
            "is_medicinal",
            "is_honey_plant",
            "livestock_danger",
            "is_edible",
            "bloom_months",
            "harvest_months",
            "fine_bhm_min",
            "fine_bhm_max",
            "law_article",
            "created_at",
            "updated_at",
        )
