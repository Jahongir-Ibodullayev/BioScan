from rest_framework.routers import DefaultRouter

from .views import SavedSpeciesViewSet

router = DefaultRouter()
router.register(r"", SavedSpeciesViewSet, basename="saved-species")

urlpatterns = router.urls
