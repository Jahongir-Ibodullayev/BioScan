from rest_framework.routers import DefaultRouter

from .views import SpeciesViewSet

router = DefaultRouter()
router.register(r"", SpeciesViewSet, basename="species")

urlpatterns = router.urls
