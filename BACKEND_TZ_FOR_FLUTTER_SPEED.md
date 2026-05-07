# 📋 BioScan Backend — Tezlik uchun to'liq TZ

**Maqsad:** Flutter APK 5x tezroq ishlashi uchun backend'ni to'g'ri sozlash. Hozir har so'rov 500-700ms, bu TZ'dan keyin **100-200ms** bo'lishi kerak.

---

## 🎯 1. INFRASTRUKTURA — eng tez yo'l

### 1.1 Server lokatsiyasi
- **MAJBURIY:** Server **Germaniya / Polsha / Turkiya / Singapur**'da bo'lsin (Toshkent'ga 50-150ms latency)
- ❌ AQSh / G'arbiy Yevropa = 300-500ms (juda sekin)
- ✅ Hetzner Helsinki / OVH Frankfurt / Vultr Frankfurt — eng yaxshi narx/tezlik

### 1.2 Texnik talab
| Resurs | Minimum | Tavsiya |
|---|---|---|
| RAM | 2 GB | **4 GB** |
| CPU | 2 vCPU | 4 vCPU |
| Disk | 20 GB SSD | 40 GB NVMe SSD |
| Bandwidth | 1 TB/oy | 5 TB/oy |
| OS | Ubuntu 22.04 | Ubuntu 24.04 LTS |

---

## 🔐 2. HTTPS / DOMEN — tezlikni 3x oshiradi

### 2.1 Domen
**MAJBURIY:** `bioscan.uz` (yoki `api.bioscan.uz`) domeni sotib olib, server IP'ga A-record qo'ying.
```
A    bioscan.uz       62.171.185.105
A    api.bioscan.uz   62.171.185.105
```

### 2.2 SSL sertifikat (Let's Encrypt — bepul)
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d bioscan.uz -d api.bioscan.uz
sudo systemctl enable certbot.timer  # avtomatik yangilanadi
```

### 2.3 Nginx konfiguratsiya (`/etc/nginx/sites-available/bioscan`)
```nginx
server {
    listen 443 ssl http2;
    server_name api.bioscan.uz;

    ssl_certificate     /etc/letsencrypt/live/bioscan.uz/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/bioscan.uz/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;

    # GZIP — javoblar 5x kichik
    gzip on;
    gzip_types application/json application/javascript text/css text/plain;
    gzip_min_length 256;
    gzip_comp_level 5;

    # Brotli (qo'shimcha tezlik)
    # brotli on; brotli_types application/json text/css;

    # HTTP/2 push, keep-alive
    keepalive_timeout 65;
    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_redirect off;
        proxy_buffering off;
        proxy_read_timeout 90s;
    }

    location /media/ {
        alias /var/www/togai-backend/media/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    location /static/ {
        alias /var/www/togai-backend/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}

# HTTP → HTTPS yo'naltirish
server {
    listen 80;
    server_name api.bioscan.uz;
    return 301 https://$host$request_uri;
}
```

---

## 🐍 3. DJANGO BACKEND — production sozlash

### 3.1 Environment fayllar `.env`
```env
DJANGO_SECRET_KEY=<yangi tasodifiy 64 char>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=api.bioscan.uz,bioscan.uz,62.171.185.105

# DB — PostgreSQL ishlatish (SQLite emas!)
DATABASE_URL=postgresql://togai:STRONG_PASS@127.0.0.1:5432/togai

# Redis — cache + Celery broker
REDIS_URL=redis://127.0.0.1:6379/1
CELERY_BROKER_URL=redis://127.0.0.1:6379/3
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/4

# AI — OpenRouter
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_REFERER=https://bioscan.uz
OPENROUTER_TITLE=BioScan

# Telegram OTP bot (ALOHIDA bot, asosiy bot bilan kesilmasin)
TELEGRAM_BOT_TOKEN=<asosiy bot token>
TELEGRAM_BOT_USERNAME=ishlabek_bot
TELEGRAM_OTP_BOT_TOKEN=<OTP bot token>
TELEGRAM_OTP_BOT_USERNAME=TogOTP_bot

# CORS — barcha domenlardan ruxsat (mobile uchun)
CORS_ALLOW_ALL=True

# HTTPS forced
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000

# Sentry (xato kuzatuv)
SENTRY_DSN=<https://...@sentry.io/...>
```

### 3.2 PostgreSQL o'rnatish (SQLite NOT for production!)
```bash
sudo apt install postgresql-16 postgresql-contrib
sudo -u postgres psql -c "CREATE DATABASE togai;"
sudo -u postgres psql -c "CREATE USER togai WITH PASSWORD 'STRONG_PASS';"
sudo -u postgres psql -c "ALTER ROLE togai SET client_encoding TO 'utf8';"
sudo -u postgres psql -c "ALTER ROLE togai SET default_transaction_isolation TO 'read committed';"
sudo -u postgres psql -c "ALTER ROLE togai SET timezone TO 'Asia/Tashkent';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE togai TO togai;"
```

### 3.3 Redis o'rnatish
```bash
sudo apt install redis-server
sudo systemctl enable redis-server
redis-cli ping  # PONG javobi kelishi kerak
```

### 3.4 Migrations va seed
```bash
cd /var/www/togai-backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn celery redis psycopg2-binary

python manage.py migrate
python manage.py collectstatic --noinput

# Ma'lumotlar bazasini to'ldirish — MAJBURIY!
python manage.py seed_redbook        # 103 Qizil kitob species
python manage.py seed_shop           # 31 sayohat anjomi
```

---

## 🚀 4. GUNICORN + CELERY — production server

### 4.1 systemd service `/etc/systemd/system/togai-web.service`
```ini
[Unit]
Description=BioScan Django (Gunicorn)
After=network.target postgresql.service redis-server.service

[Service]
User=togai
Group=togai
WorkingDirectory=/var/www/togai-backend
EnvironmentFile=/var/www/togai-backend/.env
ExecStart=/var/www/togai-backend/venv/bin/gunicorn togai.wsgi:application \
    --bind 127.0.0.1:8000 \
    --workers 4 \
    --threads 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 4.2 Celery worker `/etc/systemd/system/togai-celery.service`
```ini
[Unit]
Description=BioScan Celery worker
After=redis-server.service

[Service]
User=togai
Group=togai
WorkingDirectory=/var/www/togai-backend
EnvironmentFile=/var/www/togai-backend/.env
ExecStart=/var/www/togai-backend/venv/bin/celery -A togai worker --loglevel=info --concurrency=2
Restart=always

[Install]
WantedBy=multi-user.target
```

### 4.3 Telegram OTP bot (webhook rejimi)
**Webhook URL'ini bir marta sozlash:**
```bash
curl -X POST "https://api.telegram.org/bot<OTP_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://api.bioscan.uz/api/bot/webhook/","allowed_updates":["message"]}'
```

---

## ⚡ 5. PERFORMANCE OPTIMIZATSIYA

### 5.1 Database indekslar (postgres)
```sql
-- Tez-tez ishlatiladigan filterlar
CREATE INDEX idx_species_red_book ON catalog_species(red_book) WHERE red_book = true;
CREATE INDEX idx_species_category ON catalog_species(category);
CREATE INDEX idx_observations_user ON observations_observation(user_id, created_at DESC);
CREATE INDEX idx_observations_geo ON observations_observation(latitude, longitude) WHERE latitude IS NOT NULL;
CREATE INDEX idx_shop_active ON shop_product(status, is_featured) WHERE status = 'active';
```

### 5.2 Django settings — production
```python
# settings.py — bularni yoqing
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {"db": "1"},
    }
}

MIDDLEWARE = [
    "django.middleware.gzip.GZipMiddleware",  # ENG BIRINCHI — javoblarni siqadi
    "corsheaders.middleware.CorsMiddleware",
    # ... qolganlari
]

# Database connection pooling
DATABASES["default"]["CONN_MAX_AGE"] = 600  # 10 daqiqa connection re-use
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True

# Static files cache (1 yil)
WHITENOISE_MAX_AGE = 31536000
```

### 5.3 Image proxy (catalog rasmlari uchun)
- Serializer'da `images.weserv.nl` ishlatish (allaqachon kod ichida bor)
- Bu iNaturalist rasmlarini Cloudflare CDN orqali keshlaydi
- 6s → 0.5s rasm yuklanish

### 5.4 OpenRouter vision modellari (tez)
```python
# integrations.py vision_models()
return [
    "openai/gpt-4o-mini",                       # 3-5s, $$
    "qwen/qwen2.5-vl-72b-instruct",             # 5-7s, $
    "meta-llama/llama-3.2-11b-vision-instruct", # 7-10s, $
]
```

---

## 📡 6. FLUTTER ENDPOINT MAP — bularni qo'llab-quvvatlash kerak

### 6.1 Auth
- `POST /api/auth/quick/` — ⚠️ DEV uchun, production'da o'chiring
- `POST /api/auth/otp/request/` — SMS OTP
- `POST /api/auth/tg-otp/request/` — Telegram OTP (asosiy)
- `POST /api/auth/otp/verify/`
- `POST /api/auth/token/refresh/`
- `GET /api/auth/me/`
- `PATCH /api/auth/me/`

### 6.2 Catalog (species)
- `GET /api/species/?red_book=true&category=giyoh&search=yantoq&page=1`
- `GET /api/species/{slug}/`

### 6.3 Observations (skan)
- `POST /api/observations/scan/` (multipart photo)
- `GET /api/observations/`
- `GET /api/observations/public/`
- `GET /api/observations/yearbook/?year=2026` (PDF)

### 6.4 Map / Search / Chat
- `GET /api/map/markers/?type=danger`
- `GET /api/search/taxa/?q=yantoq`
- `GET /api/search/wiki/?title=Alhagi`
- `GET /api/search/enrich/?name=Alhagi+pseudalhagi`
- `POST /api/chat/ai/` (public)
- `GET/POST /api/chat/conversations/` (auth)

### 6.5 Shop (Bozor)
- `GET /api/shop/categories/`
- `GET /api/shop/products/?category=chodir&page=1`
- `GET /api/shop/products/{id}/`
- `GET/POST /api/shop/cart/`, `/cart/add/`, `/cart/clear/`
- `GET /api/shop/orders/`, `POST /shop/orders/checkout/`
- `GET/POST /api/shop/wishlist/`

### 6.6 Bot webhook
- `POST /api/bot/webhook/` — Telegram updates pushed here

---

## ✅ 7. TEKSHIRUV (validation checklist)

Backend tayyorligini tekshirish:
```bash
# 1. Health
curl -s https://api.bioscan.uz/api/health/?deep=1
# kutilgan: {"status":"ok","checks":{"db":{"ok":true},"cache":{"ok":true}}}

# 2. Catalog 100+ species
curl -s 'https://api.bioscan.uz/api/species/?red_book=true' | jq '.count'
# kutilgan: 100+

# 3. Shop 30+ product
curl -s 'https://api.bioscan.uz/api/shop/products/?page=1' | jq '.count'
# kutilgan: 30+

# 4. Gzip ishlayaptimi
curl -s -I -H 'Accept-Encoding: gzip' https://api.bioscan.uz/api/species/ | grep -i encoding
# kutilgan: content-encoding: gzip

# 5. HTTPS sertifikat
curl -sI https://api.bioscan.uz/api/health/ | head -3
# kutilgan: HTTP/2 200

# 6. Latency (Toshkent'dan)
time curl -s https://api.bioscan.uz/api/health/
# kutilgan: < 300ms

# 7. AI scan
echo "test" | curl -X POST -F "photo=@plant.jpg" https://api.bioscan.uz/api/observations/scan/
# kutilgan: identified: true (5-10s)

# 8. Telegram bot webhook
curl -s "https://api.telegram.org/bot<TOKEN>/getWebhookInfo" | jq .result.url
# kutilgan: "https://api.bioscan.uz/api/bot/webhook/"
```

---

## 📈 8. KUTILGAN NATIJA

| Metrika | Hozir (Vercel proxy) | TZ'dan keyin |
|---|---|---|
| API latency | 500-700ms | **100-200ms** |
| Catalog yuklash | 3-5s | **0.5-1s** |
| Skan AI | 9-12s | **5-8s** |
| Bozor sahifa | 4-6s | **1-2s** |
| Birinchi ochilish | 3-4s | **<1s** (cache) |

---

## 🚨 9. MUHIM — APK URL ALMASHISH

Backend tayyor bo'lgach, menga **bitta** URL bering:

```
https://api.bioscan.uz/api
```

Men `lib/src/core/api.dart` da quyidagini almashtaraman:
```dart
const String defaultApiBase = 'https://api.bioscan.uz/api';
```

Va yangi APK quraman. Hammasi 3-5x tezroq bo'ladi.

---

**Yozildi:** BioScan Backend Team
**Sana:** 2026-05-07
**Versiya:** 1.0
