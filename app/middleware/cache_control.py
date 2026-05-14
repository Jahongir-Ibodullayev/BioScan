"""Edge cache + security headers — Django middleware bilan teng."""
from __future__ import annotations

import re

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

CACHEABLE = [
    re.compile(r"^/api/species/?$"),
    re.compile(r"^/api/species/[\w-]+/?$"),
    re.compile(r"^/api/search/browse/?"),
    re.compile(r"^/api/search/taxa/?"),
    re.compile(r"^/api/shop/products/?$"),
    re.compile(r"^/api/shop/products/[\w-]+/?$"),
    re.compile(r"^/api/shop/categories/?"),
    re.compile(r"^/api/observations/public/?"),
    re.compile(r"^/api/map/markers/?"),
    re.compile(r"^/api/ads/active/?"),
]


class EdgeCacheMiddleware(BaseHTTPMiddleware):
    """Anonim GET'larga Cache-Control qo'shadi."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        if request.method != "GET" or response.status_code != 200:
            return response
        if request.headers.get("authorization"):
            return response
        path = request.url.path
        for pat in CACHEABLE:
            if pat.match(path):
                response.headers.setdefault(
                    "Cache-Control",
                    "public, s-maxage=3600, stale-while-revalidate=86400",
                )
                response.headers.setdefault("CDN-Cache-Control", "public, s-maxage=3600")
                response.headers.setdefault("Vary", "Accept, Accept-Language")
                break
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """OWASP tavsiyalari."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "img-src 'self' data: https: blob:; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "font-src 'self' data:; "
            "connect-src 'self' https: wss:; "
            "frame-ancestors 'self';",
        )
        response.headers.setdefault(
            "Permissions-Policy",
            "geolocation=(self), camera=(self), microphone=(), payment=()",
        )
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Cross-Origin-Resource-Policy", "cross-origin")
        return response
