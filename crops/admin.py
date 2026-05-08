from django.contrib import admin

from .models import Crop, Region, CropPlan


@admin.register(Crop)
class CropAdmin(admin.ModelAdmin):
    list_display = ("name_uz", "name_lat", "category", "icon_name",
                    "min_soil_temp_c", "days_to_harvest_min", "frost_sensitive")
    list_filter = ("category", "frost_sensitive", "drought_tolerant")
    search_fields = ("name_uz", "name_ru", "name_lat", "slug")
    prepopulated_fields = {"slug": ("name_uz",)}


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("name_uz", "lat_min", "lat_max", "lon_min", "lon_max",
                    "annual_rainfall_mm", "avg_last_frost_doy")
    search_fields = ("name_uz", "name_ru", "slug")


@admin.register(CropPlan)
class CropPlanAdmin(admin.ModelAdmin):
    list_display = ("user", "crop", "planned_plant_date",
                    "expected_harvest_date", "irrigation", "notify")
    list_filter = ("irrigation", "notify", "crop__category")
    search_fields = ("user__phone", "crop__name_uz")
    date_hierarchy = "planned_plant_date"
