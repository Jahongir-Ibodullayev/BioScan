from rest_framework import serializers

from .models import Ad


class AdSerializer(serializers.ModelSerializer):
    picture = serializers.SerializerMethodField()

    class Meta:
        model = Ad
        fields = (
            "id", "title", "slot", "platform",
            "headline", "body", "cta_text", "target_url",
            "duration_seconds", "skippable_after",
            "picture",
        )
        read_only_fields = fields

    def get_picture(self, obj) -> str | None:
        if obj.image:
            req = self.context.get("request")
            url = obj.image.url
            return req.build_absolute_uri(url) if req else url
        return obj.image_url or None
