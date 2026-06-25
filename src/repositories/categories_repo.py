from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from src.models.category import Category
from src.repositories.interfaces import ICategoriesRepository

class CategoriesRepository(ICategoriesRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, id: int) -> Category | None:
        stmt = select(Category).options(joinedload(Category.subcategories)).where(Category.id == id)
        result = await self.db.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def get_by_path(self, path: str) -> Category | None:
        stmt = select(Category).options(joinedload(Category.subcategories)).where(Category.path == path)
        result = await self.db.execute(stmt)
        return result.unique().scalar_one_or_none()


    async def list_categories(self, active_only: bool = True) -> list[Category]:
        # Return Level 1 categories with their nested subcategories
        stmt = select(Category).options(joinedload(Category.subcategories)).where(Category.parent_id == None)
        if active_only:
            stmt = stmt.where(Category.is_active == True)
        stmt = stmt.order_by(Category.name)
        result = await self.db.execute(stmt)
        # unique() is required when joinedload is used in async queries to avoid duplicates
        return list(result.unique().scalars().all())

    async def create_category(self, category: Category) -> Category:
        self.db.add(category)
        await self.db.commit()
        await self.db.refresh(category)
        res = await self.get_by_id(category.id)
        assert res is not None
        return res

    async def update_category(self, category: Category) -> Category:
        self.db.add(category)
        await self.db.commit()
        await self.db.refresh(category)
        res = await self.get_by_id(category.id)
        assert res is not None
        return res

    async def delete_category(self, category: Category) -> None:
        await self.db.delete(category)
        await self.db.commit()
