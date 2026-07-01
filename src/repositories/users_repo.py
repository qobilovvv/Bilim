from datetime import datetime

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from src.models.user import User, UserType
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

    async def delete_user(self, user: User) -> None:
        await self.db.delete(user)
        await self.db.commit()

    async def list_users(
        self,
        status_filter: str | None,
        search: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        offset: int,
        limit: int,
    ) -> tuple[list[User], int]:
        # Base filter: only regular users (not sellers, admins, authors)
        base_filter = User.type == UserType.USER

        # Status filter
        conditions = [base_filter]
        if status_filter == "active":
            conditions.append(User.is_active == True)
            conditions.append(User.is_blocked == False)
        elif status_filter == "inactive":
            conditions.append(User.is_active == False)
            conditions.append(User.is_blocked == False)
        elif status_filter == "blocked":
            conditions.append(User.is_blocked == True)

        # Search by full name (first_name + last_name) using ILIKE
        if search:
            search_term = f"%{search}%"
            full_name_expr = func.concat(User.first_name, ' ', func.coalesce(User.last_name, ''))
            conditions.append(full_name_expr.ilike(search_term))

        # Date range filter on created_at
        if date_from:
            conditions.append(User.created_at >= date_from)
        if date_to:
            conditions.append(User.created_at <= date_to)

        # Count query
        count_stmt = select(func.count()).select_from(User).where(*conditions)
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        # Data query with pagination
        data_stmt = (
            select(User)
            .where(*conditions)
            .order_by(User.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(data_stmt)
        users = list(result.scalars().all())

        return users, total

