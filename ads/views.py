"""Ads API — webapp/APK reklama olishi va statistika yuborishi."""
from django.db.models import F
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import Ad
from .serializers import AdSerializer


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def active_ad(request):
    """GET /api/ads/active/?slot=splash&platform=web

    Ayni paytda faol bo'lgan eng birinchi reklamani qaytaradi (priority bo'yicha).
    Topilmasa 204 No Content.
    """
    slot = request.GET.get("slot", Ad.SLOT_SPLASH)
    platform = request.GET.get("platform", "all")

    now = timezone.now()
    qs = Ad.objects.filter(
        is_active=True,
        slot=slot,
        starts_at__lte=now,
    ).filter(
        # platform: all yoki match
        platform__in=["all", platform],
    )
    # ends_at: null OR future
    from django.db.models import Q
    qs = qs.filter(Q(ends_at__isnull=True) | Q(ends_at__gte=now))
    qs = qs.order_by("-priority", "-created_at")

    ad = qs.first()
    if not ad:
        return Response(status=status.HTTP_204_NO_CONTENT)

    # Atomic increment impressions
    Ad.objects.filter(pk=ad.pk).update(impressions=F("impressions") + 1)

    ser = AdSerializer(ad, context={"request": request})
    return Response(ser.data)


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def track_click(request, ad_id: int):
    """POST /api/ads/<id>/click/  — bosildi statistikasi."""
    Ad.objects.filter(pk=ad_id).update(clicks=F("clicks") + 1)
    return Response({"ok": True})


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def track_impression(request, ad_id: int):
    """POST /api/ads/<id>/impression/ — qo'shimcha impression (ixtiyoriy).

    Active ad endpoint allaqachon impression hisoblaydi, lekin agar
    frontend ad'ni cache'dan ko'rsata olsa, bu endpoint orqali yuboradi.
    """
    Ad.objects.filter(pk=ad_id).update(impressions=F("impressions") + 1)
    return Response({"ok": True})
