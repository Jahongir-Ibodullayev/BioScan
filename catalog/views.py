from django_filters import rest_framework as filters
from rest_framework import mixins, permissions, viewsets

from .models import Species
from .serializers import SpeciesDetailSerializer, SpeciesListSerializer


class SpeciesFilter(filters.FilterSet):
    category = filters.CharFilter(field_name="category", lookup_expr="iexact")
    red_book = filters.BooleanFilter(field_name="red_book")
    iucn = filters.CharFilter(field_name="iucn_status", lookup_expr="iexact")
    region = filters.CharFilter(field_name="regions", lookup_expr="icontains")
    halal = filters.CharFilter(field_name="halal_status", lookup_expr="iexact")
    medicinal = filters.BooleanFilter(field_name="is_medicinal")
    honey = filters.BooleanFilter(field_name="is_honey_plant")
    edible = filters.BooleanFilter(field_name="is_edible")
    livestock_toxic = filters.CharFilter(field_name="livestock_danger", lookup_expr="iexact")

    class Meta:
        model = Species
        fields = ["category", "red_book", "iucn", "region", "halal",
                  "medicinal", "honey", "edible", "livestock_toxic"]


class SpeciesViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Read-only public catalog.

    GET /api/species/
    GET /api/species/<slug>/
    """

    queryset = Species.objects.all()
    lookup_field = "slug"
    permission_classes = [permissions.AllowAny]
    filterset_class = SpeciesFilter
    search_fields = ("name", "latin", "summary", "description")
    ordering_fields = ("name", "created_at")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return SpeciesDetailSerializer
        return SpeciesListSerializer
