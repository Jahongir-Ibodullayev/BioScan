"""Auth router — /api/auth/*.

OTP TO'LIQ OLIB TASHLANGAN — faqat telefon + parol login.
  - /auth/login/          → telefon + parol (auto-register agar yangi)
  - /auth/quick/          → faqat telefon + ism (parolsiz) — eski webapp uchun
  - /auth/me/             → joriy user
  - /auth/token/refresh/  → JWT refresh
  - /auth/fcm/*           → push notification token
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import CurrentUser, DB
from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    tokens_for,
    verify_password,
)
from app.models.user import User
from app.schemas.user import AuthResponse, LoginRequest, RefreshRequest, UpdateMeRequest, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


# ----------------------------------------------------------------------
# Login + Quick Auth
# ----------------------------------------------------------------------
@router.post("/login/", response_model=AuthResponse)
async def simple_auth(req: LoginRequest, db: DB) -> AuthResponse:
    """Telefon + parol. Foydalanuvchi mavjud bo'lmasa yangi hisob yaratiladi."""
    phone = req.phone.strip()
    password = req.password.strip()
    full_name = (req.full_name or "").strip()

    if not phone or not password:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "phone va password majburiy")
    if len(password) < 4:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Parol kamida 4 belgili bo'lsin")

    user = await db.scalar(select(User).where(User.phone == phone))
    created = False

    if user is None:
        user = User(
            phone=phone,
            password=hash_password(password),
            full_name=full_name,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        created = True
    else:
        if not verify_password(password, user.password):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Parol noto'g'ri")
        if full_name and not user.full_name:
            user.full_name = full_name
            await db.commit()
            await db.refresh(user)

    return AuthResponse(
        user=UserOut.model_validate(user),
        **tokens_for(user.id),
        new=created,
    )


class QuickAuthRequest(BaseModel):
    phone: str
    full_name: str | None = None


@router.post("/quick/", response_model=AuthResponse)
async def quick_auth(req: QuickAuthRequest, db: DB) -> AuthResponse:
    """Faqat telefon raqami bilan kirish — parolsiz (eski webapp uchun).

    QUICK_AUTH_ENABLED=false bo'lsa 403.
    """
    if not settings.QUICK_AUTH_ENABLED:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Quick auth o'chirilgan")

    phone = req.phone.strip()
    full_name = (req.full_name or "").strip()
    if not phone:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "phone majburiy")

    user = await db.scalar(select(User).where(User.phone == phone))
    created = False
    if user is None:
        user = User(phone=phone, password="", full_name=full_name, is_active=True)
        db.add(user)
        created = True
    elif full_name and not user.full_name:
        user.full_name = full_name
    await db.commit()
    await db.refresh(user)

    return AuthResponse(
        user=UserOut.model_validate(user),
        **tokens_for(user.id),
        new=created,
    )


# ----------------------------------------------------------------------
# Profile
# ----------------------------------------------------------------------
@router.get("/me/", response_model=UserOut)
async def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


@router.patch("/me/", response_model=UserOut)
async def update_me(updates: UpdateMeRequest, user: CurrentUser, db: DB) -> UserOut:
    """Profil yangilash. Pydantic strict — noma'lum maydon 422."""
    payload = updates.model_dump(exclude_unset=True)
    for k, v in payload.items():
        if v is not None:
            setattr(user, k, v)
    await db.commit()
    await db.refresh(user)
    return UserOut.model_validate(user)


# ----------------------------------------------------------------------
# Token refresh
# ----------------------------------------------------------------------
@router.post("/token/refresh/")
async def refresh_token(req: RefreshRequest, db: DB) -> dict:
    """Refresh tokenni yangi access tokenga aylantirish."""
    payload = decode_token(req.refresh)
    if not payload or payload.get("token_type") != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token noto'g'ri")
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token payload noto'g'ri")
    user = await db.scalar(select(User).where(User.id == int(user_id), User.is_active == True))  # noqa: E712
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Foydalanuvchi topilmadi")
    return {
        "access": create_access_token(user.id),
        "refresh": create_refresh_token(user.id),
    }


# ----------------------------------------------------------------------
# FCM (push notification)
# ----------------------------------------------------------------------
class FCMRegister(BaseModel):
    token: str
    platform: str = "android"


@router.post("/fcm/register/")
async def fcm_register(req: FCMRegister, user: CurrentUser, db: DB) -> dict:
    if not req.token.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "token majburiy")
    platform = req.platform.strip().lower()
    if platform not in ("android", "ios", "web"):
        platform = "android"
    user.fcm_token = req.token.strip()
    user.fcm_platform = platform
    await db.commit()
    return {"ok": True, "platform": platform}


@router.post("/fcm/unregister/")
async def fcm_unregister(user: CurrentUser, db: DB) -> dict:
    user.fcm_token = ""
    user.fcm_platform = ""
    await db.commit()
    return {"ok": True}
