from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from .models import Crop, Region, CropPlan
from .serializers import (
    CropListSerializer, CropPlanSerializer, CropSerializer, RegionSerializer,
)


class CropViewSet(viewsets.ReadOnlyModelViewSet):
    """Hamma ekinlar — sync uchun."""
    queryset = Crop.objects.all()
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"

    def get_serializer_class(self):
        if self.action == "list":
            return CropListSerializer
        return CropSerializer

    @action(detail=False, methods=["get"], url_path="regions")
    def regions(self, request):
        rows = Region.objects.all()
        return Response(RegionSerializer(rows, many=True).data)


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def crop_advice(request):
    """POST /api/crops/advice/ — GPS + ekin → maslahat."""
    crop_slug = request.data.get("crop_slug")
    try:
        lat = float(request.data.get("lat") or 0)
        lon = float(request.data.get("lon") or 0)
    except (TypeError, ValueError):
        return Response({"detail": "lat va lon raqam bo'lishi kerak"}, status=400)
    irrigation = request.data.get("irrigation", "manual")
    plot = request.data.get("plot_size_m2")
    exp = request.data.get("experience", "beginner")

    crop = Crop.objects.filter(slug=crop_slug).first()
    if not crop:
        return Response({"detail": "ekin topilmadi"}, status=404)

    from .services.advice import build_advice
    data = build_advice(crop, lat, lon, irrigation,
                        plot_size_m2=plot, experience=exp)
    return Response(data)


class CropPlanViewSet(viewsets.ModelViewSet):
    """Foydalanuvchi rejalari."""
    serializer_class = CropPlanSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = CropPlan.objects.none()  # drf_spectacular schema gen uchun

    def get_queryset(self):
        # Schema gen paytida AnonymousUser keladi — bo'sh queryset qaytaramiz
        if getattr(self, "swagger_fake_view", False):
            return CropPlan.objects.none()
        if not self.request.user.is_authenticated:
            return CropPlan.objects.none()
        return CropPlan.objects.filter(user=self.request.user).select_related("crop")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
