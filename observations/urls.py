from django.urls import path
from rest_framework.routers import DefaultRouter

from .tflite import active_tflite_model, scan_feedback
from .views import ObservationViewSet

router = DefaultRouter()
router.register(r"", ObservationViewSet, basename="observation")

# TFLite va feedback router'dan TASHQARIDA — ViewSet bilan to'qnashmasin
urlpatterns = [
    path("tflite/active/", active_tflite_model, name="tflite-active"),
    path("scan/feedback/", scan_feedback, name="scan-feedback"),
] + router.urls
