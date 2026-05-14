"""Auth router — /api/auth/*.

Django'ning SimpleAuthView, MeView, TokenRefreshView, OTP teng. APK/webapp
bilan fully compatible — bir xil JSON payload va token format.
"""
from __future__ import annotations

import secrets

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, update

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
from app.models.user import OTPCode, User
from app.schemas.user import AuthResponse, LoginRequest, RefreshRequest, UpdateMeRequest, UserOut
from app.services.sms import send_sms
from app.services.telegram import send_otp_via_telegram

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login/", response_model=AuthResponse)
async def simple_auth(req: LoginRequest, db: DB) -> AuthResponse:
    """Telefon + parol. Mavjud bo'lmasa yangi hisob yaratiladi."""
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


@router.get("/me/", response_model=UserOut)
async def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


@router.patch("/me/", response_model=UserOut)
async def update_me(updates: UpdateMeRequest, user: CurrentUser, db: DB) -> UserOut:
    """Foydalanuvchi profilini yangilash. Pydantic strict — noma'lum maydon 422."""
    payload = updates.model_dump(exclude_unset=True)
    for k, v in payload.items():
        if v is not None:
            setattr(user, k, v)
    await db.commit()
    await db.refresh(user)
    return UserOut.model_validate(user)


@router.post("/token/refresh/")
async def refresh_token(req: RefreshRequest, db: DB) -> dict:
    """SimpleJWT bilan teng — refresh tokenni access tokenga aylantirish."""
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
# OTP — APK (SMS) va Webapp (Telegram bot)
# ----------------------------------------------------------------------
class OTPRequest(BaseModel):
    phone: str


class OTPVerify(BaseModel):
    phone: str
    code: str
    full_name: str | None = None


async def _issue_otp(db: DB, phone: str) -> OTPCode:
    code = f"{secrets.randbelow(1_000_000):06d}"
    # Eski faolsizlarni invalidate qil
    await db.execute(
        update(OTPCode).where(OTPCode.phone == phone, OTPCode.used == False)  # noqa: E712
        .values(used=True)
    )
    otp = OTPCode(phone=phone, code=code)
    db.add(otp)
    await db.commit()
    await db.refresh(otp)
    return otp


@router.post("/otp/request/", status_code=status.HTTP_201_CREATED)
async def otp_request_sms(req: OTPRequest, db: DB) -> dict:
    """APK uchun — SMS gateway. DON'T BREAK APK OTP!"""
    phone = req.phone.strip()
    if not phone:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "phone majburiy")
    otp = await _issue_otp(db, phone)
    ok = await send_sms(phone, f"BioScan tasdiqlash kodi: {otp.code}. Kod 2 daqiqa amal qiladi.")
    if not ok:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "SMS yuborilmadi. Keyinroq qayta urinib ko'ring.",
        )
    data: dict = {"ok": True, "phone": phone}
    if settings.DEBUG:
        data["dev_code"] = otp.code
    return data


@router.post("/tg-otp/request/", status_code=status.HTTP_201_CREATED)
async def otp_request_telegram(req: OTPRequest, db: DB) -> dict:
    """Webapp uchun — Telegram bot. APK SMS'iga tegmaydi."""
    phone = req.phone.strip()
    if not phone:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "phone majburiy")

    user = await db.scalar(select(User).where(User.phone == phone))
    bot_username = (settings.TELEGRAM_OTP_BOT_USERNAME or settings.TELEGRAM_BOT_USERNAME).lstrip("@")

    if not user or not user.telegram_id:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            {
                "detail": (
                    "Telegram orqali kirish uchun avval botga ulaning. "
                    "Botni oching va /login bosib telefon raqamingizni ulashing."
                ),
                "telegram_not_linked": True,
                "bot_username": bot_username or None,
                "bot_url": f"https://t.me/{bot_username}" if bot_username else None,
            },
        )

    otp = await _issue_otp(db, phone)
    ok = await send_otp_via_telegram(user.telegram_id, otp.code)
    if not ok:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Kod yuborilmadi. Botni qayta oching va /login bosing.",
        )
    data: dict = {"ok": True, "phone": phone, "channel": "telegram", "bot_username": bot_username or None}
    if settings.DEBUG:
        data["dev_code"] = otp.code
    return data


@router.post("/otp/verify/", response_model=AuthResponse)
async def otp_verify(req: OTPVerify, db: DB) -> AuthResponse:
    """Kod tasdiqlash + auto-register. APK va webapp ikkalasi uchun."""
    phone = req.phone.strip()
    code = req.code.strip()
    if not phone or not code:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "phone va code majburiy")

    otp = await db.scalar(
        select(OTPCode).where(OTPCode.phone == phone, OTPCode.code == code, OTPCode.used == False)  # noqa: E712
        .order_by(OTPCode.created_at.desc())
    )
    if not otp or not otp.is_valid():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Kod noto'g'ri yoki eskirgan")

    otp.used = True

    user = await db.scalar(select(User).where(User.phone == phone))
    created = False
    if not user:
        user = User(phone=phone, password="", full_name=(req.full_name or "").strip(), is_active=True)
        db.add(user)
        created = True
    elif req.full_name and not user.full_name:
        user.full_name = req.full_name.strip()

    await db.commit()
    await db.refresh(user)

    return AuthResponse(
        user=UserOut.model_validate(user),
        **tokens_for(user.id),
        new=created,
    )


# Webapp uchun teng URL — Django'da `tg-otp/verify/` ham bor edi
@router.post("/tg-otp/verify/", response_model=AuthResponse)
async def tg_otp_verify(req: OTPVerify, db: DB) -> AuthResponse:
    return await otp_verify(req, db)


# ----------------------------------------------------------------------
# FCM token register/unregister
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
