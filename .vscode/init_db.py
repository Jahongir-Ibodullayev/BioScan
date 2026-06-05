"""Lokal SQLite jadvallarini yaratish (.env'dagi DATABASE_URL bo'yicha).

VS Code: Terminal > Run Task > "BioScan: Init SQLite tables"
Yoki:    .venv/bin/python .vscode/init_db.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Skript .vscode/ ichida — workspace root'ni import yo'liga qo'shamiz
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app.models  # barcha modellarni Base.metadata'ga ro'yxatdan o'tkazadi  # noqa: E402,F401
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.db.session import Base


async def main() -> None:
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print(f"{len(Base.metadata.tables)} ta jadval tayyor → {settings.DATABASE_URL}")


if __name__ == "__main__":
    asyncio.run(main())
