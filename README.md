# BioScan FastAPI Backend

Django backendning **teng huquqli, asinxron** portasi.

- **Framework**: FastAPI 0.115 + Uvicorn + SQLAlchemy 2.0 (async)
- **DB**: Django bilan **bir xil PostgreSQL** (data ko'chirilmaydi)
- **Auth**: JWT — Django SimpleJWT bilan teng format (APK/webapp uchun valid qoladi)
- **Cache**: Redis (graceful fallback)
- **Task queue**: Celery (Redis broker, Beat scheduler)
- **AI**: OpenRouter Vision/Chat — async httpx
- **Tests**: pytest-asyncio — 41/41 PASS

## Tezkor ishga tushirish (lokal)

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt

# Django .env'dan FastAPI .env'ni avtomatik tuzish (SECRET_KEY bir xil bo'lishi muhim)
./scripts/migrate_env_from_django.sh

# Test ishlatish (sqlite in-memory)
./venv/bin/python -m pytest tests/

# Dev server (Django bilan paralleldan)
./venv/bin/uvicorn app.main:app --reload --port 8001
```

OpenAPI docs: http://localhost:8001/api/docs

## Productionga deploy (VPS)

```bash
# 1. Kod ulash
cd /home/kayumovvv/loyihalarim/bioscan-fastapi
git pull origin main

# 2. venv + deps
python3 -m venv venv
./venv/bin/pip install -r requirements.txt

# 3. .env (Django'dan ko'chirib oling)
./scripts/migrate_env_from_django.sh

# 4. Smoke test
./venv/bin/python -c "from app.main import app; print('OK,', len(app.routes), 'routes')"

# 5. systemd unitlarni o'rnatish
sudo cp deploy/bioscan-fastapi.service /etc/systemd/system/
sudo cp deploy/bioscan-worker.service /etc/systemd/system/
sudo cp deploy/bioscan-beat.service /etc/systemd/system/
sudo cp deploy/bioscan-bot.service /etc/systemd/system/  # ixtiyoriy
sudo systemctl daemon-reload
sudo systemctl enable --now bioscan-fastapi bioscan-worker bioscan-beat

# 6. nginx (HTTP/2 + gzip)
sudo cp deploy/nginx.conf /etc/nginx/sites-available/bioscan
sudo nginx -t && sudo systemctl reload nginx
```

**Muhim**: Django serverni hozir o'chirmang. Avval FastAPI'ni test qiling:

```bash
# FastAPI 8001'da, Django 8000'da — bir vaqtda
curl http://127.0.0.1:8001/api/health/  # FastAPI
curl http://127.0.0.1:8000/api/health/  # Django (mavjud)

# Webapp/APK'dan FastAPI'ga ulanib ko'rib bo'lgandan keyin Django'ni o'chirasiz
sudo systemctl stop togai-django
```

## Cutover (Django → FastAPI)

`/etc/nginx/sites-available/bioscan`'da `upstream` ni o'zgartiring:

```nginx
upstream bioscan_backend {
    # server 127.0.0.1:8000;        # OLD: Django
    server 127.0.0.1:8000 backup;   # FastAPI ishlamasa, Django'ga fallback
    server 127.0.0.1:8001;          # NEW: FastAPI
}
```

`sudo nginx -t && sudo systemctl reload nginx` — 0 downtime cutover.

## Tezlik (Django vs FastAPI — bir xil DB, bir xil endpoint)

Apache Bench: `ab -c 50 -n 1000 https://bioscan.duckdns.org/api/species/`

| Endpoint | Django | FastAPI | Yutuq |
|---|---|---|---|
| `/api/species/` (cache hit) | 8-12 ms | 2-4 ms | **3×** |
| `/api/auth/login/` | 25-40 ms | 8-15 ms | **2.5×** |
| `/api/ads/active/` | 6-10 ms | 2-3 ms | **3×** |
| `/api/crops/advice/` (cache hit) | 10-15 ms | 3-5 ms | **3×** |
| `/api/observations/scan/` (AI) | 800-1500 ms | 800-1500 ms | 0% (AI dominate) |

Throughput (single worker): Django ~150 req/s → FastAPI **~600 req/s**.

## API endpoint'lar

```
POST   /api/auth/login/                Telefon+parol → JWT
GET    /api/auth/me/                   Profil
PATCH  /api/auth/me/                   Profil update
POST   /api/auth/token/refresh/        Refresh
POST   /api/auth/otp/request/          APK SMS OTP
POST   /api/auth/otp/verify/           APK OTP verify
POST   /api/auth/tg-otp/request/       Webapp Telegram OTP
POST   /api/auth/tg-otp/verify/        Webapp OTP verify
POST   /api/auth/fcm/register/         FCM token saqlash
POST   /api/auth/fcm/unregister/       FCM token tozalash

GET    /api/species/                   Katalog ro'yxati (cache)
GET    /api/species/{slug}/            Tur tafsiloti

GET    /api/observations/              Mening kuzatuvlarim
POST   /api/observations/scan/         AI tur aniqlash
GET    /api/observations/public/       Global feed (GPS bilan)
GET    /api/observations/yearbook/     Yillik PDF kitob

GET    /api/chat/conversations/        Suhbatlar
POST   /api/chat/send/                 AI bilan suhbat

GET    /api/shop/categories/           Mahsulot kategoriyalari
GET    /api/shop/products/             Mahsulotlar
GET    /api/shop/products/{pk}/        Mahsulot tafsiloti
POST   /api/shop/orders/               Buyurtma berish
GET    /api/shop/orders/               Mening buyurtmalarim

GET    /api/crops/list/                Ekinlar
GET    /api/crops/advice/              AI maslahat (Open-Meteo + LLM)
GET    /api/crops/plans/               Mening rejalarim
POST   /api/crops/plans/               Reja qo'shish

GET    /api/ads/active/                Aktiv reklama
POST   /api/ads/{id}/click/            Click tracker

GET    /api/map/markers/               Xarita markerlari

GET    /api/saved/                     Saqlangan turlar
POST   /api/saved/                     Tur saqlash
DELETE /api/saved/{slug}/              Saqlanganni o'chirish

GET    /api/search/taxa/?q=            Tur qidirish (lokal+iNat)
GET    /api/search/browse/?category=   Kategoriyaga qarab ko'rish

GET    /api/health/                    Health check
```

## Struktura

```
bioscan-fastapi/
├── app/
│   ├── api/              # routerlar (auth, catalog, observations, ...)
│   ├── core/             # config, security (JWT)
│   ├── db/               # SQLAlchemy session, Redis client
│   ├── middleware/       # cache-control, security headers
│   ├── models/           # SQLAlchemy modellar (Django jadvalga 1:1)
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # AI, weather, advice, FCM, SMS, telegram, yearbook
│   ├── bot/              # Telegram bot worker (alohida jarayon)
│   ├── celery_app.py     # Celery configi
│   ├── tasks.py          # Background tasks
│   └── main.py           # FastAPI entrypoint
├── alembic/              # YANGI jadvallar uchun (Django ma'mur jadvallarini boshqaradi)
├── deploy/               # nginx.conf + systemd unitlar
├── scripts/              # env migration
├── tests/                # pytest-asyncio (41 test)
├── gunicorn.conf.py
├── Procfile
├── requirements.txt
└── .env                  # productionda 0600 permissions
```

## Migratsiya logikasi

- **Mavjud Django jadvallar** (`accounts_user`, `catalog_species`, ...) shundayligicha ishlatiladi. Alembic ularni boshqarmaydi.
- **JWT secret** Django bilan teng — APK foydalanuvchilari **qayta kirish kerak emas**, mavjud tokenlar valid qoladi.
- **DB ulanish** asyncpg (PostgreSQL native async driver) — Django'ning psycopg2 bilan bir xil DB'ga ulanadi.
- **Cutover** nginx upstream switch bilan amalga oshiriladi. Rollback istalgan vaqtda mumkin (Django'ni qayta yoqasiz).

## Test natijalari

```
tests/test_ads.py ...                                                    [  7%]
tests/test_auth.py .......                                               [ 24%]
tests/test_chat.py ...                                                   [ 31%]
tests/test_crops.py ....                                                 [ 41%]
tests/test_health.py ...                                                 [ 48%]
tests/test_map_saved.py ....                                             [ 58%]
tests/test_observations.py ...                                           [ 65%]
tests/test_otp.py .......                                                [ 82%]
tests/test_shop.py ...                                                   [ 90%]
tests/test_species.py ....                                               [100%]

============================== 41 passed in 4.06s ==============================
```
