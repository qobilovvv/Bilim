from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from src.models.module import Module
from src.models.lesson import Lesson
from src.models.homework import Homework, TestHomework, TestQuestion
from src.repositories.interfaces import IModulesRepository

class ModulesRepository(IModulesRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, id: int) -> Module | None:
        stmt = (
            select(Module)
            .options(
                joinedload(Module.course),
                selectinload(Module.lessons).selectinload(Lesson.materials),
                selectinload(Module.lessons)
                .selectinload(Lesson.homework)
                .selectinload(Homework.test_detail)
                .selectinload(TestHomework.questions)
                .selectinload(TestQuestion.options),
                selectinload(Module.lessons).selectinload(Lesson.homework).selectinload(Homework.text_detail),
                selectinload(Module.lessons).selectinload(Lesson.homework).selectinload(Homework.file_detail),
            )
            .where(Module.id == id)
        )
        result = await self.db.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def create_module(self, module: Module) -> Module:
        self.db.add(module)
        await self.db.commit()
        await self.db.refresh(module)
        res = await self.get_by_id(module.id)
        assert res is not None
        return res

    async def update_module(self, module: Module) -> Module:
        self.db.add(module)
        await self.db.commit()
        await self.db.refresh(module)
        res = await self.get_by_id(module.id)
        assert res is not None
        return res

    async def delete_module(self, module: Module) -> None:
        await self.db.delete(module)
        await self.db.commit()
