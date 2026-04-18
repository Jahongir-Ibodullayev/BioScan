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
