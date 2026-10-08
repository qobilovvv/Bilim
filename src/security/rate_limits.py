"""Database-backed authentication throttles shared by all API workers."""

import hashlib
import hmac
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request
from sqlalchemy import case, delete
from sqlalchemy.dialects.postgresql import insert

from src.infrastructure.config import settings
from src.infrastructure.database import AsyncSessionFactory
from src.models.auth_session import AuthRateLimit


async def check_rate_limit(action, identity, limit, seconds):
    key = hmac.new(
        settings.JWT_SECRET_KEY.encode(), f"{action}:{identity}".encode(), hashlib.sha256
    ).hexdigest()
    now = datetime.now(timezone.utc)
    expired = AuthRateLimit.expires_at <= now
    stmt = insert(AuthRateLimit).values(
        key=key, count=1, expires_at=now + timedelta(seconds=seconds)
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[AuthRateLimit.key],
        set_={
            "count": case((expired, 1), else_=AuthRateLimit.count + 1),
            "expires_at": case((expired, stmt.excluded.expires_at), else_=AuthRateLimit.expires_at),
        },
    ).returning(AuthRateLimit.count, AuthRateLimit.expires_at)
    # Independent commit preserves attempt counts even when the API request is rejected.
    async with AsyncSessionFactory() as db:
        count, expires = (await db.execute(stmt)).one()
        await db.execute(
            delete(AuthRateLimit).where(AuthRateLimit.expires_at < now - timedelta(days=1))
        )
        await db.commit()
    if count > limit:
        raise HTTPException(
            429,
            "Too many attempts; try again later",
            headers={"Retry-After": str(max(1, int((expires - now).total_seconds())))},
        )


async def rate_limit_auth(request: Request):
    action = request.url.path.rsplit("/", 1)[-1]
    policies = {
        "login": (20, 60),
        "register": (5, 60),
        "send-code": (3, 900),
        "verify-code": (10, 300),
        "new-password": (10, 300),
        "refresh": (30, 60),
    }
    if action not in policies or request.method != "POST":
        return
    limit, seconds = policies[action]
    address = request.client.host if request.client else "unknown"
    await check_rate_limit(f"ip:{action}", address, limit, seconds)
    try:
        payload = await request.json()
    except ValueError:
        return
    if isinstance(payload, dict):
        identity = payload.get("phone") or payload.get("username")
        if isinstance(identity, str) and len(identity) <= 256:
            identity = identity.strip()
            if "phone" in payload:
                identity = "".join(char for char in identity if char.isdigit())
            await check_rate_limit(f"account:{action}", identity, limit, seconds)
