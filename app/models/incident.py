"""Incident — incidents_incident jadvali (community xavf hisobotlari)."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.db.types import BIGINT_PK


class Incident(Base):
    __tablename__ = "incidents_incident"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    reporter_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("accounts_user.id", ondelete="SET NULL"), nullable=True
    )
    code: Mapped[str] = mapped_column(String(12), unique=True, default="")
    category: Mapped[str] = mapped_column(String(20))  # ilon, yirtqich, ...
    severity: Mapped[str] = mapped_column(String(8), default="orta")
    status: Mapped[str] = mapped_column(String(20), default="yangi")
    note: Mapped[str] = mapped_column(Text, default="")
    photo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    place_name: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
