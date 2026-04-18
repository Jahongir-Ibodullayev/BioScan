from django.contrib import admin

from .models import Observation


@admin.register(Observation)
class ObservationAdmin(admin.ModelAdmin):
    list_display = ("user", "species", "ai_confidence", "place_name", "created_at")
    list_filter = ("species__category",)
    search_fields = ("user__phone", "user__full_name", "species__name")
    raw_id_fields = ("user", "species")
    date_hierarchy = "created_at"
