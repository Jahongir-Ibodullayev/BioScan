from rest_framework import serializers

from .models import Crop, Region, CropPlan


class CropSerializer(serializers.ModelSerializer):
    class Meta:
        model = Crop
        fields = "__all__"


class CropListSerializer(serializers.ModelSerializer):
    """Yengil — ro'yxat uchun."""
    class Meta:
        model = Crop
        fields = (
            "id", "slug", "name_uz", "name_ru", "name_lat", "category",
            "icon_name", "image_url", "days_to_harvest_min", "days_to_harvest_max",
        )


class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = "__all__"


class CropPlanSerializer(serializers.ModelSerializer):
    crop_data = CropListSerializer(source="crop", read_only=True)

    class Meta:
        model = CropPlan
        fields = (
            "id", "crop", "crop_data", "lat", "lon", "irrigation",
            "plot_size_m2", "planned_plant_date", "expected_harvest_date",
            "notes", "notify", "created_at", "completed_at",
        )
        read_only_fields = ("id", "created_at", "crop_data")
