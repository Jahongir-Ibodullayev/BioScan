"""Django settings for togai backend."""
from datetime import timedelta
from pathlib import Path

import sentry_sdk
from decouple import Csv, config
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

BASE_DIR = Path(__file__).resolve().parent.parent

# -------------------------------------------------------------------
# Core
# -------------------------------------------------------------------
SECRET_KEY = config("DJANGO_SECRET_KEY", default="dev-only-insecure-key-change-me")
DEBUG = config("DJANGO_DEBUG", default=True, cast=bool)
ALLOWED_HOSTS = config("DJANGO_ALLOWED_HOSTS", default="*", cast=Csv())

if DEBUG and "*" not in ALLOWED_HOSTS and "testserver" not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append("testserver")

# Temporary local/demo auth shortcut. Keep disabled in production unless explicitly enabled.
QUICK_AUTH_ENABLED = config("QUICK_AUTH_ENABLED", default=DEBUG, cast=bool)

# -------------------------------------------------------------------
# Sentry — error tracking (disabled if SENTRY_DSN not set)
# -------------------------------------------------------------------
SENTRY_DSN = config("SENTRY_DSN", default="")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            LoggingIntegration(level=None, event_level=None),
        ],
        environment=config("SENTRY_ENV", default="development"),
        release=config("APP_VERSION", default="togai@0.1.0"),
        traces_sample_rate=float(config("SENTRY_TRACES", default="0.1")),
        profiles_sample_rate=0.0,
        send_default_pii=False,
    )

AUTH_USER_MODEL = "accounts.User"

# -------------------------------------------------------------------
# Applications
# -------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "django_filters",
    "drf_spectacular",

    # local
    "accounts",
    "catalog",
    "observations",
    "incidents",
    "mapdata",
    "chat",
    "saved_items",
    "bot",
    "search",
    "shop",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=not DEBUG, cast=bool)
SESSION_COOKIE_SECURE = config("SESSION_COOKIE_SECURE", default=not DEBUG, cast=bool)
CSRF_COOKIE_SECURE = config("CSRF_COOKIE_SECURE", default=not DEBUG, cast=bool)
SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=0 if DEBUG else 31536000, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = config("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=not DEBUG, cast=bool)
SECURE_HSTS_PRELOAD = config("SECURE_HSTS_PRELOAD", default=not DEBUG, cast=bool)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# WhiteNoise — serve static files in production
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

ROOT_URLCONF = "togai.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "togai.wsgi.application"

# -------------------------------------------------------------------
# Database
# -------------------------------------------------------------------
# Railway / Render / Heroku provide DATABASE_URL. Local development defaults
# to SQLite; set USE_POSTGRES=True to use the DB_* settings below.
DATABASE_URL = config("DATABASE_URL", default="")
USE_POSTGRES = config("USE_POSTGRES", default=False, cast=bool)
USE_SQLITE = config("USE_SQLITE", default=not USE_POSTGRES, cast=bool)
if DATABASE_URL:
    import dj_database_url
    DATABASES = {
        "default": dj_database_url.parse(DATABASE_URL, conn_max_age=600, ssl_require=False),
    }
elif USE_SQLITE:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": config("DB_NAME", default="togai"),
            "USER": config("DB_USER", default="togai"),
            "PASSWORD": config("DB_PASSWORD", default="togai_pass"),
            "HOST": config("DB_HOST", default="localhost"),
            "PORT": config("DB_PORT", default="5432"),
        }
    }

# -------------------------------------------------------------------
# Password validation
# -------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# -------------------------------------------------------------------
# I18n
# -------------------------------------------------------------------
LANGUAGE_CODE = "uz"
TIME_ZONE = "Asia/Tashkent"
USE_I18N = True
USE_TZ = True

# -------------------------------------------------------------------
# Static / Media
# -------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# -------------------------------------------------------------------
# REST framework
# -------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        # Global per-IP / per-user fallback
        "anon": "120/min",
        "user": "300/min",
        # Scoped — qimmat AI endpoints
        "otp": "5/min",
        "scan": "10/min",            # AI vision: anon ham 10 daqiqada — bot spam to'sish
        "ai_chat": "20/min",         # Groq LLM chat
        "ai_enrich": "30/min",       # Wikipedia + AI enrich
        "ai_help": "20/min",         # AI search assistant
        "search": "120/min",
    },
}

# -------------------------------------------------------------------
# Cache (LocMem for dev, Redis for prod)
# -------------------------------------------------------------------
REDIS_URL = config("REDIS_URL", default="")
if REDIS_URL:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.redis.RedisCache", "LOCATION": REDIS_URL}}
else:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "togai-default"}}

# -------------------------------------------------------------------
# Logging
# -------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "[{asctime}] {levelname} {name} · {message}", "style": "{"},
        # JSON format — Railway/Logtail/Datadog parser uchun
        "json": {
            "()": "togai.log_formatter.JSONFormatter",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json" if not DEBUG else "verbose",
        },
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.request": {"level": "WARNING", "handlers": ["console"], "propagate": False},
        "django.db.backends": {"level": "WARNING", "handlers": ["console"], "propagate": False},
        # 4xx/5xx responses ham log'ga tushadi
        "django.server": {"level": "INFO", "handlers": ["console"], "propagate": False},
        "togai": {"level": "INFO", "handlers": ["console"], "propagate": False},
    },
}

# -------------------------------------------------------------------
# External services (stubs — production keys via .env)
# -------------------------------------------------------------------
# Plant.id — AI tur aniqlash. https://web.plant.id
PLANT_ID_API_KEY = config("PLANT_ID_API_KEY", default="")

# SMS gateway (Eskiz / Play Mobile)
SMS_PROVIDER = config("SMS_PROVIDER", default="console")  # console | eskiz | playmobile
SMS_ESKIZ_EMAIL = config("SMS_ESKIZ_EMAIL", default="")
SMS_ESKIZ_PASSWORD = config("SMS_ESKIZ_PASSWORD", default="")

# OpenAI / Claude — AI chat
OPENAI_API_KEY = config("OPENAI_API_KEY", default="")
ANTHROPIC_API_KEY = config("ANTHROPIC_API_KEY", default="")

# IUCN Red List API
IUCN_API_TOKEN = config("IUCN_API_TOKEN", default="")

# Groq — tez LLM + Vision (asosiy AI provayderimiz)
GROQ_API_KEY = config("GROQ_API_KEY", default="")

# Telegram bot — asosiy bot (skaner, chat, qidiruv)
TELEGRAM_BOT_TOKEN = config("TELEGRAM_BOT_TOKEN", default="")
TELEGRAM_BOT_USERNAME = config("TELEGRAM_BOT_USERNAME", default="ishlabek_bot")

# Telegram OTP bot — alohida bot (faqat OTP kodlari uchun, webapp kirish)
# Asosiy botdan ajratilgan: foydalanuvchi tasodifan asosiy bot bilan aralashtirmasin.
TELEGRAM_OTP_BOT_TOKEN = config("TELEGRAM_OTP_BOT_TOKEN", default="")
TELEGRAM_OTP_BOT_USERNAME = config("TELEGRAM_OTP_BOT_USERNAME", default="TogOTP_bot")

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=6),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Tog'AI API",
    "DESCRIPTION": "Dunyo tabiati — o'simlik, hayvon, hasharot AI yordamchisi",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# -------------------------------------------------------------------
# CORS
# -------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = [
    config("FRONTEND_URL", default="http://localhost:5173"),
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:4173",
]
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^http://localhost:\d+$",
    r"^http://127\.0\.0\.1:\d+$",
    r"^http://0\.0\.0\.0:\d+$",
    r"^http://172\.\d+\.\d+\.\d+:\d+$",
    r"^http://192\.168\.\d+\.\d+:\d+$",
]
CORS_ALLOW_ALL_ORIGINS = config("CORS_ALLOW_ALL", default=DEBUG, cast=bool)
CORS_ALLOW_CREDENTIALS = True
