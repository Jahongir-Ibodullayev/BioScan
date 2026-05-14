#!/usr/bin/env bash
# BioScan production deploy — VPS'da bir buyruq bilan
# Ishlatish (VPS root yoki sudo bilan):
#   curl -fsSL https://raw.githubusercontent.com/otabekqayumov762-collab/tog-ai-back/main/scripts/deploy_vps.sh | bash
# yoki lokal:
#   bash scripts/deploy_vps.sh

set -euo pipefail

REPO_URL="https://github.com/otabekqayumov762-collab/tog-ai-back.git"
DEPLOY_DIR="/var/www/bioscan-api"
BRANCH="main"

log() { echo -e "\n\033[1;36m▶ $*\033[0m"; }
ok()  { echo -e "  \033[1;32m✓ $*\033[0m"; }
err() { echo -e "  \033[1;31m✗ $*\033[0m" >&2; }

# ---- 1. Repo ----
log "Repo clone/pull..."
if [[ -d "$DEPLOY_DIR/.git" ]]; then
    cd "$DEPLOY_DIR" && git fetch --all -q && git reset --hard origin/$BRANCH
else
    sudo mkdir -p "$DEPLOY_DIR"
    sudo chown -R "$USER:$USER" "$DEPLOY_DIR"
    git clone -q -b "$BRANCH" "$REPO_URL" "$DEPLOY_DIR"
    cd "$DEPLOY_DIR"
fi
ok "Code: $(git log -1 --oneline)"

# ---- 2. venv + deps ----
log "Python venv + paketlar..."
[[ -d venv ]] || python3 -m venv venv
./venv/bin/pip install -q --upgrade pip
./venv/bin/pip install -q -r requirements.txt
ok "Deps OK"

# ---- 3. .env ----
log ".env tekshiruv..."
if [[ ! -f .env ]]; then
    if [[ -f /var/www/togai-backend/.env ]]; then
        # Eski Django .env'dan ko'chirish
        bash scripts/migrate_env_from_django.sh /var/www/togai-backend/.env .env
        ok ".env Django'dan ko'chirildi"
    else
        cp .env.example .env
        err ".env shablondan yaratildi — REAL QIYMATLARNI TO'LDIRING!"
        echo "    Tahrirlash: nano $DEPLOY_DIR/.env"
        exit 1
    fi
fi

# ---- 4. Schema (jadvallar mavjudligini tekshirish) ----
log "DB schema (mavjud Postgres'da)..."
set -a; source .env; set +a
./venv/bin/python -c "
import asyncio
from app.db.session import _get_engine, Base
from app import models  # noqa
async def go():
    engine = _get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
asyncio.run(go())
print('  ✓ Schema sync (yangi jadvallar yaratildi)')
"

# ---- 5. Smoke test ----
log "FastAPI smoke test..."
./venv/bin/python -c "
from app.main import app
n = len([r for r in app.routes if hasattr(r, 'path') and '/api/' in r.path])
print(f'  ✓ {n} ta endpoint yuklandi')
"

# ---- 6. systemd unitlar ----
log "systemd unitlar..."
SU=$([ "$EUID" -eq 0 ] && echo "" || echo "sudo")
$SU cp deploy/bioscan-fastapi.service /etc/systemd/system/
$SU cp deploy/bioscan-worker.service /etc/systemd/system/ 2>/dev/null || true
$SU cp deploy/bioscan-beat.service /etc/systemd/system/ 2>/dev/null || true
$SU cp deploy/bioscan-bot.service /etc/systemd/system/ 2>/dev/null || true

# WorkingDirectory va User'ni to'g'rilash (default: kayumovvv → DEPLOY_DIR egasi)
SVC_USER=$(stat -c '%U' "$DEPLOY_DIR")
$SU sed -i "s|/home/kayumovvv/loyihalarim/bioscan-fastapi|$DEPLOY_DIR|g" /etc/systemd/system/bioscan-*.service
$SU sed -i "s|User=kayumovvv|User=$SVC_USER|g; s|Group=kayumovvv|Group=$SVC_USER|g" /etc/systemd/system/bioscan-*.service

$SU systemctl daemon-reload
$SU systemctl enable bioscan-fastapi 2>/dev/null
ok "systemd tayyor"

# ---- 7. nginx (avval Django'ni backup, FastAPI primary) ----
log "nginx config..."
if [[ -f /etc/nginx/sites-available/bioscan ]]; then
    $SU cp /etc/nginx/sites-available/bioscan /etc/nginx/sites-available/bioscan.bak.$(date +%s)
    ok "nginx backup olindi"
fi
$SU cp deploy/nginx.conf /etc/nginx/sites-available/bioscan
$SU ln -sf /etc/nginx/sites-available/bioscan /etc/nginx/sites-enabled/bioscan
$SU nginx -t

# ---- 8. Service'larni qayta yoqish ----
log "FastAPI ishga tushirish (port 8001)..."
$SU systemctl restart bioscan-fastapi
sleep 3
if curl -sf http://127.0.0.1:8001/api/health/ >/dev/null; then
    ok "FastAPI 8001'da javob beryapti"
else
    err "FastAPI ishga tushmadi — log: journalctl -u bioscan-fastapi -n 30"
    exit 1
fi

log "nginx reload (Django backup, FastAPI primary)..."
$SU systemctl reload nginx
sleep 2

# Live check
log "Live check..."
HEALTH=$(curl -sk https://bioscan.duckdns.org/api/health/ -m 10)
if echo "$HEALTH" | grep -q "ok"; then
    ok "Live: $HEALTH"
else
    err "Live test fail — $HEALTH"
fi

echo ""
echo -e "\033[1;32m═══════════════════════════════════════════\033[0m"
echo -e "\033[1;32m  ✓ DEPLOY TUGADI\033[0m"
echo -e "\033[1;32m═══════════════════════════════════════════\033[0m"
echo ""
echo "Tekshirish:"
echo "  curl https://bioscan.duckdns.org/api/health/"
echo "  curl https://bioscan.duckdns.org/api/species/?page_size=2"
echo ""
echo "Logs:"
echo "  sudo journalctl -u bioscan-fastapi -f"
echo ""
echo "Rollback (Django'ga qaytish):"
echo "  sudo systemctl stop bioscan-fastapi"
echo "  sudo systemctl start togai-django  # eski"
