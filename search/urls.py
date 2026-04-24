from django.urls import path

from . import views

urlpatterns = [
    path("taxa/", views.taxa_search, name="taxa-search"),
    path("taxa/<int:taxon_id>/", views.taxon_detail, name="taxon-detail"),
    path("observations/", views.nearest_observations, name="nearest-observations"),
    path("wiki/", views.wikipedia_summary, name="wiki-summary"),
    path("browse/", views.browse, name="browse"),
    path("gbif/", views.gbif_search, name="gbif-search"),
    path("gbif/<int:taxon_key>/", views.gbif_detail, name="gbif-detail"),
    path("gbif/occurrences/", views.gbif_occurrences, name="gbif-occurrences"),
    path("enrich/", views.enrich, name="enrich"),
    path("ai-help/", views.ai_help, name="ai-help"),
]
