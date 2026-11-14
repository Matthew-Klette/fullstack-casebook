from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import UTC, datetime, timedelta

import jwt

from app.config import Settings


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, salt_hex, digest_hex = stored.split("$")
    except ValueError:
        return False
    if scheme != "scrypt":
        return False
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1)
    return hmac.compare_digest(digest.hex(), digest_hex)


def make_access_token(user_id: int, settings: Settings, now: datetime | None = None) -> str:
    now = now or datetime.now(UTC)
    claims = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(seconds=settings.access_ttl_seconds),
    }
    return jwt.encode(claims, settings.secret_key, algorithm="HS256")


def decode_access_token(token: str, settings: Settings) -> int | None:
    try:
        claims = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        return int(claims["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None


def new_refresh_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(32)
    return raw, hash_refresh_token(raw)


def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()
