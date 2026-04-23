"""DRF exception handler + Django middleware for consistent error envelopes.

Every error returned to clients looks like:
  { "error": { "code": "...", "message": "...", "detail": {...} }, "status": 4xx/5xx }
"""
from __future__ import annotations

import logging

from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_default

from .exceptions import TogaiError

log = logging.getLogger(__name__)


def togai_exception_handler(exc, context):
    """Wire this in REST_FRAMEWORK['EXCEPTION_HANDLER']."""
    if isinstance(exc, TogaiError):
        log.warning("togai.error %s: %s", exc.code, exc.message)
        return Response(
            {"error": {"code": exc.code, "message": exc.message, "detail": exc.detail}},
            status=exc.status_code,
        )

    response = drf_default(exc, context)
    if response is not None:
        # Wrap DRF's default in our envelope for consistency
        payload = response.data
        if isinstance(payload, dict) and "error" not in payload:
            response.data = {
                "error": {
                    "code": "validation_error" if response.status_code < 500 else "server_error",
                    "message": payload.get("detail") or str(payload)[:200],
                    "detail": payload if not payload.get("detail") else {},
                }
            }
        return response

    log.exception("unhandled: %s", exc)
    return Response(
        {"error": {"code": "internal_error", "message": "Serverda xatolik",
                   "detail": {"type": type(exc).__name__}}},
        status=500,
    )
