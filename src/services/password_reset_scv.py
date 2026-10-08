import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.config import settings
from src.infrastructure.database import get_db_session
from src.infrastructure.eskiz import eskiz_client
from src.models.password_reset import PasswordResetCode
from src.repositories.password_reset_repo import PasswordResetRepository
from src.repositories.sessions_repo import SessionsRepository
from src.repositories.users_repo import UsersRepository
from src.security.passwords import hash_password_async

logger = logging.getLogger(__name__)


def code_digest(phone, code):
    return hmac.new(settings.JWT_SECRET_KEY.encode(), f"reset:{phone}:{code}".encode(), hashlib.sha256).hexdigest()


class PasswordResetService:
    def __init__(self, reset_repo, users_repo):
        self.reset_repo = reset_repo
        self.users_repo = users_repo

    async def send_reset_code(self, phone: str) -> None:
        user = await self.users_repo.get_by_phone_for_update(phone)
        if not user or not user.is_active or user.is_blocked:
            return  # Same response for unknown and unavailable accounts.
        await self.reset_repo.invalidate_for_phone(phone)
        code = str(secrets.randbelow(900000) + 100000)
        reset = PasswordResetCode(phone=phone, code=code_digest(phone, code), attempts=0,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5), verified=False)
        await self.reset_repo.create_reset_code(reset)
        try:
            await eskiz_client.send_sms(phone, f"Bilim: Password reset code: {code}. Do not share it.")
        except Exception as exc:
            logger.warning("Password reset SMS provider failed", exc_info=False)
            raise HTTPException(502, "Verification service temporarily unavailable") from exc

    async def verify_reset_code(self, phone: str, code: str) -> str | None:
        user = await self.users_repo.get_by_phone_for_update(phone)
        if not user or not user.is_active or user.is_blocked:
            return None
        reset = await self.reset_repo.get_latest_challenge(phone)
        if not reset or reset.attempts >= 5:
            return None
        if not secrets.compare_digest(reset.code, code_digest(phone, code)):
            reset.attempts += 1
            await self.reset_repo.update_reset_code(reset)
            # Return an error response instead of raising, so the attempt counter commits.
            return None
        token = secrets.token_urlsafe(32)
        reset.verified = True
        reset.token = hashlib.sha256(token.encode()).hexdigest()
        reset.expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
        await self.reset_repo.update_reset_code(reset)
        return token

    async def reset_password(self, phone: str, token: str, new_password: str) -> None:
        user = await self.users_repo.get_by_phone_for_update(phone)
        if not user or not user.is_active or user.is_blocked:
            raise HTTPException(400, "Invalid or expired password reset token")
        reset = await self.reset_repo.get_active_token(phone, hashlib.sha256(token.encode()).hexdigest())
        if not reset:
            raise HTTPException(400, "Invalid or expired password reset token")
        user.password = await hash_password_async(new_password)
        user.auth_version += 1
        await SessionsRepository(self.users_repo.db).revoke_all(user.id)
        await self.reset_repo.invalidate_for_phone(phone)
        await self.users_repo.db.flush()


def get_password_reset_service(db: AsyncSession = Depends(get_db_session, scope="function")):
    return PasswordResetService(PasswordResetRepository(db), UsersRepository(db))
