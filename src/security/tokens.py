import secrets
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


def _encode(payload: dict) -> str:
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_token_pair(
    *, subject: str, role: str, version: int = 0, session_id: str | None = None
) -> TokenPair:
    now = datetime.now(timezone.utc)
    common = {
        "sub": subject,
        "role": role,
        "ver": version,
        "sid": session_id or secrets.token_hex(16),
        "iat": int(now.timestamp()),
    }
    access = {
        **common,
        "type": "access",
        "jti": secrets.token_hex(16),
        "exp": int((now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp()),
    }
    refresh = {
        **common,
        "type": "refresh",
        "jti": secrets.token_hex(16),
        "exp": int((now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)).timestamp()),
    }
    return TokenPair(_encode(access), _encode(refresh))


@dataclass(frozen=True)
class AccessTokenClaims:
    sub: str
    role: str
    version: int
    session_id: str


def _verify_token(token: str, expected_type: str) -> AccessTokenClaims:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp", "iat", "sub", "ver", "sid", "jti", "role", "type"]},
        )
    except jwt.PyJWTError as exc:
        raise TokenError("Invalid token") from exc
    sub, role = payload.get("sub"), payload.get("role")
    version, session_id = payload.get("ver"), payload.get("sid")
    if payload.get("type") != expected_type:
        raise TokenError("Invalid token type")
    if not isinstance(sub, str) or not sub.isascii() or not sub.isdigit() or int(sub) <= 0:
        raise TokenError("Invalid token subject")
    if not isinstance(role, str) or not role:
        raise TokenError("Invalid token role")
    if (
        type(version) is not int
        or version < 0
        or not isinstance(session_id, str)
        or len(session_id) != 32
    ):
        raise TokenError("Invalid session claims")
    return AccessTokenClaims(sub, role, version, session_id)


def verify_access_token(token: str) -> AccessTokenClaims:
    return _verify_token(token, "access")


def verify_refresh_token(token: str) -> AccessTokenClaims:
    return _verify_token(token, "refresh")
