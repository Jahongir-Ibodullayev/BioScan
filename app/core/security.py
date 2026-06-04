"""JWT (PyJWT) + parol — Django pbkdf2_sha256 + bcrypt.

passlib va python-jose tushirildi — ikkalasi ham unmaintained.
- PyJWT (Auth0/community) — aktiv maintained
- bcrypt — to'g'ridan-to'g'ri (passlib'siz)
- pbkdf2_sha256 — Django formatini qo'lda parse (foydalanuvchi parollari Django'dan kelganligi sababli)

Django format: pbkdf2_sha256$<iterations>$<salt>$<base64-hash>
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt

from .config import settings


# ----------------------------------------------------------------------
# PAROL — Django pbkdf2_sha256 + bcrypt fallback
# ----------------------------------------------------------------------

# Django default: 1_000_000 iteration (Django 5.1)
PBKDF2_ITERATIONS = 1_000_000
PBKDF2_DIGEST = "sha256"


def _pbkdf2_hash(plain: str, salt: str, iterations: int = PBKDF2_ITERATIONS) -> str:
    """Django formatda hash qaytaradi."""
    raw = hashlib.pbkdf2_hmac(
        PBKDF2_DIGEST, plain.encode("utf-8"), salt.encode("utf-8"), iterations
    )
    b64 = base64.b64encode(raw).decode("ascii")
    return f"pbkdf2_sha256${iterations}${salt}${b64}"


def _pbkdf2_verify(plain: str, hashed: str) -> bool:
    """Django formatda hash'ni tekshirish — pbkdf2_sha256$ITER$SALT$HASH."""
    parts = hashed.split("$")
    if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
        return False
    try:
        iterations = int(parts[1])
    except ValueError:
        return False
    salt = parts[2]
    expected = parts[3]

    actual_raw = hashlib.pbkdf2_hmac(
        PBKDF2_DIGEST, plain.encode("utf-8"), salt.encode("utf-8"), iterations
    )
    actual_b64 = base64.b64encode(actual_raw).decode("ascii")
    # Konstant vaqtli taqqoslash
    return hmac.compare_digest(actual_b64, expected)


def hash_password(plain: str) -> str:
    """Yangi parollar Django formatda saqlanadi (Django foydalanuvchi compat)."""
    salt = secrets.token_urlsafe(12)  # ~16 chars
    return _pbkdf2_hash(plain, salt)


def verify_password(plain: str, hashed: str) -> bool:
    """Django pbkdf2 yoki bcrypt formatlarini tekshiradi."""
    if not hashed:
        return False
    if hashed.startswith("pbkdf2_sha256$"):
        return _pbkdf2_verify(plain, hashed)
    if hashed.startswith("$2"):  # bcrypt
        try:
            return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
        except (ValueError, TypeError):
            return False
    return False


def hash_password_bcrypt(plain: str) -> str:
    """bcrypt — modern alternative (yangi loyihalar uchun)."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


# ----------------------------------------------------------------------
# JWT — PyJWT (Auth0) bilan, SimpleJWT bilan teng struct
# ----------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(user_id: int, extra: Optional[dict] = None) -> str:
    now = _now()
    payload = {
        "token_type": "access",
        "exp": now + timedelta(minutes=settings.JWT_ACCESS_LIFETIME_MIN),
        "iat": now,
        "jti": secrets.token_hex(16),
        "user_id": int(user_id),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    now = _now()
    payload = {
        "token_type": "refresh",
        "exp": now + timedelta(days=settings.JWT_REFRESH_LIFETIME_DAYS),
        "iat": now,
        "jti": secrets.token_hex(16),
        "user_id": int(user_id),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None


def tokens_for(user_id: int) -> dict:
    return {
        "access": create_access_token(user_id),
        "refresh": create_refresh_token(user_id),
    }
