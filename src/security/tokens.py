from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt

from src.infrastructure.config import settings


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenError(Exception):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _encode(payload: dict) -> str:
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(*, subject: str, role: str) -> str:
    now = _utcnow()
    payload = {
        "sub": subject,
        "role": role,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp()),
    }
    return _encode(payload)


def create_token_pair(*, subject: str, role: str) -> TokenPair:
    now = _utcnow()

    access_payload = {
        "sub": subject,
        "role": role,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp()),
    }
    refresh_payload = {
        "sub": subject,
        "role": role,
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)).timestamp()),
    }

    return TokenPair(access_token=_encode(access_payload), refresh_token=_encode(refresh_payload))


@dataclass(frozen=True)
class AccessTokenClaims:
    sub: str
    role: str


def _verify_token(token: str, expected_type: str) -> AccessTokenClaims:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.PyJWTError as e:
        raise TokenError("Invalid token") from e

    if payload.get("type") != expected_type:
        article = "an" if expected_type.startswith(("a", "e", "i", "o", "u")) else "a"
        raise TokenError(f"Not {article} {expected_type} token")

    sub = payload.get("sub")
    role = payload.get("role")
    if not isinstance(sub, str) or not sub:
        raise TokenError("Invalid token subject")
    if not isinstance(role, str) or not role:
        raise TokenError("Invalid token role")

    return AccessTokenClaims(sub=sub, role=role)


def verify_access_token(token: str) -> AccessTokenClaims:
    return _verify_token(token, "access")


def verify_refresh_token(token: str) -> AccessTokenClaims:
    return _verify_token(token, "refresh")
