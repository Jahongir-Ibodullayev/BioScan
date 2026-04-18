from django.contrib import admin

from .models import Species


@admin.register(Species)
class SpeciesAdmin(admin.ModelAdmin):
    list_display = ("name", "latin", "category", "red_book", "iucn_status", "updated_at")
    list_filter = ("category", "red_book", "iucn_status")
    search_fields = ("name", "latin", "slug")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)
