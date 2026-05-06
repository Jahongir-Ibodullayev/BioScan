from urllib.parse import quote

from rest_framework import serializers

from .models import Species


def _fast_url(raw: str, w: int = 400) -> str:
    """Wrap external image URL through images.weserv.nl proxy.

    The proxy caches + resizes on Cloudflare's network → 3-5x faster
    than direct iNaturalist/S3 from non-US clients. Free, no key.
    """
    if not raw:
        return raw
    if "weserv.nl" in raw:
        return raw
    # weserv expects URL without scheme
    if raw.startswith("https://"):
        cleaned = raw[len("https://") :]
    elif raw.startswith("http://"):
        cleaned = raw[len("http://") :]
    else:
        cleaned = raw
    return (
        f"https://images.weserv.nl/?url={quote(cleaned, safe='')}"
        f"&w={w}&q=70&output=webp&af"
    )


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
        if obj.image_url:
            return _fast_url(obj.image_url, w=400)
        return None


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
