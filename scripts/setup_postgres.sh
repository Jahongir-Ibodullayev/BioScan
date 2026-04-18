#!/usr/bin/env bash
# Tog'AI — PostgreSQL DB va user yaratish
# Ishlatish: bash scripts/setup_postgres.sh
set -e

DB=togai
USER=togai
PASS=togai_pass_$(date +%s | shasum | head -c 16)

echo "→ Yaratilyapti: $DB / $USER"
sudo -u postgres psql <<EOF
CREATE DATABASE $DB;
CREATE USER $USER WITH PASSWORD '$PASS';
GRANT ALL PRIVILEGES ON DATABASE $DB TO $USER;
ALTER DATABASE $DB OWNER TO $USER;
\\c $DB
GRANT ALL ON SCHEMA public TO $USER;
EOF

# Write creds back to .env
ENV_FILE="$(cd "$(dirname "$0")/.." && pwd)/.env"
sed -i '/^DB_NAME=/d;/^DB_USER=/d;/^DB_PASSWORD=/d;/^USE_SQLITE=/d;/^# USE_SQLITE=/d' "$ENV_FILE"
{
  echo "DB_NAME=$DB"
  echo "DB_USER=$USER"
  echo "DB_PASSWORD=$PASS"
} >> "$ENV_FILE"

echo "✓ PostgreSQL tayyor. .env yangilandi."
echo "  Endi: ./venv/bin/python manage.py makemigrations && ./venv/bin/python manage.py migrate && ./venv/bin/python manage.py seed"
