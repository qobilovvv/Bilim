from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from src.models.material import Material
from src.models.lesson import Lesson
from src.models.module import Module
from src.repositories.interfaces import IMaterialsRepository

class MaterialsRepository(IMaterialsRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, id: int) -> Material | None:
        stmt = (
            select(Material)
            .options(joinedload(Material.lesson).joinedload(Lesson.module).joinedload(Module.course))
            .where(Material.id == id)
        )
        result = await self.db.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def create_material(self, material: Material) -> Material:
        self.db.add(material)
        await self.db.commit()
        await self.db.refresh(material)
        res = await self.get_by_id(material.id)
        assert res is not None
        return res

    async def delete_material(self, material: Material) -> None:
        await self.db.delete(material)
        await self.db.commit()
