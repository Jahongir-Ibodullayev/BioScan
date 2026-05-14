"""Saved species — saved_items_savedspecies."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.db.types import BIGINT_PK


class SavedSpecies(Base):
    __tablename__ = "saved_items_savedspecies"
    __table_args__ = (
        UniqueConstraint("user_id", "species_id", name="saved_items_savedspecies_user_species_uniq"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("accounts_user.id", ondelete="CASCADE"))
    species_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("catalog_species.id", ondelete="CASCADE"))
    note: Mapped[str] = mapped_column(String(240), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
