"""Health check endpoint — Railway/CDN liveness va readiness probes uchun.

GET /api/health/  → 200 OK + JSON status
GET /api/health/?deep=1 → DB va cache ham tekshiriladi
"""
import time

from django.core.cache import cache
from django.db import connection
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    """Basic liveness — har doim 200 qaytaradi (process tirik)."""
    deep = request.GET.get("deep") in ("1", "true", "yes")

    result = {
        "status": "ok",
        "service": "togai-backend",
        "time": timezone.now().isoformat(),
    }

    if not deep:
        return Response(result)

    # DEEP — DB va cache tekshir
    checks = {}

    # DB ping
    db_start = time.monotonic()
    try:
        with connection.cursor() as c:
            c.execute("SELECT 1")
            c.fetchone()
        checks["db"] = {"ok": True, "ms": round((time.monotonic() - db_start) * 1000, 1)}
    except Exception as e:
        checks["db"] = {"ok": False, "error": str(e)[:120]}
        result["status"] = "degraded"

    # Cache ping
    cache_start = time.monotonic()
    try:
        cache.set("__health__", "1", 5)
        v = cache.get("__health__")
        checks["cache"] = {
            "ok": v == "1",
            "ms": round((time.monotonic() - cache_start) * 1000, 1),
        }
    except Exception as e:
        checks["cache"] = {"ok": False, "error": str(e)[:120]}
        result["status"] = "degraded"

    result["checks"] = checks
    return Response(result, status=200 if result["status"] == "ok" else 503)
