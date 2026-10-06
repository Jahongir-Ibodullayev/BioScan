<div align="center">

# 🧬 BioScan Backend

**AI-powered nature & species identification — async FastAPI service**

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.136-009688?style=flat-square&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-DC382D?style=flat-square&logo=redis&logoColor=white)
![Tests](https://img.shields.io/badge/tests-41%2F41%20%E2%9C%85-22c55e?style=flat-square)
![License](https://img.shields.io/badge/license-Proprietary-6b7280?style=flat-square)

[![CI](https://github.com/Jahongir-Ibodullayev/BioScan/actions/workflows/ci.yml/badge.svg)](https://github.com/Jahongir-Ibodullayev/BioScan/actions/workflows/ci.yml)
[![Code style](https://img.shields.io/badge/ruff-line%20110-1c7ed6?style=flat-square&logo=ruff&logoColor=white)](pyproject.toml)

</div>

---

## 📖 Overview

BioScan backend is a **fully asynchronous, production-grade** port of the original Django service. It speaks to the **same PostgreSQL database**, so the mobile APK, web app and Telegram bot keep working without re-authentication.

| Metric | Django (before) | FastAPI (now) | Improvement |
|---|---:|---:|---:|
| `GET /api/species/` (cache hit) | 8–12 ms | **2–4 ms** | **3×** |
| `POST /api/auth/login/` | 25–40 ms | **8–15 ms** | **2.5×** |
| `GET /api/ads/active/` | 6–10 ms | **2–3 ms** | **3×** |
| Throughput (1 worker) | ~150 req/s | **~600 req/s** | **4×** |
| Test suite | — | **41/41 ✅** | — |

> AI endpoints (`/observations/scan/`, `/chat/send/`) are latency-bound by the
> upstream LLM provider — network time dominates, framework choice does not.

---

## ✨ Features

- **Async everything** — FastAPI + SQLAlchemy 2.0 async + `asyncpg` + Alembic
- **Zero-friction auth** — JWT compatible with Django SimpleJWT (existing tokens stay valid)
- **Multi-channel OTP** — SMS, Telegram WebApp OTP, FCM push tokens
- **Caching** — Redis with graceful fallback when Redis is unavailable
- **Background work** — Celery + Redis broker + Beat scheduler
- **AI** — OpenRouter Vision/Chat via `httpx`, Groq fallback
- **Observability** — Sentry traces, structured logs, config-warning banner at boot
- **Hardened HTTP** — CORS, GZip, cache-control and security-header middleware
- **Admin** — `sqladmin` panel

---

## 🛠️ Tech Stack

| Layer | Choice |
|---|---|
| Framework | FastAPI 0.136 · Uvicorn · Gunicorn |
| ORM / Migrations | SQLAlchemy 2.0 (async) · Alembic |
| Database | PostgreSQL (`asyncpg`) |
| Cache / Broker | Redis · Celery (+ Beat) |
| Auth | PyJWT · bcrypt |
| AI | OpenRouter · Groq |
| Push / Bot | Firebase Admin · python-telegram-bot |
| Monitoring | Sentry |
| Tests | pytest · pytest-asyncio · pytest-cov |
| Lint | ruff (line-length 110) |
| Deploy | nginx · systemd · Procfile |

---

## 🚀 Quick Start

```bash
git clone https://github.com/Jahongir-Ibodullayev/BioScan.git
cd BioScan
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

Create `.env` from the example (the `SECRET_KEY` must match Django's, otherwise existing JWTs break):

```bash
cp .env.example .env
./scripts/migrate_env_from_django.sh   # pulls values out of the Django .env
```

Run the test suite (in-memory SQLite, no external services needed):

```bash
./venv/bin/python -m pytest tests/ -q
# 41 passed in ~4s
```

Start the dev server:

```bash
./venv/bin/uvicorn app.main:app --reload --port 8001
```

Interactive API docs → <http://localhost:8001/api/docs>

---

## 🔌 API Surface

<details>
<summary><b>Auth</b> — 12 endpoints</summary>

```
POST   /api/auth/login/             phone + password → JWT
POST   /api/auth/token/refresh/     refresh rotation
GET    /api/auth/me/                current profile
PATCH  /api/auth/me/                update profile
POST   /api/auth/otp/request/       SMS OTP  (APK)
POST   /api/auth/otp/verify/
POST   /api/auth/tg-otp/request/    Telegram OTP (WebApp)
POST   /api/auth/tg-otp/verify/
POST   /api/auth/fcm/register/      save FCM token
POST   /api/auth/fcm/unregister/
```
</details>

<details>
<summary><b>Catalog & observations</b></summary>

```
GET    /api/species/                catalog (cached)
GET    /api/species/{slug}/
GET    /api/search/taxa/?q=         local + iNaturalist
GET    /api/search/browse/?category=
GET    /api/observations/           mine
POST   /api/observations/scan/      AI species ID
GET    /api/observations/public/    global GPS feed
GET    /api/observations/yearbook/  yearly PDF
GET    /api/saved/ · POST · DELETE  favourites
```
</details>

<details>
<summary><b>Business & AI</b></summary>

```
GET/POST /api/chat/*                AI conversation
GET      /api/crops/list/           crops
GET      /api/crops/advice/         AI advice (Open-Meteo + LLM)
GET/POST /api/crops/plans/          my plans
GET      /api/shop/*                categories, products, orders
GET      /api/seller/*              seller dashboard
GET      /api/ads/active/ · POST /api/ads/{id}/click/
GET      /api/map/markers/
GET      /api/incidents/*
GET      /api/health/               health check
```
</details>

---

## 🏗️ Architecture

```
BioScan/
├── app/
│   ├── api/          routers (auth, catalog, observations, shop, …)
│   ├── core/         config, security (JWT)
│   ├── db/           async engine, session factory, Redis client
│   ├── middleware/   cache-control, security headers, CORS, GZip
│   ├── models/       SQLAlchemy models — 1:1 with Django tables
│   ├── schemas/      Pydantic request/response schemas
│   ├── services/     AI, weather, advice, FCM, SMS, Telegram, yearbook
│   ├── bot/          Telegram bot worker (separate process)
│   ├── celery_app.py Celery configuration
│   ├── tasks.py      background tasks
│   └── main.py       FastAPI entrypoint + lifespan
├── alembic/          NEW tables only (Django owns the legacy ones)
├── deploy/           nginx.conf + systemd units
├── scripts/          env migration helpers
├── tests/            pytest-asyncio — 41 tests
├── gunicorn.conf.py
├── Procfile
└── pyproject.toml    deps, ruff, pytest, coverage config
```

### Migration strategy

- **Legacy Django tables** (`accounts_user`, `catalog_species`, …) are read/written as-is — Alembic does not manage them.
- **JWT secret is shared** with Django, so APK/webapp tokens remain valid — no forced re-login.
- **Same database** — data is never copied or migrated.
- **Cutover** happens by switching the nginx `upstream`, so rollback is a one-line revert:

```nginx
upstream bioscan_backend {
    server 127.0.0.0:8000 backup;   # Django (fallback)
    server 127.0.0.1:8001;           # FastAPI (primary)
}
```

---

## 🧪 Testing

```bash
./venv/bin/python -m pytest tests/ -v
./venv/bin/python -m pytest --cov=app --cov-report=term-missing
```

```
tests/test_ads.py ............                                        [  7%]
tests/test_auth.py ...........                                        [ 24%]
tests/test_chat.py .......                                             [ 31%]
tests/test_crops.py ......                                             [ 41%]
tests/test_health.py .....                                             [ 48%]
tests/test_map_saved.py ......                                         [ 58%]
tests/test_observations.py .....                                       [ 65%]
tests/test_otp.py ........                                              [ 82%]
tests/test_shop.py ......                                              [ 90%]
tests/test_species.py ......                                           [100%]
============================== 41 passed in 4.06s ==============================
```

---

## 🐳 Deployment (VPS)

```bash
git pull origin main
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
./scripts/migrate_env_from_django.sh

sudo cp deploy/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now bioscan-fastapi bioscan-worker bioscan-beat bioscan-bot

sudo cp deploy/nginx.conf /etc/nginx/sites-available/bioscan
sudo nginx -t && sudo systemctl reload nginx
```

Smoke test:

```bash
./venv/bin/python -c "from app.main import app; print('OK,', len(app.routes), 'routes')"
curl -fsS http://127.0.0.1:8001/api/health/
```

> **Zero-downtime cutover:** keep Django running on `:8000` as `backup` while
> FastAPI serves `:8001`. If FastAPI dies, nginx falls back automatically.

---

## ⚙️ Configuration

Copy `.env.example` → `.env`. Missing optional services are reported as
**startup warnings** rather than silent failures.

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | **Must match Django** — JWT compatibility |
| `DATABASE_URL` | Shared PostgreSQL (asyncpg) |
| `REDIS_URL` / `CELERY_BROKER_URL` | Cache + task queue |
| `OPENROUTER_API_KEY` | AI scan / chat / crop advice |
| `TELEGRAM_BOT_TOKEN` | WebApp OTP + bot worker |
| `FCM_CREDENTIALS_PATH` | Push notifications |
| `SENTRY_DSN` | Error monitoring |

---

## 📂 Project Layout

See [`pyproject.toml`](pyproject.toml) for pinned dependency versions, ruff
rules and pytest configuration.

---

## 🤝 Contributing

1. Fork → feature branch → `pytest -q` must stay green
2. Follow `ruff` rules (line length 110)
3. Open a PR with a clear description

## 📄 License

Proprietary — see [`pyproject.toml`](pyproject.toml).
