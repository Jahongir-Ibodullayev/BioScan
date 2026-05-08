from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"plans", views.CropPlanViewSet, basename="crop-plan")
router.register(r"", views.CropViewSet, basename="crop")

urlpatterns = [
    path("advice/", views.crop_advice, name="crop-advice"),
    path("", include(router.urls)),
]
