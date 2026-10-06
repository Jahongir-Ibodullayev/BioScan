"""Observation + Scan feedback + TFLite — real schema."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.db.types import BIGINT_PK

if TYPE_CHECKING:
    from app.models.species import Species  # noqa: F401  — forward ref uchun


class Observation(Base):
    __tablename__ = "observations_observation"
    # User'ning kuzatuvlarini sort qilingan ko'rinishda olish uchun composite index.
    # Xarita uchun (lat, lon, created_at) ham — bbox query'lar tezroq bo'ladi.
    __table_args__ = (
        Index("ix_obs_user_created", "user_id", "created_at"),
        Index("ix_obs_geo", "latitude", "longitude", "created_at"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("accounts_user.id", ondelete="CASCADE"))
    species_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("catalog_species.id", ondelete="SET NULL"), nullable=True
    )
    photo: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ai_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    note: Mapped[str] = mapped_column(Text, default="")
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    place_name: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Async relationship — N+1 oldini olish uchun har doim selectinload(Observation.species) bilan oling
    species: Mapped[Optional[Species]] = relationship("Species", lazy="raise", foreign_keys=[species_id])  # noqa: F821


class TFLiteModel(Base):
    __tablename__ = "observations_tflitemodel"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    name: Mapped[str] = mapped_column(String(40), unique=True)
    version: Mapped[str] = mapped_column(String(20))
    file: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    sha256: Mapped[str] = mapped_column(String(64), default="")
    classes_url: Mapped[str] = mapped_column(String(600), default="")
    accuracy: Mapped[float] = mapped_column(Float, default=0.85)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ScanFeedback(Base):
    __tablename__ = "observations_scanfeedback"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("accounts_user.id", ondelete="SET NULL"), nullable=True)
    observation_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("observations_observation.id", ondelete="CASCADE"), nullable=True)
    predicted_slug: Mapped[str] = mapped_column(String(140), default="")
    correct_slug: Mapped[str] = mapped_column(String(140), default="")
    is_correct: Mapped[bool] = mapped_column(Boolean, default=True)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
