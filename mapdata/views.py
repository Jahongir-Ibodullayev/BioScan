from django_filters import rest_framework as filters
from rest_framework import permissions, viewsets

from .models import MapMarker
from .serializers import MapMarkerSerializer


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
