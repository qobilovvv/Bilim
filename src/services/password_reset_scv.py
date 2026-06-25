import random
import uuid
import logging
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db_session
from src.infrastructure.eskiz import eskiz_client
from src.models.password_reset import PasswordResetCode
from src.repositories.password_reset_repo import PasswordResetRepository
from src.repositories.users_repo import UsersRepository
from src.security.passwords import hash_password

logger = logging.getLogger(__name__)

class PasswordResetService:
    def __init__(self, reset_repo: PasswordResetRepository, users_repo: UsersRepository):
        self.reset_repo = reset_repo
        self.users_repo = users_repo

    async def send_reset_code(self, phone: str) -> None:
        # 1. Verify user exists with this phone number
        user = await self.users_repo.get_by_phone(phone)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User with this phone number not found"
            )

        # 2. Generate a 6-digit random code
        code = str(random.randint(100000, 999999))

        # 3. Create active reset code record in database
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
        reset_code = PasswordResetCode(
            phone=phone,
            code=code,
            expires_at=expires_at,
            verified=False
        )
        await self.reset_repo.create_reset_code(reset_code)

        # 4. Send code via Eskiz SMS
        try:
            sms_text = f"Bilim: Verification code for password reset: {code}. Do not share this with anyone."
            await eskiz_client.send_sms(phone, sms_text)
        except Exception as e:
            logger.error(f"Failed to send SMS to {phone}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send SMS verification code: {str(e)}"
            )

    async def verify_reset_code(self, phone: str, code: str) -> str:
        # 1. Find active unverified reset code matching phone and code
        reset_code = await self.reset_repo.get_active_code(phone, code)
        if not reset_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification code"
            )

        # 2. Mark code as verified and generate a secure reset token
        token = uuid.uuid4().hex
        reset_code.verified = True
        reset_code.token = token
        # Token is valid for another 15 minutes to reset the password
        reset_code.expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
        
        await self.reset_repo.update_reset_code(reset_code)
        return token

    async def reset_password(self, phone: str, token: str, new_password: str) -> None:
        # 1. Find verified active reset token matching phone and token
        reset_code = await self.reset_repo.get_active_token(phone, token)
        if not reset_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired password reset token"
            )

        # 2. Get the user
        user = await self.users_repo.get_by_phone(phone)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # 3. Hash new password and update user
        user.password = hash_password(new_password)
        await self.users_repo.update_user(user)

        # 4. Invalidate the token so it cannot be reused
        reset_code.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        await self.reset_repo.update_reset_code(reset_code)

async def get_password_reset_service(
    db: AsyncSession = Depends(get_db_session)
) -> PasswordResetService:
    reset_repo = PasswordResetRepository(db)
    users_repo = UsersRepository(db)
    return PasswordResetService(reset_repo, users_repo)
