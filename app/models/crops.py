"""Crops: Region, Crop, CropPlan — real Django schema.

IrrigationLog va ScoutingNote modellar Django'da yo'q — bu yerda ham qo'shmaymiz.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.session import Base
from app.db.types import BIGINT_PK


class Region(Base):
    __tablename__ = "crops_region"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    slug: Mapped[str] = mapped_column(String(40), unique=True)
    name_uz: Mapped[str] = mapped_column(String(40))
    name_ru: Mapped[str] = mapped_column(String(40), default="")
    lat_min: Mapped[Decimal] = mapped_column(Numeric(8, 4))
    lat_max: Mapped[Decimal] = mapped_column(Numeric(8, 4))
    lon_min: Mapped[Decimal] = mapped_column(Numeric(8, 4))
    lon_max: Mapped[Decimal] = mapped_column(Numeric(8, 4))
    avg_last_frost_doy: Mapped[int] = mapped_column(Integer, default=80)
    avg_first_frost_doy: Mapped[int] = mapped_column(Integer, default=290)
    annual_rainfall_mm: Mapped[int] = mapped_column(Integer, default=300)

    def contains(self, lat: float, lon: float) -> bool:
        return (
            float(self.lat_min) <= lat <= float(self.lat_max)
            and float(self.lon_min) <= lon <= float(self.lon_max)
        )


class Crop(Base):
    __tablename__ = "crops_crop"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    name_uz: Mapped[str] = mapped_column(String(80))
    name_ru: Mapped[str] = mapped_column(String(80), default="")
    name_lat: Mapped[str] = mapped_column(String(120), default="")
    category: Mapped[str] = mapped_column(String(20), default="sabzavot")
    icon_name: Mapped[str] = mapped_column(String(40), default="leaf")

    min_soil_temp_c: Mapped[int] = mapped_column(Integer, default=0)
    optimal_soil_temp_c: Mapped[int] = mapped_column(Integer, default=0)
    frost_sensitive: Mapped[bool] = mapped_column(Boolean, default=False)
    plant_window_start_month: Mapped[int] = mapped_column(Integer, default=3)
    plant_window_end_month: Mapped[int] = mapped_column(Integer, default=5)
    days_to_harvest_min: Mapped[int] = mapped_column(Integer, default=80)
    days_to_harvest_max: Mapped[int] = mapped_column(Integer, default=120)

    water_freq_days: Mapped[int] = mapped_column(Integer, default=5)
    drought_tolerant: Mapped[bool] = mapped_column(Boolean, default=False)
    flood_tolerant: Mapped[bool] = mapped_column(Boolean, default=False)

    soil_type: Mapped[str] = mapped_column(String(80), default="qum-tuproq")
    ph_min: Mapped[Decimal] = mapped_column(Numeric(3, 1), default=Decimal("6.0"))
    ph_max: Mapped[Decimal] = mapped_column(Numeric(3, 1), default=Decimal("7.0"))
    sun_hours_min: Mapped[int] = mapped_column(Integer, default=6)

    soil_prep_uz: Mapped[str] = mapped_column(Text, default="")
    planting_method_uz: Mapped[str] = mapped_column(Text, default="")
    care_tips_uz: Mapped[str] = mapped_column(Text, default="")
    common_pests: Mapped[str] = mapped_column(Text, default="")

    # Django'da JSONField — Postgres'da jsonb, SQLite'da JSON (test paytida)
    common_varieties: Mapped[list] = mapped_column(JSON().with_variant(JSONB, "postgresql"), default=list)
    image_url: Mapped[str] = mapped_column(String(600), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class CropPlan(Base):
    __tablename__ = "crops_cropplan"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("accounts_user.id", ondelete="CASCADE"))
    crop_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("crops_crop.id", ondelete="CASCADE"))
    lat: Mapped[Decimal] = mapped_column(Numeric(8, 4))
    lon: Mapped[Decimal] = mapped_column(Numeric(8, 4))
    irrigation: Mapped[str] = mapped_column(String(20), default="manual")
    plot_size_m2: Mapped[int | None] = mapped_column(Integer, nullable=True)
    planned_plant_date: Mapped[date] = mapped_column(Date)
    expected_harvest_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    notify: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
