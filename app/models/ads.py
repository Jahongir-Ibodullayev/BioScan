"""Ad — ads_ad (real schema)."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.db.types import BIGINT_PK


class Ad(Base):
    __tablename__ = "ads_ad"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    title: Mapped[str] = mapped_column(String(140))

    image: Mapped[str | None] = mapped_column(String(100), nullable=True)
    image_url: Mapped[str] = mapped_column(String(600), default="")
    headline: Mapped[str] = mapped_column(String(80), default="")
    body: Mapped[str] = mapped_column(String(200), default="")
    cta_text: Mapped[str] = mapped_column(String(40), default="Batafsil")
    target_url: Mapped[str] = mapped_column(String(200), default="")

    slot: Mapped[str] = mapped_column(String(12), default="splash", index=True)
    platform: Mapped[str] = mapped_column(String(8), default="all", index=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)

    duration_seconds: Mapped[int] = mapped_column(Integer, default=4)
    skippable_after: Mapped[int] = mapped_column(Integer, default=2)

    impressions: Mapped[int] = mapped_column(Integer, default=0)
    clicks: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
