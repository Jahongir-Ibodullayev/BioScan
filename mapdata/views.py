from django.conf import settings
from django_filters import rest_framework as filters
from rest_framework import permissions, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import MapMarker
from .serializers import MapMarkerSerializer


# MBTiles offline xarita paketlari (CDN/R2 URL'lar — bo'sh holatda yo'q)
# Real fayllarni yuklash kerak: tilemaker yoki mbutil bilan tayyorlanadi.
MBTILES_URLS = {
    "tashkent":      "",  # https://cdn.bioscan.uz/mbtiles/tashkent.mbtiles
    "samarqand":     "",
    "buxoro":        "",
    "fargona":       "",
    "andijon":       "",
    "namangan":      "",
    "qashqadaryo":   "",
    "surxondaryo":   "",
    "navoiy":        "",
    "xorazm":        "",
    "qoraqalpogiston": "",
    "jizzax":        "",
    "sirdaryo":      "",
}


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def mbtiles_url(request, slug: str):
    """GET /api/map/regions/<slug>/mbtiles_url/

    Offline xarita paketi havolasini qaytaradi (Cloudflare R2 yoki S3'da).
    Hozircha CDN'ga fayllar yuklanmagan — bo'sh URL bilan 200 qaytariladi.
    """
    url = MBTILES_URLS.get(slug, "")
    return Response({
        "region": slug,
        "url": url or None,
        "size_mb": 18 if url else 0,
        "available": bool(url),
        "message": (
            "Offline xarita paketi tayyor — yuklab oling"
            if url else
            "Bu viloyat uchun offline xarita hali tayyor emas"
        ),
    })


class MarkerFilter(filters.FilterSet):
    type = filters.CharFilter(field_name="type", lookup_expr="iexact")
    region = filters.CharFilter(field_name="region", lookup_expr="icontains")

    # Geo bounding-box: ?min_lat=...&max_lat=...&min_lng=...&max_lng=...
    min_lat = filters.NumberFilter(field_name="latitude", lookup_expr="gte")
    max_lat = filters.NumberFilter(field_name="latitude", lookup_expr="lte")
    min_lng = filters.NumberFilter(field_name="longitude", lookup_expr="gte")
    max_lng = filters.NumberFilter(field_name="longitude", lookup_expr="lte")

    class Meta:
        model = MapMarker
        fields = ["type", "region", "min_lat", "max_lat", "min_lng", "max_lng"]


class MapMarkerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MapMarker.objects.filter(active=True)
    serializer_class = MapMarkerSerializer
    permission_classes = [permissions.AllowAny]
    filterset_class = MarkerFilter
    search_fields = ("label", "description", "region")

    def get_queryset(self):
        qs = super().get_queryset()
        # `?bbox=lat1,lon1,lat2,lon2` qo'shimcha format (Flutter uchun qulay)
        bbox = self.request.GET.get("bbox", "")
        if bbox:
            try:
                lat1, lon1, lat2, lon2 = [float(x) for x in bbox.split(",")[:4]]
                qs = qs.filter(
                    latitude__gte=min(lat1, lat2), latitude__lte=max(lat1, lat2),
                    longitude__gte=min(lon1, lon2), longitude__lte=max(lon1, lon2),
                )
            except (TypeError, ValueError):
                pass
        # max 500 ta marker — APK katta natija qabul qilmasin
        try:
            limit = max(1, min(500, int(self.request.GET.get("limit") or 500)))
        except ValueError:
            limit = 500
        return qs[:limit]
