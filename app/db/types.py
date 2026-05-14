"""Maxsus tiplar — SQLite vs Postgres farqlarini yashiradi."""
from __future__ import annotations

from sqlalchemy import BigInteger, Integer

# SQLite'da BIGINT PRIMARY KEY autoincrement bo'lmaydi — INTEGER kerak.
# Postgres'da Django BigAutoField bilan teng — BIGINT identity.
BIGINT_PK = BigInteger().with_variant(Integer, "sqlite")
