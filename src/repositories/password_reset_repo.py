from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func
from src.models.password_reset import PasswordResetCode
from src.repositories.interfaces import IPasswordResetRepository

class PasswordResetRepository(IPasswordResetRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_reset_code(self, reset_code: PasswordResetCode) -> PasswordResetCode:
        self.db.add(reset_code)
        await self.db.commit()
        await self.db.refresh(reset_code)
        return reset_code

    async def get_active_code(self, phone: str, code: str) -> PasswordResetCode | None:
        stmt = (
            select(PasswordResetCode)
            .where(
                and_(
                    PasswordResetCode.phone == phone,
                    PasswordResetCode.code == code,
                    PasswordResetCode.verified == False,
                    PasswordResetCode.expires_at > func.now()
                )
            )
            .order_by(PasswordResetCode.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_token(self, phone: str, token: str) -> PasswordResetCode | None:
        stmt = (
            select(PasswordResetCode)
            .where(
                and_(
                    PasswordResetCode.phone == phone,
                    PasswordResetCode.token == token,
                    PasswordResetCode.verified == True,
                    PasswordResetCode.expires_at > func.now()
                )
            )
            .order_by(PasswordResetCode.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_reset_code(self, reset_code: PasswordResetCode) -> PasswordResetCode:
        self.db.add(reset_code)
        await self.db.commit()
        await self.db.refresh(reset_code)
        return reset_code
