from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import MapMarkerViewSet, mbtiles_url

router = DefaultRouter()
router.register(r"markers", MapMarkerViewSet, basename="map-marker")

urlpatterns = [
    path("regions/<slug:slug>/mbtiles_url/", mbtiles_url, name="map-mbtiles-url"),
] + router.urls
