from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from src.models.user import User
from src.repositories.interfaces import IUsersRepository

class UsersRepository(IUsersRepository):

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: int) -> User | None:
        stmt = select(User).options(joinedload(User.seller_profile)).where(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_phone(self, phone: str) -> User | None:
        stmt = select(User).options(joinedload(User.seller_profile)).where(User.phone == phone)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        stmt = select(User).options(joinedload(User.seller_profile)).where(User.username == username)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()


    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).options(joinedload(User.seller_profile)).where(User.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_user(self, user: User) -> User:
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        res = await self.get_by_id(user.id)
        assert res is not None
        return res

    async def update_user(self, user: User) -> User:
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        res = await self.get_by_id(user.id)
        assert res is not None
        return res
