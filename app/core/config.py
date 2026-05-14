"""Sozlamalar — environment variables.

Production'da xavfsizlik kritik:
  - SECRET_KEY default qiymat bo'lsa va DEBUG=false → loyiha startup'da xato bersin.
  - CORS '*' production'da rad etiladi (faqat dev).
"""
from __future__ import annotations

from functools import cached_property, lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Default xavfli qiymat — biz tekshiramiz
_INSECURE_DEFAULT_KEY = "dev-only-insecure-change-me"


class Settings(BaseSettings):
    """Barcha environment variables — strict tipli + fail-fast."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core
    SECRET_KEY: str = _INSECURE_DEFAULT_KEY
    DEBUG: bool = False
    ENV: str = "development"
    APP_VERSION: str = "bioscan-fastapi@1.0.0"

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    ALLOWED_HOSTS: str = "*"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://togai:togai@localhost:5432/togai"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # JWT
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_LIFETIME_MIN: int = 60 * 24
    JWT_REFRESH_LIFETIME_DAYS: int = 30

    # Rate limit (config'da, hardcoded emas)
    RATE_LIMIT_SCAN_PER_MIN: int = 10
    RATE_LIMIT_ADVICE_PER_MIN: int = 20
    RATE_LIMIT_AUTH_PER_MIN: int = 30

    # AI providers
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE: str = "https://openrouter.ai/api/v1"
    OPENROUTER_VISION_MODEL: str = "meta-llama/llama-3.2-90b-vision-instruct"
    OPENROUTER_CHAT_MODEL: str = "meta-llama/llama-3.3-70b-instruct"
    GROQ_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # SMS
    SMS_PROVIDER: str = "console"
    SMS_ESKIZ_EMAIL: str = ""
    SMS_ESKIZ_PASSWORD: str = ""

    # External
    OPEN_METEO_BASE: str = "https://api.open-meteo.com/v1"

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_BOT_USERNAME: str = ""
    TELEGRAM_OTP_BOT_TOKEN: str = ""
    TELEGRAM_OTP_BOT_USERNAME: str = ""

    # Firebase
    FCM_CREDENTIALS_PATH: str = ""

    # Sentry
    SENTRY_DSN: str = ""
    SENTRY_TRACES: float = 0.1

    # Media
    MEDIA_ROOT: str = "media"
    MEDIA_URL: str = "/media/"

    # Auth flags
    QUICK_AUTH_ENABLED: bool = True

    # Test rejimi — pytest avtomatik o'rnatadi, prod tekshiruvlari o'tkazib yuboriladi
    TESTING: bool = False

    @model_validator(mode="after")
    def _validate_production_security(self):
        """Production'da xavfsizlik tekshiruvlari — fail fast."""
        is_prod = not self.DEBUG and not self.TESTING and self.ENV.lower() in ("production", "prod")

        if is_prod:
            # SECRET_KEY tekshiruvi
            if self.SECRET_KEY == _INSECURE_DEFAULT_KEY:
                raise ValueError(
                    "PRODUCTION'DA xavfli: SECRET_KEY default qiymatda! "
                    ".env faylida SECRET_KEY=<random 64+ byte> kiriting."
                )
            if len(self.SECRET_KEY) < 32:
                raise ValueError(
                    f"SECRET_KEY kamida 32 belgili bo'lsin (hozir: {len(self.SECRET_KEY)})"
                )

            # CORS '*' rad
            origins = [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]
            if "*" in origins or not origins:
                raise ValueError(
                    "PRODUCTION'DA xavfli: CORS_ORIGINS aniq domain'lar bilan to'ldiring "
                    "(masalan: https://bioscan.uz,https://bioscan-startup.vercel.app)"
                )

            # Database
            if "localhost" in self.DATABASE_URL or "127.0.0.1" in self.DATABASE_URL:
                # OK — VPS'da lokal Postgres bo'lishi mumkin, faqat log
                pass

        return self

    @field_validator("CORS_ORIGINS")
    @classmethod
    def _validate_cors_format(cls, v: str) -> str:
        # Bo'sh qiymat OK (validator yuqorida prod uchun tekshiradi)
        return v

    @cached_property
    def cors_origins_list(self) -> list[str]:
        """Har request'da qayta hisoblanmaydi — bir martagina parse."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
