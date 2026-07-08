from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from src.models.lesson import Lesson
from src.models.module import Module
from src.models.homework import Homework, TestHomework, TestQuestion
from src.repositories.interfaces import ILessonsRepository

class LessonsRepository(ILessonsRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, id: int) -> Lesson | None:
        stmt = (
            select(Lesson)
            .options(
                joinedload(Lesson.module).joinedload(Module.course),
                selectinload(Lesson.materials),
                selectinload(Lesson.homework)
                .selectinload(Homework.test_detail)
                .selectinload(TestHomework.questions)
                .selectinload(TestQuestion.options),
                selectinload(Lesson.homework).selectinload(Homework.text_detail),
                selectinload(Lesson.homework).selectinload(Homework.file_detail),
            )
            .where(Lesson.id == id)
        )
        result = await self.db.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def create_lesson(self, lesson: Lesson) -> Lesson:
        self.db.add(lesson)
        await self.db.commit()
        await self.db.refresh(lesson)
        res = await self.get_by_id(lesson.id)
        assert res is not None
        return res

    async def update_lesson(self, lesson: Lesson) -> Lesson:
        self.db.add(lesson)
        await self.db.commit()
        await self.db.refresh(lesson)
        res = await self.get_by_id(lesson.id)
        assert res is not None
        return res

    async def delete_lesson(self, lesson: Lesson) -> None:
        await self.db.delete(lesson)
        await self.db.commit()
