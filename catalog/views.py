import hashlib

from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from django_filters import rest_framework as filters
from rest_framework import mixins, permissions, viewsets
from rest_framework.response import Response

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

    Both endpoints are cached in Redis for 10 minutes per (path + query)
    combination. Catalog data is global, mostly static, and identical
    across all users — caching here is safe and turns DB hits into
    ~2 ms Redis reads.
    """

    queryset = Species.objects.all().only(
        "id", "slug", "name", "latin", "category", "icon_name",
        "color_class", "summary", "red_book", "iucn_status",
        "image", "image_url",
    )
    lookup_field = "slug"
    permission_classes = [permissions.AllowAny]
    filterset_class = SpeciesFilter
    search_fields = ("name", "latin", "summary", "description")
    ordering_fields = ("name", "created_at")

    _CACHE_TTL = 600  # 10 minutes

    def get_queryset(self):
        # Detail view needs all fields, list view stays light
        if self.action == "retrieve":
            return Species.objects.all()
        return super().get_queryset()

    def get_serializer_class(self):
        if self.action == "retrieve":
            return SpeciesDetailSerializer
        return SpeciesListSerializer

    def _cache_key(self, request) -> str:
        raw = f"{request.path}?{request.META.get('QUERY_STRING', '')}"
        h = hashlib.md5(raw.encode("utf-8")).hexdigest()
        return f"species:v2:{h}"

    def list(self, request, *args, **kwargs):
        key = self._cache_key(request)
        hit = cache.get(key)
        if hit is not None:
            return Response(hit)
        resp = super().list(request, *args, **kwargs)
        if resp.status_code == 200:
            cache.set(key, resp.data, self._CACHE_TTL)
        return resp

    def retrieve(self, request, *args, **kwargs):
        key = self._cache_key(request)
        hit = cache.get(key)
        if hit is not None:
            return Response(hit)
        resp = super().retrieve(request, *args, **kwargs)
        if resp.status_code == 200:
            cache.set(key, resp.data, self._CACHE_TTL)
        return resp
