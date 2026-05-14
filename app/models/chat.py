"""Chat: Conversation + Message."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.db.types import BIGINT_PK


class Conversation(Base):
    __tablename__ = "chat_conversation"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("accounts_user.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(120), default="Yangi suhbat")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Message(Base):
    __tablename__ = "chat_message"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("chat_conversation.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(4))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
