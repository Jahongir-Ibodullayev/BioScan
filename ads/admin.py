from django.contrib import admin
from django.utils.html import format_html

from .models import Ad


@admin.register(Ad)
class AdAdmin(admin.ModelAdmin):
    list_display = (
        "title", "slot", "platform", "is_active", "priority",
        "preview", "impressions", "clicks", "ctr_display",
        "starts_at", "ends_at",
    )
    list_filter = ("slot", "platform", "is_active")
    search_fields = ("title", "headline", "body", "target_url")
    readonly_fields = ("impressions", "clicks", "created_at", "updated_at")
    fieldsets = (
        ("Asosiy", {
            "fields": ("title", "is_active", "priority"),
        }),
        ("Joylashuv", {
            "fields": ("slot", "platform"),
        }),
        ("Tana — kontent", {
            "fields": ("image", "image_url", "headline", "body", "cta_text", "target_url"),
        }),
        ("Vaqt va sozlash", {
            "fields": ("starts_at", "ends_at", "duration_seconds", "skippable_after"),
        }),
        ("Statistika", {
            "fields": ("impressions", "clicks", "created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    def preview(self, obj):
        url = (obj.image.url if obj.image else None) or obj.image_url
        if url:
            return format_html(
                '<img src="{}" style="height:50px; border-radius:6px;" />', url,
            )
        return "—"
    preview.short_description = "Rasm"

    def ctr_display(self, obj):
        return f"{obj.ctr}%"
    ctr_display.short_description = "CTR"
