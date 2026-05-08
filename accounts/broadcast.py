"""POST /api/admin/notifications/broadcast/ — admin'lar uchun ommaviy push.

Faqat is_staff=True yoki is_superuser=True foydalanuvchilar.
"""
from __future__ import annotations

from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from togai.services.fcm import broadcast as fcm_broadcast


class IsStaffOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and (u.is_staff or u.is_superuser))


@api_view(["POST"])
@permission_classes([IsStaffOnly])
def admin_broadcast(request):
    """POST {title, body, data?, segment?}

    segment: "all" (default) yoki "active_7d"
    """
    data = request.data or {}
    title = (data.get("title") or "").strip()
    body = (data.get("body") or "").strip()
    if not title or not body:
        return Response(
            {"detail": "title va body majburiy"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    extra = data.get("data") or {}
    segment = data.get("segment")

    sent = fcm_broadcast(title, body, data=extra, segment=segment)
    return Response({"sent": sent, "title": title})
