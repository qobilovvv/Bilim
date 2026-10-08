from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.models.category import Category
from src.repositories.interfaces import ICategoriesRepository


class CategoriesRepository(ICategoriesRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def lock_tree(self):
        await self.db.execute(text("SELECT pg_advisory_xact_lock(641192)"))

    async def get_by_id(self, id: int) -> Category | None:
        stmt = select(Category).options(joinedload(Category.subcategories)).where(Category.id == id)
        result = await self.db.execute(stmt.execution_options(populate_existing=True))
        return result.unique().scalar_one_or_none()

    async def get_by_path(self, path: str) -> Category | None:
        stmt = (
            select(Category)
            .options(joinedload(Category.subcategories))
            .where(Category.path == path)
        )
        result = await self.db.execute(stmt.execution_options(populate_existing=True))
        return result.unique().scalar_one_or_none()

    async def list_categories(self, active_only: bool = True) -> list[Category]:
        # Return Level 1 categories with their nested subcategories
        stmt = (
            select(Category)
            .options(joinedload(Category.subcategories))
            .where(Category.parent_id.is_(None))
        )
        if active_only:
            stmt = stmt.where(Category.is_active.is_(True))
        if active_only:
            stmt = stmt.options(
                joinedload(Category.subcategories.and_(Category.is_active.is_(True)))
            )
        stmt = stmt.order_by(Category.id).execution_options(populate_existing=True)
        result = await self.db.execute(stmt.execution_options(populate_existing=True))
        # unique() is required when joinedload is used in async queries to avoid duplicates
        return list(result.unique().scalars().all())

    async def create_category(self, category: Category) -> Category:
        self.db.add(category)
        await self.db.flush()
        res = await self.get_by_id(category.id)
        assert res is not None
        return res

    async def update_category(self, category: Category) -> Category:
        self.db.add(category)
        await self.db.flush()
        res = await self.get_by_id(category.id)
        assert res is not None
        return res

    async def delete_category(self, category: Category) -> None:
        await self.db.delete(category)
        await self.db.flush()
