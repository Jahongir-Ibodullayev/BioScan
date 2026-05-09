"""BioScan Cache-Control middleware — Vercel edge caching uchun.

Anonim GET so'rovlarga `Cache-Control: public, s-maxage=N, stale-while-revalidate`
qo'shadi. Vercel edge cache mahalliy regionda javobni saqlaydi —
keyingi so'rov VPS'gacha bormaydi (UZ→HK ping ~800ms tejaladi).

Faqat ANONIM so'rovlar — Authorization header bo'lsa cache'lamaydi
(har bir foydalanuvchining shaxsiy ma'lumoti aralashmasin).
"""
from __future__ import annotations

import re

# Cache qilinadigan endpoint patternlar (regex)
CACHEABLE_PATHS = [
    re.compile(r"^/api/species/?$"),
    re.compile(r"^/api/species/[\w-]+/?$"),
    re.compile(r"^/api/search/browse/?"),
    re.compile(r"^/api/search/taxa/?"),
    re.compile(r"^/api/shop/products/?$"),
    re.compile(r"^/api/shop/products/[\w-]+/?$"),
    re.compile(r"^/api/shop/categories/?"),
    re.compile(r"^/api/observations/public/?"),
    re.compile(r"^/api/map/?"),
]


class EdgeCacheMiddleware:
    """Anonim GET so'rovlarga Cache-Control qo'shadi."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.method != "GET":
            return response
        if response.status_code != 200:
            return response
        # Foydalanuvchi token'i bor — shaxsiy javob, cache yo'q
        if request.headers.get("Authorization"):
            return response
        path = request.path
        for pat in CACHEABLE_PATHS:
            if pat.match(path):
                # 5 minut edge cache, 1 soat stale-while-revalidate
                response["Cache-Control"] = (
                    "public, s-maxage=300, stale-while-revalidate=3600"
                )
                # Vercel uchun
                response["CDN-Cache-Control"] = "public, s-maxage=300"
                response["Vary"] = "Accept, Accept-Language"
                break
        return response


class SecurityHeadersMiddleware:
    """Production security headers — OWASP tavsiyalari.

    Django'ning SecurityMiddleware'i HSTS qo'yadi, lekin CSP, Permissions-Policy
    va Referrer-Policy ni alohida boshqaramiz.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # Browser'ga ruxsat etilgan resurslar
        response.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "img-src 'self' data: https: blob:; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "font-src 'self' data:; "
            "connect-src 'self' https: wss:; "
            "frame-ancestors 'self';",
        )
        # Brauzerlar API'larini cheklash (kerak emaslarini)
        response.setdefault(
            "Permissions-Policy",
            "geolocation=(self), camera=(self), microphone=(), payment=()",
        )
        response.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.setdefault("X-Content-Type-Options", "nosniff")
        # Cross-origin resource policy — xavfsiz default
        response.setdefault("Cross-Origin-Resource-Policy", "cross-origin")
        return response
