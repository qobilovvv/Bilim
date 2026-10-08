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
        await self.db.flush()
        await self.db.refresh(reset_code)
        return reset_code

    async def invalidate_for_phone(self, phone):
        from sqlalchemy import update
        await self.db.execute(update(PasswordResetCode).where(PasswordResetCode.phone == phone)
                              .values(expires_at=func.now()))

    async def get_latest_challenge(self, phone):
        stmt = (select(PasswordResetCode).where(PasswordResetCode.phone == phone,
                PasswordResetCode.verified.is_(False), PasswordResetCode.expires_at > func.now())
                .order_by(PasswordResetCode.created_at.desc(), PasswordResetCode.id.desc())
                .limit(1).with_for_update())
        return (await self.db.execute(stmt)).scalar_one_or_none()

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
            .order_by(PasswordResetCode.created_at.desc()).limit(1).with_for_update()
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
            .order_by(PasswordResetCode.created_at.desc()).limit(1).with_for_update()
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_reset_code(self, reset_code: PasswordResetCode) -> PasswordResetCode:
        self.db.add(reset_code)
        await self.db.flush()
        await self.db.refresh(reset_code)
        return reset_code
