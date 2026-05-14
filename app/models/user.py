"""User + OTPCode — Django accounts_user / accounts_otpcode jadvallari (real schema)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import BigInteger, Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.db.types import BIGINT_PK


class User(Base):
    __tablename__ = "accounts_user"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)

    # Django AbstractUser
    password: Mapped[str] = mapped_column(String(128))
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    first_name: Mapped[str] = mapped_column(String(150), default="")
    last_name: Mapped[str] = mapped_column(String(150), default="")
    email: Mapped[str] = mapped_column(String(254), default="")
    is_staff: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    date_joined: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Custom
    phone: Mapped[str] = mapped_column(String(20), unique=True)
    full_name: Mapped[str] = mapped_column(String(120), default="")
    role: Mapped[str] = mapped_column(String(40), default="Turist")
    avatar: Mapped[str | None] = mapped_column(String(100), nullable=True)
    locale: Mapped[str] = mapped_column(String(5), default="uz")
    verified_member: Mapped[bool] = mapped_column(Boolean, default=False)

    # E-commerce role (Django migration 0002 qo'shgan)
    account_type: Mapped[str] = mapped_column(String(20), default="customer")
    seller_name: Mapped[str] = mapped_column(String(120), default="")
    seller_bio: Mapped[str] = mapped_column(Text, default="")
    seller_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Telegram link (0003)
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, unique=True, index=True)
    telegram_username: Mapped[str] = mapped_column(String(64), default="")

    # FCM (0004)
    fcm_token: Mapped[str] = mapped_column(String(255), default="", index=True)
    fcm_platform: Mapped[str] = mapped_column(String(20), default="")

    def __repr__(self) -> str:
        return f"<User {self.phone}>"


class OTPCode(Base):
    __tablename__ = "accounts_otpcode"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    phone: Mapped[str] = mapped_column(String(20), index=True)
    code: Mapped[str] = mapped_column(String(6))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    used: Mapped[bool] = mapped_column(Boolean, default=False)

    def is_valid(self) -> bool:
        if self.used:
            return False
        now = datetime.now(timezone.utc)
        created = self.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        return (now - created) < timedelta(minutes=2)
