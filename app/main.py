"""BioScan FastAPI — entrypoint.

Django'ning teng huquqli almashtiruvchisi. Bir xil PostgreSQL DB.
Foydalanuvchi/APK/Webapp/Bot — barchasi bilan compat.

uvicorn app.main:app --workers 4 --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.api import ads, auth, catalog, chat, crops, incidents, mapdata, observations, saved, search, shop
from app.api import seller as seller_router
from app.core.config import settings
from app.db.session import dispose_engine
from app.middleware.cache_control import EdgeCacheMiddleware, SecurityHeadersMiddleware

log = logging.getLogger("bioscan")
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("BioScan FastAPI starting — env=%s", settings.ENV)
    # DB warmup
    try:
        from sqlalchemy import text

        from app.db.session import _get_sessionmaker
        sm = _get_sessionmaker()
        async with sm() as db:
            await db.execute(text("SELECT 1"))
        log.info("DB ulanish: OK")
    except Exception as e:
        log.warning("DB warmup failed: %s", e)

    # Konfiguratsiya ogohlantirishlari — silently degrade emas
    warnings = []
    if not settings.OPENROUTER_API_KEY:
        warnings.append("OPENROUTER_API_KEY bo'sh — AI scan/chat/advice ishlamaydi")
    if not settings.FCM_CREDENTIALS_PATH:
        warnings.append("FCM_CREDENTIALS_PATH bo'sh — push notification yo'q")
    if settings.SMS_PROVIDER == "console":
        warnings.append("SMS_PROVIDER=console — APK SMS OTP test rejimda")
    if not settings.TELEGRAM_BOT_TOKEN:
        warnings.append("TELEGRAM_BOT_TOKEN bo'sh — webapp Telegram OTP yo'q")
    if not settings.SENTRY_DSN:
        warnings.append("SENTRY_DSN bo'sh — xato monitoring yo'q")
    for w in warnings:
        log.warning("⚠ %s", w)

    yield
    await dispose_engine()
    log.info("Engine disposed")


app = FastAPI(
    title="BioScan API",
    version=settings.APP_VERSION,
    # FastAPI 0.136+ — Pydantic native JSON serializer (orjson uchun custom kerak emas)
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Middleware — CORS strict (config validator prod'da '*'ni rad qiladi)
_cors_origins = settings.cors_origins_list
if not _cors_origins:
    if settings.DEBUG or settings.TESTING:
        _cors_origins = ["http://localhost:5173", "http://localhost:3000"]
    else:
        raise RuntimeError("CORS_ORIGINS bo'sh — production'da ruxsat berilmaydi")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# GZip — 256 baytdan kichikni siqmaymiz (CPU vaqti tejaladi)
app.add_middleware(GZipMiddleware, minimum_size=256, compresslevel=6)
app.add_middleware(EdgeCacheMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# Sentry — ixtiyoriy
if settings.SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            integrations=[StarletteIntegration(), FastApiIntegration()],
            environment=settings.ENV,
            release=settings.APP_VERSION,
            traces_sample_rate=settings.SENTRY_TRACES,
        )
        log.info("Sentry init OK")
    except Exception as e:
        log.warning("Sentry init failed: %s", e)


# Routes
API = "/api"
app.include_router(auth.router, prefix=API)
app.include_router(catalog.router, prefix=API)
app.include_router(observations.router, prefix=API)
app.include_router(chat.router, prefix=API)
app.include_router(shop.router, prefix=API)
app.include_router(seller_router.router, prefix=API)
app.include_router(crops.router, prefix=API)
app.include_router(ads.router, prefix=API)
app.include_router(mapdata.router, prefix=API)
# Admin panel — /admin/ (faqat is_superuser)
try:
    from app.admin import setup_admin
    setup_admin(app, settings.SECRET_KEY)
    log.info("Admin panel: /admin/")
except Exception as e:
    log.warning("Admin panel ulanmadi: %s", e)

app.include_router(saved.router, prefix=API)
app.include_router(saved.collections_router, prefix=API)
app.include_router(search.router, prefix=API)
app.include_router(incidents.router, prefix=API)


@app.get("/api/health/")
async def health() -> dict:
    return {"ok": True, "version": settings.APP_VERSION, "env": settings.ENV}


@app.get("/")
async def root() -> dict:
    return {
        "service": "BioScan FastAPI",
        "version": settings.APP_VERSION,
        "docs": "/api/docs",
    }
