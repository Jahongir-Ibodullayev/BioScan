"""Chat router — /api/chat/*."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import CurrentUser, DB
from app.models.chat import Conversation, Message
from app.services.ai import openrouter_chat

router = APIRouter(prefix="/chat", tags=["chat"])

SYSTEM_PROMPT = (
    "Sen BioScan AI yordamchisisan — Markaziy Osiyo tabiati va biologiyasi bo'yicha mutaxassis. "
    "Foydalanuvchiga aniq, qisqa, o'zbekcha javob ber. Yo'q narsani uydirma."
)


class ChatMessage(BaseModel):
    text: str
    conversation_id: int | None = None


@router.get("/conversations/")
async def list_conversations(user: CurrentUser, db: DB) -> dict:
    rows = (await db.scalars(
        select(Conversation).where(Conversation.user_id == user.id).order_by(Conversation.created_at.desc())
    )).all()
    return {"results": [
        {"id": c.id, "title": c.title, "created_at": c.created_at.isoformat()} for c in rows
    ]}


@router.get("/conversations/{conv_id}/messages/")
async def list_messages(conv_id: int, user: CurrentUser, db: DB) -> dict:
    conv = await db.scalar(
        select(Conversation).where(Conversation.id == conv_id, Conversation.user_id == user.id)
    )
    if not conv:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Suhbat topilmadi")
    rows = (await db.scalars(
        select(Message).where(Message.conversation_id == conv_id).order_by(Message.created_at)
    )).all()
    return {"results": [
        {"id": m.id, "role": m.role, "text": m.text, "created_at": m.created_at.isoformat()}
        for m in rows
    ]}


@router.post("/send/")
async def send_message(payload: ChatMessage, user: CurrentUser, db: DB) -> dict:
    return await _send_impl(payload, user, db)


@router.post("/conversations/ask/")
async def ask_conversation(payload: ChatMessage, user: CurrentUser, db: DB) -> dict:
    """Webapp eski URL — /chat/send/ bilan teng."""
    return await _send_impl(payload, user, db)


@router.post("/ai/")
async def chat_ai(payload: ChatMessage, user: CurrentUser, db: DB) -> dict:
    """Flutter foydalanadi — /chat/send/ bilan teng."""
    return await _send_impl(payload, user, db)


async def _send_impl(payload: ChatMessage, user: CurrentUser, db: DB) -> dict:
    text = payload.text.strip()
    if not text:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Xabar bo'sh bo'lmaslik kerak")

    # Conversation tanlash yoki yaratish
    if payload.conversation_id:
        conv = await db.scalar(
            select(Conversation).where(
                Conversation.id == payload.conversation_id,
                Conversation.user_id == user.id,
            )
        )
        if not conv:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Suhbat topilmadi")
    else:
        title = text[:60]
        conv = Conversation(user_id=user.id, title=title)
        db.add(conv)
        await db.commit()
        await db.refresh(conv)

    # User xabari
    db.add(Message(conversation_id=conv.id, role="user", text=text))
    await db.commit()

    # AI javob
    ai_text = await openrouter_chat(text, system=SYSTEM_PROMPT, max_tokens=600)
    ai_msg = Message(conversation_id=conv.id, role="ai", text=ai_text)
    db.add(ai_msg)
    await db.commit()
    await db.refresh(ai_msg)

    return {
        "conversation_id": conv.id,
        "reply": {
            "id": ai_msg.id,
            "role": "ai",
            "text": ai_text,
            "created_at": ai_msg.created_at.isoformat(),
        },
    }
