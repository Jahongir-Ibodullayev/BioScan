from django_filters import rest_framework as filters
from rest_framework import permissions, viewsets
from rest_framework.parsers import FormParser, MultiPartParser

from .models import Incident
from .serializers import IncidentSerializer


class IncidentFilter(filters.FilterSet):
    category = filters.CharFilter(field_name="category", lookup_expr="iexact")
    severity = filters.CharFilter(field_name="severity", lookup_expr="iexact")
    mine = filters.BooleanFilter(method="filter_mine")

    class Meta:
        model = Incident
        fields = ["category", "severity", "mine"]

    def filter_mine(self, qs, name, value):
        if value and self.request.user.is_authenticated:
            return qs.filter(reporter=self.request.user)
        return qs


class IncidentViewSet(viewsets.ModelViewSet):
    """Community incident feed.

    - GET  /api/incidents/            — public list (nearby / category filter)
    - POST /api/incidents/            — auth required
    - GET  /api/incidents/<id>/       — public
    - ?mine=true                      — only mine
    """

    queryset = Incident.objects.all()
    serializer_class = IncidentSerializer
    filterset_class = IncidentFilter
    parser_classes = [MultiPartParser, FormParser]
    search_fields = ("note", "place_name", "code")
    ordering_fields = ("created_at", "severity")

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(reporter=self.request.user)
