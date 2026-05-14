#!/usr/bin/env bash
# Django .env'dan FastAPI .env'ni avtomatik tuzadi.
# Eng muhimi: DJANGO_SECRET_KEY → SECRET_KEY (JWT bir xil bo'lishi uchun!)

set -euo pipefail

DJANGO_ENV="${1:-/home/kayumovvv/loyihalarim/togai-backend/.env}"
TARGET_ENV="${2:-/home/kayumovvv/loyihalarim/bioscan-fastapi/.env}"

if [[ ! -f "$DJANGO_ENV" ]]; then
    echo "[!] Django .env topilmadi: $DJANGO_ENV"
    exit 1
fi

# Helper — Django .env'dan kalit oladi
get() {
    grep -E "^${1}=" "$DJANGO_ENV" | head -1 | cut -d= -f2- || true
}

DJANGO_SECRET=$(get DJANGO_SECRET_KEY)
DB_USER=$(get DB_USER); DB_USER=${DB_USER:-togai}
DB_PASSWORD=$(get DB_PASSWORD); DB_PASSWORD=${DB_PASSWORD:-togai}
DB_HOST=$(get DB_HOST); DB_HOST=${DB_HOST:-127.0.0.1}
DB_PORT=$(get DB_PORT); DB_PORT=${DB_PORT:-5432}
DB_NAME=$(get DB_NAME); DB_NAME=${DB_NAME:-togai}

REDIS=$(get REDIS_URL); REDIS=${REDIS:-redis://127.0.0.1:6379/0}
OPENROUTER=$(get OPENROUTER_API_KEY)
GROQ=$(get GROQ_API_KEY)
TG_BOT_TOKEN=$(get TELEGRAM_BOT_TOKEN)
TG_BOT_USER=$(get TELEGRAM_BOT_USERNAME)
TG_OTP_TOKEN=$(get TELEGRAM_OTP_BOT_TOKEN)
TG_OTP_USER=$(get TELEGRAM_OTP_BOT_USERNAME)
FRONTEND=$(get FRONTEND_URL); FRONTEND=${FRONTEND:-http://localhost:5173}

cat > "$TARGET_ENV" <<EOF
# Avtomatik yaratilgan Django .env'dan: $(date -Iseconds)
# DJANGO_SECRET_KEY bilan SECRET_KEY teng — JWT tokenlar APK/webapp uchun valid qoladi.

SECRET_KEY=${DJANGO_SECRET}
DEBUG=false
ENV=production
APP_VERSION=bioscan-fastapi@1.0.0

# Django bilan teng PostgreSQL
DATABASE_URL=postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}

# Redis (Celery uchun alohida bazalar)
REDIS_URL=${REDIS}
CELERY_BROKER_URL=redis://${DB_HOST}:6379/1
CELERY_RESULT_BACKEND=redis://${DB_HOST}:6379/2

# CORS
CORS_ORIGINS=${FRONTEND},https://bioscan.duckdns.org,https://bioscan-startup.vercel.app
ALLOWED_HOSTS=*

# JWT — SimpleJWT bilan teng
JWT_ALGORITHM=HS256
JWT_ACCESS_LIFETIME_MIN=1440
JWT_REFRESH_LIFETIME_DAYS=30

# AI
OPENROUTER_API_KEY=${OPENROUTER}
OPENROUTER_VISION_MODEL=meta-llama/llama-3.2-90b-vision-instruct
OPENROUTER_CHAT_MODEL=meta-llama/llama-3.3-70b-instruct
GROQ_API_KEY=${GROQ}

# Telegram
TELEGRAM_BOT_TOKEN=${TG_BOT_TOKEN}
TELEGRAM_BOT_USERNAME=${TG_BOT_USER}
TELEGRAM_OTP_BOT_TOKEN=${TG_OTP_TOKEN}
TELEGRAM_OTP_BOT_USERNAME=${TG_OTP_USER}

# SMS — Eskiz uchun keyin to'ldiring
SMS_PROVIDER=console
SMS_ESKIZ_EMAIL=
SMS_ESKIZ_PASSWORD=

# Firebase — JSON yo'l (kerak bo'lsa)
FCM_CREDENTIALS_PATH=

# Sentry — DSN bor bo'lsa
SENTRY_DSN=
SENTRY_TRACES=0.1

# Media (Django bilan teng papka)
MEDIA_ROOT=/home/kayumovvv/loyihalarim/togai-backend/media
MEDIA_URL=/media/
EOF

chmod 600 "$TARGET_ENV"
echo "[+] FastAPI .env tayyor: $TARGET_ENV"
echo "[+] Permissions: 0600 (faqat egasi o'qiy oladi)"
