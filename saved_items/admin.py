from django.contrib import admin

from .models import SavedSpecies


@admin.register(SavedSpecies)
class SavedSpeciesAdmin(admin.ModelAdmin):
    list_display = ("user", "species", "created_at")
    search_fields = ("user__phone", "species__name")
    raw_id_fields = ("user", "species")
