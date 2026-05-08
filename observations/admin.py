from django.contrib import admin

from .models import Observation, ScanFeedback, TFLiteModel


@admin.register(Observation)
class ObservationAdmin(admin.ModelAdmin):
    list_display = ("user", "species", "ai_confidence", "place_name", "created_at")
    list_filter = ("species__category",)
    search_fields = ("user__phone", "user__full_name", "species__name")
    raw_id_fields = ("user", "species")
    date_hierarchy = "created_at"


@admin.register(TFLiteModel)
class TFLiteModelAdmin(admin.ModelAdmin):
    list_display = ("name", "version", "size_bytes", "accuracy", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "version", "sha256")


@admin.register(ScanFeedback)
class ScanFeedbackAdmin(admin.ModelAdmin):
    list_display = ("predicted_slug", "correct_slug", "is_correct", "user", "created_at")
    list_filter = ("is_correct",)
    search_fields = ("predicted_slug", "correct_slug", "note")
