from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ConversationViewSet, ai_public

router = DefaultRouter()
router.register(r"conversations", ConversationViewSet, basename="conversation")

urlpatterns = [
    path("ai/", ai_public, name="chat-ai"),
    *router.urls,
]
