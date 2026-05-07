from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

from bot.webhook import telegram_webhook
from togai.health import health

api_patterns = [
    path("health/", health, name="health"),
    path("bot/webhook/", telegram_webhook, name="bot-webhook"),
    path("auth/", include("accounts.urls")),
    path("species/", include("catalog.urls")),
    path("observations/", include("observations.urls")),
    path("incidents/", include("incidents.urls")),
    path("map/", include("mapdata.urls")),
    path("chat/", include("chat.urls")),
    path("collections/", include("saved_items.urls")),
    path("search/", include("search.urls")),
    path("shop/", include("shop.urls")),
    path("ads/", include("ads.urls")),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(api_patterns)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
