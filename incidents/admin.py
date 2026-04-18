from django.contrib import admin

from .models import Incident


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ("code", "category", "severity", "status", "place_name", "created_at")
    list_filter = ("category", "severity", "status")
    search_fields = ("code", "note", "place_name", "reporter__phone")
    date_hierarchy = "created_at"
    raw_id_fields = ("reporter",)
