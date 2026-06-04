"""User schemas — Django UserSerializer bilan teng struktura."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class UserOut(BaseModel):
    id: int
    phone: str
    full_name: str = ""
    role: str = "Turist"
    avatar: Optional[str] = None
    locale: str = "uz"
    verified_member: bool = False
    date_joined: datetime

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    # Django'ning SimpleAuthView bilan teng: validatsiya endpoint ichida — 400 qaytaradi
    phone: str = ""
    password: str = ""
    full_name: Optional[str] = None


class TokenPair(BaseModel):
    access: str
    refresh: str


class AuthResponse(BaseModel):
    user: UserOut
    access: str
    refresh: str
    new: bool = False


class RefreshRequest(BaseModel):
    refresh: str


class UpdateMeRequest(BaseModel):
    """PATCH /api/auth/me/ — faqat ruxsat etilgan maydonlar."""
    full_name: Optional[str] = None
    role: Optional[str] = None
    locale: Optional[str] = None
    fcm_token: Optional[str] = None
    fcm_platform: Optional[str] = None

    model_config = {"extra": "forbid"}  # noma'lum maydon → 422
