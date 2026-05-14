#!/usr/bin/env bash
# BioScan FastAPI — toza Postgres'dan to'liq sozlash (Django'siz).
#
# Bir buyruq bilan butun backend'ni ko'taradi:
#  1) venv yaratish + paketlar
#  2) .env mavjudligini tekshirish (yoki .env.example'dan ko'chirish)
#  3) Postgres'da jadval(lar) yaratish (Alembic upgrade head)
#  4) Seed data: 13 Region + 20 Crop + 20+ Species
#  5) Smoke test
#
# Ishlatish:
#     bash scripts/setup.sh
#     # yoki:
#     ./scripts/setup.sh

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# ---- 1. venv + paketlar ----
if [[ ! -d venv ]]; then
    echo "▶ venv yaratish..."
    python3 -m venv venv
fi
echo "▶ Paketlarni o'rnatish..."
./venv/bin/pip install -q --upgrade pip
./venv/bin/pip install -q -r requirements.txt

# ---- 2. .env tekshirish ----
if [[ ! -f .env ]]; then
    echo "⚠ .env yo'q — .env.example'dan ko'chirildi"
    cp .env.example .env
    chmod 600 .env
    echo "   ⚠ .env'ga real qiymatlarni qo'shing (DATABASE_URL, SECRET_KEY, OPENROUTER_API_KEY, ...)"
fi

# .env'ni yuklash
set -a; source .env; set +a

# ---- 3. Alembic upgrade head — Postgres'da jadvallar ----
echo "▶ Alembic upgrade head (jadvallar yaratish)..."
./venv/bin/alembic upgrade head

# ---- 4. Seed data ----
echo "▶ Seed boshlang'ich ma'lumotlarni yuklash..."
./venv/bin/python -m scripts.seed

# ---- 5. Smoke test ----
echo "▶ Smoke test (FastAPI ishlay oladimi)..."
./venv/bin/python -c "
from app.main import app
n = len([r for r in app.routes if hasattr(r, 'path')])
print(f'  ✓ {n} ta endpoint yuklandi')
"

echo ""
echo "✅ BioScan FastAPI tayyor!"
echo ""
echo "Ishga tushirish:"
echo "  ./venv/bin/uvicorn app.main:app --port 8001 --reload   # dev"
echo "  ./venv/bin/gunicorn -c gunicorn.conf.py app.main:app   # prod"
echo ""
echo "OpenAPI docs: http://localhost:8001/api/docs"
