from rest_framework.routers import DefaultRouter

from .views import MapMarkerViewSet

router = DefaultRouter()
router.register(r"markers", MapMarkerViewSet, basename="map-marker")

urlpatterns = router.urls
