"""Species — catalog_species (real schema)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.db.types import BIGINT_PK


class Species(Base):
    __tablename__ = "catalog_species"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    slug: Mapped[str] = mapped_column(String(140), unique=True)
    name: Mapped[str] = mapped_column(String(140), index=True)
    latin: Mapped[str] = mapped_column(String(160), default="")
    category: Mapped[str] = mapped_column(String(16), index=True)
    icon_name: Mapped[str] = mapped_column(String(40), default="leaf")
    color_class: Mapped[str] = mapped_column(String(80), default="bg-primary-100 text-primary-700")

    summary: Mapped[str] = mapped_column(String(280), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    habitat: Mapped[str] = mapped_column(Text, default="")
    uses: Mapped[str] = mapped_column(Text, default="")
    warnings: Mapped[str] = mapped_column(Text, default="")
    first_aid: Mapped[str] = mapped_column(Text, default="")

    image: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    image_url: Mapped[str] = mapped_column(String(600), default="")

    red_book: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    iucn_status: Mapped[str] = mapped_column(String(4), default="NE", index=True)
    regions: Mapped[str] = mapped_column(String(240), default="")
    external_ref: Mapped[str] = mapped_column(String(200), default="")

    halal_status: Mapped[str] = mapped_column(String(10), default="unknown", index=True)
    is_medicinal: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_honey_plant: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    livestock_danger: Mapped[str] = mapped_column(String(10), default="safe", index=True)
    is_edible: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    bloom_months: Mapped[str] = mapped_column(String(50), default="")
    harvest_months: Mapped[str] = mapped_column(String(50), default="")

    fine_bhm_min: Mapped[int] = mapped_column(Integer, default=0)
    fine_bhm_max: Mapped[int] = mapped_column(Integer, default=0)
    law_article: Mapped[str] = mapped_column(String(120), default="")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    @property
    def picture(self) -> str:
        if self.image:
            return f"/media/{self.image}"
        return self.image_url or ""
