# 📘 BioScan — Backend To'liq Texnik Topshiriq

**Loyiha:** BioScan (oldingi nom: Tog'AI) — Markaziy Osiyo flora/faunasini AI orqali aniqlash mobil ilovasi
**Versiya:** 1.0
**Sana:** 2026-05-07
**Frontend:** Flutter APK + Webapp (React)
**Backend:** Django REST Framework + PostgreSQL + Redis + Celery

---

## 📑 MUNDARIJA

1. [Infrastruktura va hosting](#1-infrastruktura)
2. [Domen, SSL, Nginx](#2-domen-ssl-nginx)
3. [Database — PostgreSQL](#3-postgresql)
4. [Cache va task queue — Redis + Celery](#4-redis--celery)
5. [Django sozlash](#5-django)
6. [AI integratsiya — OpenRouter](#6-openrouter-ai)
7. [Telegram bot — 2 ta bot](#7-telegram-bot)
8. [SMS gateway (ixtiyoriy)](#8-sms-gateway)
9. [Ma'lumot bazasini to'ldirish (seeding)](#9-seeding)
10. [Image handling va CDN](#10-image-cdn)
11. [API endpoint to'liq ro'yxati](#11-api-endpoints)
12. [Performance optimizatsiya](#12-performance)
13. [Monitoring va logging](#13-monitoring)
14. [Xavfsizlik](#14-security)
15. [Deploy va systemd servislari](#15-deploy)
16. [Acceptance criteria — qabul shartlari](#16-acceptance)
17. [Maintenance buyruqlari](#17-maintenance)

---

## 1. INFRASTRUKTURA

### 1.1 Server talablari
| Resurs | Minimum | **Tavsiya (production)** |
|---|---|---|
| RAM | 2 GB | **4 GB** |
| CPU | 2 vCPU | 4 vCPU |
| Disk | 20 GB SSD | 40 GB NVMe |
| Bandwidth | 1 TB/oy | 5 TB/oy |
| OS | Ubuntu 22.04 | **Ubuntu 24.04 LTS** |

### 1.2 Server lokatsiyasi (KRITIK)
**Toshkent'ga eng yaqin datacenter:**
- ✅ **Hetzner Helsinki** (FI) — 80-120ms latency, eng yaxshi narx
- ✅ **Hetzner Falkenstein** (DE) — 120-150ms
- ✅ **Vultr Frankfurt** (DE) — 130-160ms
- ✅ **DigitalOcean Frankfurt** — 130-160ms
- ⚠️ **Yandex Cloud Moskva** — 80-100ms (tezroq, lekin to'lov murakkab)
- ❌ AQSh, G'arbiy Yevropa, Yaponiya — 250-400ms (tashlash)

### 1.3 Boshlash narxi
- VPS: **$5-10/oy** (Hetzner CX22)
- Domen `.uz`: **~150 000 so'm/yil**
- SSL: **0 so'm** (Let's Encrypt bepul)
- **Jami: ~$10/oy + domen**

---

## 2. DOMEN, SSL, NGINX

### 2.1 Domen sozlash
**Tavsiya:** `bioscan.uz` yoki `api.bioscan.uz` subdomen

DNS A-record'lar:
```
A    bioscan.uz       <SERVER_IP>      TTL=300
A    api.bioscan.uz   <SERVER_IP>      TTL=300
A    www.bioscan.uz   <SERVER_IP>      TTL=300
```

### 2.2 SSL — Let's Encrypt (bepul, avtomatik yangilanadi)
```bash
sudo apt update
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d bioscan.uz -d api.bioscan.uz -d www.bioscan.uz
sudo systemctl enable certbot.timer
```

### 2.3 Nginx konfiguratsiya
**Fayl:** `/etc/nginx/sites-available/bioscan`

```nginx
# HTTP → HTTPS yo'naltirish
server {
    listen 80;
    server_name bioscan.uz www.bioscan.uz api.bioscan.uz;
    return 301 https://$host$request_uri;
}

# Asosiy HTTPS server
server {
    listen 443 ssl http2;
    server_name api.bioscan.uz;

    ssl_certificate     /etc/letsencrypt/live/bioscan.uz/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/bioscan.uz/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;
    ssl_session_cache   shared:SSL:10m;
    ssl_session_timeout 10m;

    # GZIP — javoblar 5x kichik
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 5;
    gzip_min_length 256;
    gzip_types
        application/json
        application/javascript
        application/xml
        text/css
        text/plain
        text/javascript
        image/svg+xml;

    keepalive_timeout 65;
    client_max_body_size 10M;
    client_body_timeout 90;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header Referrer-Policy "same-origin" always;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_redirect off;
        proxy_buffering off;
        proxy_read_timeout 120s;
        proxy_connect_timeout 30s;
    }

    # Static fayllar — uzoq cache
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

    # Health check — Nginx darajasida
    location = /nginx-health {
        return 200 'ok';
        add_header Content-Type text/plain;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/bioscan /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 3. POSTGRESQL

### 3.1 O'rnatish
```bash
sudo apt install -y postgresql-16 postgresql-contrib
sudo systemctl enable --now postgresql
```

### 3.2 Database yaratish
```bash
sudo -u postgres psql <<'SQL'
CREATE DATABASE togai;
CREATE USER togai WITH PASSWORD 'STRONG_PASSWORD_HERE';
ALTER ROLE togai SET client_encoding TO 'utf8';
ALTER ROLE togai SET default_transaction_isolation TO 'read committed';
ALTER ROLE togai SET timezone TO 'Asia/Tashkent';
GRANT ALL PRIVILEGES ON DATABASE togai TO togai;
\c togai
GRANT ALL ON SCHEMA public TO togai;
SQL
```

### 3.3 Performance tuning (postgresql.conf)
```ini
# /etc/postgresql/16/main/postgresql.conf
shared_buffers = 1GB              # RAM ning 1/4
effective_cache_size = 3GB        # RAM ning 3/4
work_mem = 16MB
maintenance_work_mem = 256MB
random_page_cost = 1.1            # SSD uchun
effective_io_concurrency = 200
max_connections = 100
```

---

## 4. REDIS + CELERY

### 4.1 Redis
```bash
sudo apt install -y redis-server
sudo systemctl enable --now redis-server
redis-cli ping  # PONG kelishi kerak
```

`/etc/redis/redis.conf` — production sozlash:
```ini
maxmemory 512mb
maxmemory-policy allkeys-lru
save ""                           # Cache uchun persistence kerak emas
appendonly no
```

### 4.2 Celery
- Broker: Redis DB 3
- Result backend: Redis DB 4
- Task queue (PDF generatsiya, email, async AI scan)

---

## 5. DJANGO

### 5.1 Repo
```bash
sudo mkdir -p /var/www
cd /var/www
sudo git clone <REPO_URL> togai-backend
sudo chown -R www-data:www-data togai-backend
cd togai-backend

sudo -u www-data python3 -m venv venv
sudo -u www-data ./venv/bin/pip install --upgrade pip
sudo -u www-data ./venv/bin/pip install -r requirements.txt
sudo -u www-data ./venv/bin/pip install gunicorn celery redis psycopg2-binary
```

### 5.2 `.env` fayl (`/var/www/togai-backend/.env`)
```env
# === Core ===
DJANGO_SECRET_KEY=<RANDOM 64 CHARS>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=api.bioscan.uz,bioscan.uz,www.bioscan.uz

# === Database ===
USE_POSTGRES=True
DB_NAME=togai
DB_USER=togai
DB_PASSWORD=<STRONG_PASSWORD>
DB_HOST=127.0.0.1
DB_PORT=5432

# === Redis / Celery ===
REDIS_URL=redis://127.0.0.1:6379/1
CELERY_BROKER_URL=redis://127.0.0.1:6379/3
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/4

# === HTTPS / Security ===
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000

# === CORS ===
CORS_ALLOW_ALL=False
FRONTEND_URL=https://bioscan.uz

# === AI — OpenRouter (asosiy) ===
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_REFERER=https://bioscan.uz
OPENROUTER_TITLE=BioScan

# === AI — Groq (fallback) ===
GROQ_API_KEY=

# === Telegram bot — 2 ta alohida ===
TELEGRAM_BOT_TOKEN=<MAIN_BOT_TOKEN>
TELEGRAM_BOT_USERNAME=<bot_username>
TELEGRAM_OTP_BOT_TOKEN=<OTP_BOT_TOKEN>
TELEGRAM_OTP_BOT_USERNAME=TogOTP_bot

# === SMS (ixtiyoriy — yo'q bo'lsa Telegram OTP) ===
SMS_PROVIDER=eskiz                # console|eskiz|playmobile
SMS_ESKIZ_EMAIL=<email>
SMS_ESKIZ_PASSWORD=<password>

# === Sentry (xato kuzatuv) ===
SENTRY_DSN=
SENTRY_ENV=production
```

### 5.3 Migration va static fayllar
```bash
cd /var/www/togai-backend
source venv/bin/activate

python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser    # admin uchun
```

---

## 6. OPENROUTER AI

### 6.1 Hisob
1. https://openrouter.ai → ro'yxatdan o'ting
2. Balansga $5-10 to'ldiring (test uchun yetadi)
3. API key oling: `sk-or-v1-...`
4. `.env` ga qo'shing: `OPENROUTER_API_KEY=sk-or-v1-...`

### 6.2 Ishlatiladigan modellar (verified — ishlaydi)
**Vision (rasm tanish):**
- `openai/gpt-4o-mini` (asosiy, 5-7s, ~$0.001/scan)
- `qwen/qwen2.5-vl-72b-instruct` (zaxira, 5-9s)
- `meta-llama/llama-3.2-11b-vision-instruct` (tezkor fallback)

**Chat:**
- `meta-llama/llama-3.3-70b-instruct` (asosiy AI suhbat)

**Translate:**
- Avtomatik chat_model() (ingliz/rus → o'zbek)

### 6.3 Vision sozlash (`integrations.py`)
- Rasm avtomatik 768px ga siqiladi (3-4x tez upload)
- Quality 78 (yetarli, kichik fayl)
- 25 sek timeout har model uchun
- Birinchi muvaffaqiyatli javob g'oliblik qiladi

### 6.4 Token sarfi (oylik prognoz)
- 1000 ta scan = ~$1.5
- 5000 ta chat = ~$2
- **Boshlash uchun $10 yetadi**

---

## 7. TELEGRAM BOT

### 7.1 Ikki bot kerak
1. **Asosiy bot** (`@bioscan_uz_bot` yoki shunga o'xshash) — webapp, ilovani ochish, yordam
2. **OTP bot** (`@TogOTP_bot` yoki `@bioscan_otp_bot`) — FAQAT login kodlarini yuborish

@BotFather'da `/newbot` orqali ikkita bot yarating, ikkita token oling.

### 7.2 Webhook sozlash (POLLING EMAS!)
**Polling 409 Conflict beradi** ikki instance ishlasa. Webhook — yagona to'g'ri yechim.

```bash
# OTP bot uchun:
curl -X POST "https://api.telegram.org/bot<OTP_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://api.bioscan.uz/api/bot/webhook/",
    "allowed_updates": ["message"]
  }'

# Tasdiqlash:
curl "https://api.telegram.org/bot<OTP_BOT_TOKEN>/getWebhookInfo"
```

### 7.3 Bot funksiyasi
- Foydalanuvchi `/start` yoki `/login` ga bossa → "Telefon raqamini ulashish" tugmasini ko'rsatadi
- Telefon ulagandan keyin `User.telegram_id` saqlanadi
- API'ga `/auth/tg-otp/request/` chaqirilganda → 6 xonali kod shu bot orqali yuboriladi
- Kod 2 daqiqa amal qiladi

### 7.4 Asosiy bot (ixtiyoriy)
Agar ishlatilsa — webapp tugmasi, AI scan rasmni qabul qilish, ilon ogohlantirish va h.k.

---

## 8. SMS GATEWAY (IXTIYORIY)

Telegram OTP yetarli. Lekin SMS qo'shimcha kerak bo'lsa:

### 8.1 Eskiz.uz (O'zbekiston)
- 1 SMS = ~95 so'm
- Hisob ochish: https://my.eskiz.uz
- Sender ID tasdiqlash kerak (1-2 ish kuni)
- `.env`:
```env
SMS_PROVIDER=eskiz
SMS_ESKIZ_EMAIL=<email>
SMS_ESKIZ_PASSWORD=<password>
```

### 8.2 Muqobil — PlayMobile, SmsHub
Eskiz emas bo'lsa, integratsiyani `togai/integrations.py` da `send_sms()` funksiyasiga qo'shing.

---

## 9. SEEDING — bazani to'ldirish

### 9.1 Avtomatik seed buyruqlari
```bash
cd /var/www/togai-backend
source venv/bin/activate

python manage.py seed_redbook         # 100+ Qizil kitob species
python manage.py seed_shop            # 31 sayohat anjomi (Uzum link bilan)
```

### 9.2 Qo'shimcha — kengroq Qizil kitob (500+ tur)
- `catalog/management/commands/seed_redbook.py` faylini kengaytiring
- Yoki JSON fayl tayyorlab `import_redbook_json` script orqali import qiling
- Manba: O'zbekiston Qizil kitobi 4-nashri (2019)
- Tafsilot: `REDBOOK_TZ.md` (alohida fayl)

### 9.3 Kategoriyalar minimum:
| Kategoriya | Minimum |
|---|---|
| Gullar | 25 |
| Daraxtlar | 15 |
| Giyohlar | 20 |
| Sutemizuvchilar | 15 |
| Qushlar | 15 |
| Ilonlar/sudralib | 5 |
| Baliqlar | 5 |

---

## 10. IMAGE / CDN

### 10.1 Catalog rasm proxy
**Allaqachon kod ichida bor** (`catalog/serializers.py`):
- iNaturalist/Wikimedia URL'larini `images.weserv.nl` orqali proxy qiladi
- Cloudflare CDN'da keshlanadi
- Toshkent'da 6s → 0.5s (12x tezroq)

### 10.2 Foydalanuvchi yuklagan fayllar
- `MEDIA_ROOT = /var/www/togai-backend/media/`
- Nginx static (1 yil cache)
- Skan rasmlari: `/media/observations/`
- Profil avatar: `/media/avatars/`

### 10.3 Cloudflare oldida (ixtiyoriy, bepul)
1. https://cloudflare.com da hisob oching
2. `bioscan.uz` ni qo'shing
3. DNS'ni Cloudflare'ga ko'chiring
4. SSL/TLS: "Full (strict)"
5. Caching → "Standard"
6. Speed → "Brotli on", "Auto Minify"

**Foyda:** Static fayllar + JSON javoblar global CDN'da keshlanadi → tezlik 2-3x oshadi.

---

## 11. API ENDPOINTS — to'liq ro'yxat

Flutter chaqiradigan barcha endpoint'lar (har biri ishlamoqda):

### 11.1 Sog'lomlik
```
GET  /api/health/               — quick check
GET  /api/health/?deep=1        — DB + cache check
```

### 11.2 Auth (telefon + Telegram OTP)
```
POST /api/auth/quick/                  — DEV only (ENV'da o'chirilsin)
POST /api/auth/otp/request/            — SMS OTP
POST /api/auth/otp/verify/             — Kod tasdiqlash
POST /api/auth/tg-otp/request/         — Telegram OTP (asosiy)
POST /api/auth/token/refresh/          — JWT yangilash
GET  /api/auth/me/                     — Profil
PATCH /api/auth/me/                    — Profil yangilash
```

### 11.3 Catalog (species)
```
GET /api/species/                      — Ro'yxat (filterlar)
GET /api/species/?red_book=true        — Faqat Qizil kitob
GET /api/species/?category=gul         — Kategoriya
GET /api/species/?search=yantoq        — Qidiruv
GET /api/species/{slug}/               — Detail
```

### 11.4 Observations (skan)
```
POST /api/observations/scan/           — AI rasm tanish (multipart)
GET  /api/observations/                — Mening kuzatuvlarim
GET  /api/observations/public/         — Hammaning skanlari (xarita)
GET  /api/observations/yearbook/?year=2026  — Yillik PDF kitob
```

### 11.5 Map / Search / Chat
```
GET /api/map/markers/                  — Xavf hududlari
GET /api/search/taxa/?q=yantoq         — iNaturalist
GET /api/search/taxa/{id}/             — Detail
GET /api/search/wiki/?title=Alhagi     — Wikipedia (uz/ru/en)
GET /api/search/enrich/?name=...       — AI tavsif
GET /api/search/gbif/?q=...            — GBIF biodiversity

POST /api/chat/ai/                     — Public AI suhbat
GET  /api/chat/conversations/          — Suhbat tarixi (auth)
POST /api/chat/conversations/ask/      — Auth chat
```

### 11.6 Shop (Bozor)
```
GET /api/shop/categories/              — Kategoriyalar
GET /api/shop/products/                — Mahsulotlar (filter)
GET /api/shop/products/{id}/           — Detail
GET /api/shop/cart/                    — Savat
POST /api/shop/cart/add/               — Savatga qo'shish
POST /api/shop/cart/clear/             — Tozalash
GET /api/shop/orders/                  — Buyurtmalar
POST /api/shop/orders/checkout/        — To'lov
GET /api/shop/wishlist/                — Sevimlilar
POST /api/shop/wishlist/               — Qo'shish
GET /api/shop/reviews/?product=X       — Sharhlar
POST /api/shop/reviews/                — Sharh yozish
```

### 11.7 Incidents (xavf hisoboti)
```
GET /api/incidents/                    — Hisobotlar
POST /api/incidents/                   — Yangi hisobot (auth)
```

### 11.8 Collections (sevimlilar)
```
GET /api/collections/                  — Mening kolleksiyam
POST /api/collections/                 — Qo'shish
DELETE /api/collections/{id}/          — O'chirish
```

### 11.9 Telegram bot webhook
```
POST /api/bot/webhook/                 — Telegram → bizga update
```

---

## 12. PERFORMANCE

### 12.1 Indekslar (PostgreSQL)
```sql
CREATE INDEX idx_species_red_book ON catalog_species(red_book) WHERE red_book = true;
CREATE INDEX idx_species_category ON catalog_species(category);
CREATE INDEX idx_species_search ON catalog_species USING gin(to_tsvector('simple', name || ' ' || latin || ' ' || summary));
CREATE INDEX idx_obs_user_time ON observations_observation(user_id, created_at DESC);
CREATE INDEX idx_obs_geo ON observations_observation(latitude, longitude) WHERE latitude IS NOT NULL;
CREATE INDEX idx_shop_active ON shop_product(status, is_featured) WHERE status = 'active';
CREATE INDEX idx_user_phone ON accounts_user(phone);
CREATE INDEX idx_user_tg ON accounts_user(telegram_id) WHERE telegram_id IS NOT NULL;
```

### 12.2 Settings.py optimizatsiya
```python
DATABASES["default"]["CONN_MAX_AGE"] = 600
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
    }
}

MIDDLEWARE = [
    "django.middleware.gzip.GZipMiddleware",      # ENG BIRINCHI
    "corsheaders.middleware.CorsMiddleware",
    # ...
]

WHITENOISE_MAX_AGE = 31536000
```

### 12.3 Kutilgan tezliklar
| Endpoint | Hozir | TZ'dan keyin |
|---|---|---|
| `/api/health/` | 50ms | 30ms |
| `/api/species/?red_book=true` | 800ms | **150ms** |
| `/api/shop/products/` | 1.2s | **200ms** |
| `/api/observations/scan/` (AI) | 12s | **6-8s** |
| `/api/chat/ai/` | 3s | 2s |

---

## 13. MONITORING

### 13.1 Sentry (xato kuzatuv) — bepul
1. https://sentry.io ro'yxatdan o'ting
2. Yangi project yarating (Django)
3. DSN oling
4. `.env`: `SENTRY_DSN=https://...@sentry.io/...`
5. Avtomatik xatolarni qabul qiladi

### 13.2 Server monitoring (ixtiyoriy)
- **Netdata** — bepul, real-time CPU/RAM/disk
- **UptimeRobot** — bepul HTTP ping har 5 daqiqa
- **Better Stack** — mavjud + alerting

### 13.3 Loglar
```bash
# Django log
sudo journalctl -u togai-web -f

# Nginx access log
sudo tail -f /var/log/nginx/access.log

# Celery
sudo journalctl -u togai-celery -f
```

---

## 14. SECURITY

### 14.1 Server
- ✅ SSH parol o'rniga **SSH key** ishlatish
- ✅ `ufw` firewall: faqat 22 (SSH), 80, 443 ochiq
- ✅ Fail2ban: SSH brute force himoyasi
- ✅ Avtomatik update: `sudo apt install unattended-upgrades`

### 14.2 Django
- ✅ `DEBUG=False` (production'da)
- ✅ `SECRET_KEY` — yangi tasodifiy 64 char
- ✅ `ALLOWED_HOSTS` — faqat to'g'ri domenlar
- ✅ HTTPS forced
- ✅ JWT token expiry: 6 soat (access), 30 kun (refresh)

### 14.3 Throttling
- ✅ Auth: 10/min/IP
- ✅ Scan: 10/min anon
- ✅ AI chat: 20/min user
- (Hozir kod ichida bor — `togai/throttles.py`)

### 14.4 Backup
**Har kuni avtomatik DB backup:**
```bash
# /etc/cron.daily/togai-backup
#!/bin/bash
DATE=$(date +%Y%m%d)
sudo -u postgres pg_dump togai | gzip > /var/backups/togai-$DATE.sql.gz
find /var/backups -name 'togai-*.sql.gz' -mtime +30 -delete
```

---

## 15. DEPLOY (systemd)

### 15.1 Gunicorn `/etc/systemd/system/togai-web.service`
```ini
[Unit]
Description=BioScan Django (Gunicorn)
After=network.target postgresql.service redis-server.service

[Service]
User=www-data
Group=www-data
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

### 15.2 Celery `/etc/systemd/system/togai-celery.service`
```ini
[Unit]
Description=BioScan Celery worker
After=redis-server.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/togai-backend
EnvironmentFile=/var/www/togai-backend/.env
ExecStart=/var/www/togai-backend/venv/bin/celery -A togai worker \
    --loglevel=info --concurrency=2
Restart=always

[Install]
WantedBy=multi-user.target
```

### 15.3 Yoqish
```bash
sudo systemctl daemon-reload
sudo systemctl enable togai-web togai-celery
sudo systemctl start togai-web togai-celery
sudo systemctl status togai-web togai-celery
```

---

## 16. ACCEPTANCE — qabul qilish shartlari

Backend tayyor deb hisoblash uchun **HAR BIRI ishlashi shart**:

```bash
# 1. HTTPS + Health
curl -s https://api.bioscan.uz/api/health/?deep=1
# expected: {"status":"ok","checks":{"db":{"ok":true},"cache":{"ok":true}}}

# 2. Latency Toshkent'dan < 300ms
time curl -s https://api.bioscan.uz/api/health/

# 3. Gzip ishlamoqda
curl -sI -H 'Accept-Encoding: gzip' https://api.bioscan.uz/api/species/ | grep -i content-encoding
# expected: content-encoding: gzip

# 4. 100+ Qizil kitob species
curl -s 'https://api.bioscan.uz/api/species/?red_book=true' | jq .count
# expected: >= 100

# 5. 30+ shop product
curl -s 'https://api.bioscan.uz/api/shop/products/' | jq .count
# expected: >= 30

# 6. Scan AI ishlaydi (5-10s)
curl -X POST -F "photo=@plant.jpg" https://api.bioscan.uz/api/observations/scan/ -m 30
# expected: {"identified": true, "species": {...}}

# 7. Telegram OTP webhook
curl -s "https://api.telegram.org/bot<OTP_TOKEN>/getWebhookInfo" | jq .result.url
# expected: "https://api.bioscan.uz/api/bot/webhook/"

# 8. PostgreSQL ishlaydi
sudo -u postgres psql -d togai -c "SELECT count(*) FROM catalog_species;"
# expected: 100+

# 9. Redis ishlaydi
redis-cli ping
# expected: PONG

# 10. Image proxy
curl -sI "$(curl -s 'https://api.bioscan.uz/api/species/?red_book=true' | jq -r '.results[0].picture')" | head -1
# expected: HTTP/2 200
```

---

## 17. MAINTENANCE — kunlik buyruqlar

### 17.1 Restart
```bash
sudo systemctl restart togai-web togai-celery
sudo systemctl reload nginx
```

### 17.2 Loglar tekshirish
```bash
sudo journalctl -u togai-web -n 100 --no-pager
sudo journalctl -u togai-celery -n 100 --no-pager
```

### 17.3 Yangi seed
```bash
cd /var/www/togai-backend && source venv/bin/activate
python manage.py seed_redbook       # Qizil kitob
python manage.py seed_shop          # Bozor
```

### 17.4 Migration
```bash
git pull
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart togai-web togai-celery
```

### 17.5 Cache tozalash
```bash
redis-cli FLUSHDB
```

### 17.6 Backup tiklash
```bash
gunzip < /var/backups/togai-20260507.sql.gz | sudo -u postgres psql togai
```

---

## ⚙️ MENGA YUBORILADIGAN MA'LUMOT

Backend tayyor bo'lgach, Flutter tomonida **bitta narsa** kerak:

```
URL: https://api.bioscan.uz/api
```

Men `lib/src/core/api.dart` da:
```dart
const String defaultApiBase = 'https://api.bioscan.uz/api';
```

deb yozaman va yangi APK quraman.

---

**📞 Aloqa:**
- Frontend (Flutter + Webapp): mendan so'rang
- Backend: serverda ishlovchi developer
- Domen/SSL: hosting provider
- AI/OpenRouter: hisobni siz yaratasiz, key beriladi

---

**Hujjatlar:**
- `MASTER_BACKEND_TZ.md` — bu fayl (umumiy)
- `BACKEND_TZ_FOR_FLUTTER_SPEED.md` — alohida tezlik bo'yicha
- `REDBOOK_TZ.md` — alohida Qizil kitob seeding bo'yicha

---

**Versiya:** 1.0
**Sana:** 2026-05-07
