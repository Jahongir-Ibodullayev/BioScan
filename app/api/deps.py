"""FastAPI dependency'lar — current_user, optional_user."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User

bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Authorization: Bearer <jwt> — yo'q yoki noto'g'ri bo'lsa 401."""
    if not creds or not creds.credentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Autentifikatsiya kerak")
    payload = decode_token(creds.credentials)
    if not payload or payload.get("token_type") != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token noto'g'ri")
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token payload noto'g'ri")
    user = await db.scalar(select(User).where(User.id == int(user_id), User.is_active == True))  # noqa: E712
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Foydalanuvchi topilmadi")
    return user


async def get_optional_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User | None:
    """Authorization bor bo'lsa user, yo'q bo'lsa None."""
    if not creds or not creds.credentials:
        return None
    payload = decode_token(creds.credentials)
    if not payload:
        return None
    user_id = payload.get("user_id")
    if not user_id:
        return None
    return await db.scalar(select(User).where(User.id == int(user_id), User.is_active == True))  # noqa: E712


CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]
DB = Annotated[AsyncSession, Depends(get_db)]
