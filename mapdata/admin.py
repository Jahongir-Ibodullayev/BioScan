from django.contrib import admin

from .models import MapMarker


@admin.register(MapMarker)
class MapMarkerAdmin(admin.ModelAdmin):
    list_display = ("label", "type", "region", "active", "created_at")
    list_filter = ("type", "active", "region")
    search_fields = ("label", "description")
