"""Chat router — /api/chat/*.

Webapp + Flutter formatlari bilan moslashuvchan:
  - /chat/send/, /chat/ai/, /chat/conversations/ask/ — barchasi teng
  - Response: {conversation_id, messages: [user_msg, ai_msg], reply: ai_msg}
  - /chat/conversations/{id}/ — detail (messages bilan)
  - POST /chat/conversations/ — yaratish
  - DELETE /chat/conversations/{id}/
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import delete, func, select

from app.api.deps import CurrentUser, DB
from app.models.chat import Conversation, Message
from app.schemas.common import paginated
from app.services.ai import openrouter_chat

router = APIRouter(prefix="/chat", tags=["chat"])

SYSTEM_PROMPT = (
    "Sen BioScan AI yordamchisisan — Markaziy Osiyo tabiati va biologiyasi bo'yicha mutaxassis. "
    "Foydalanuvchiga aniq, qisqa, o'zbekcha javob ber. Yo'q narsani uydirma."
)


class ChatMessage(BaseModel):
    text: str
    conversation_id: int | None = None
    species_slug: str | None = None  # Flutter ba'zan yuboradi


def _msg_dict(m: Message) -> dict:
    return {
        "id": m.id, "role": m.role, "text": m.text,
        "created_at": m.created_at.isoformat(),
    }


# ----------------------------------------------------------------------
# Conversations CRUD
# ----------------------------------------------------------------------
@router.get("/conversations/")
async def list_conversations(
    user: CurrentUser, db: DB,
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
) -> dict:
    base = select(Conversation).where(Conversation.user_id == user.id)
    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0
    stmt = base.order_by(Conversation.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.scalars(stmt)).all()
    items = [{"id": c.id, "title": c.title, "created_at": c.created_at.isoformat()} for c in rows]
    return paginated(items, total=total, page=page, page_size=page_size)


class ConversationIn(BaseModel):
    title: str | None = None


@router.post("/conversations/", status_code=status.HTTP_201_CREATED)
async def create_conversation(payload: ConversationIn, user: CurrentUser, db: DB) -> dict:
    conv = Conversation(user_id=user.id, title=(payload.title or "Yangi suhbat")[:120])
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return {"id": conv.id, "title": conv.title, "created_at": conv.created_at.isoformat()}


@router.get("/conversations/{conv_id}/")
async def conversation_detail(conv_id: int, user: CurrentUser, db: DB) -> dict:
    conv = await db.scalar(
        select(Conversation).where(Conversation.id == conv_id, Conversation.user_id == user.id)
    )
    if not conv:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Suhbat topilmadi")
    rows = (await db.scalars(
        select(Message).where(Message.conversation_id == conv_id).order_by(Message.created_at)
    )).all()
    return {
        "id": conv.id,
        "title": conv.title,
        "created_at": conv.created_at.isoformat(),
        "messages": [_msg_dict(m) for m in rows],
    }


@router.delete("/conversations/{conv_id}/")
async def delete_conversation(conv_id: int, user: CurrentUser, db: DB) -> dict:
    conv = await db.scalar(
        select(Conversation).where(Conversation.id == conv_id, Conversation.user_id == user.id)
    )
    if not conv:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Suhbat topilmadi")
    await db.delete(conv)
    await db.commit()
    return {"ok": True}


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
    items = [_msg_dict(m) for m in rows]
    return paginated(items, total=len(items))


# ----------------------------------------------------------------------
# Ask / Send (3 ta alias — webapp, Flutter, eski)
# ----------------------------------------------------------------------
async def _send_impl(payload: ChatMessage, user, db) -> dict:
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
        conv = Conversation(user_id=user.id, title=text[:60])
        db.add(conv)
        await db.commit()
        await db.refresh(conv)

    user_msg = Message(conversation_id=conv.id, role="user", text=text)
    db.add(user_msg)
    await db.commit()
    await db.refresh(user_msg)

    # AI prompt — species slug ham hisobga olinadi
    prompt = text
    if payload.species_slug:
        prompt = f"[Tur: {payload.species_slug}] {text}"

    ai_text = await openrouter_chat(prompt, system=SYSTEM_PROMPT, max_tokens=600)
    ai_msg = Message(conversation_id=conv.id, role="ai", text=ai_text)
    db.add(ai_msg)
    await db.commit()
    await db.refresh(ai_msg)

    return {
        "conversation_id": conv.id,
        # Webapp uchun — messages array
        "messages": [_msg_dict(user_msg), _msg_dict(ai_msg)],
        # Flutter uchun — reply (ai_text string)
        "reply": ai_text,
        # Eski format (orqaga moslik) — reply object
        "reply_message": _msg_dict(ai_msg),
    }


@router.post("/send/")
async def send_message(payload: ChatMessage, user: CurrentUser, db: DB) -> dict:
    return await _send_impl(payload, user, db)


@router.post("/conversations/ask/")
async def ask_conversation(payload: ChatMessage, user: CurrentUser, db: DB) -> dict:
    """Webapp foydalanadi — /chat/send/ bilan teng."""
    return await _send_impl(payload, user, db)


@router.post("/ai/")
async def chat_ai(payload: ChatMessage, user: CurrentUser, db: DB) -> dict:
    """Flutter foydalanadi — /chat/send/ bilan teng."""
    return await _send_impl(payload, user, db)
