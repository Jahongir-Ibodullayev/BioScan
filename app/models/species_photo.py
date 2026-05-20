"""SpeciesPhoto — iNat'dan boyitilgan rasm galeriyasi.

Har bir species'ga bir nechta rasm: iNat taxon_photos array'idan kelgan.
Default rasmni `is_default=True` belgilab qo'yiladi (Species.image_url'ga ham
yoziladi — backward compat uchun).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.db.types import BIGINT_PK


class SpeciesPhoto(Base):
    __tablename__ = "catalog_species_photo"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    species_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("catalog_species.id", ondelete="CASCADE"),
        index=True,
    )

    url: Mapped[str] = mapped_column(String(800))
    attribution: Mapped[str] = mapped_column(String(300), default="")
    license_code: Mapped[str] = mapped_column(String(20), default="")  # CC-BY-NC, CC0, ...
    source: Mapped[str] = mapped_column(String(20), default="inat")  # inat | manual | crowd
    external_id: Mapped[str] = mapped_column(String(40), default="", index=True)

    is_default: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    ordering: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<SpeciesPhoto species={self.species_id} url={self.url[:40]}…>"
