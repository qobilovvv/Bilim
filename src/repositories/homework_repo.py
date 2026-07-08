from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from src.models.homework import Homework, TestHomework, TestQuestion
from src.models.lesson import Lesson
from src.models.module import Module
from src.repositories.interfaces import IHomeworkRepository

def _detail_options():
    return (
        joinedload(Homework.lesson).joinedload(Lesson.module).joinedload(Module.course),
        selectinload(Homework.test_detail).selectinload(TestHomework.questions).selectinload(TestQuestion.options),
        selectinload(Homework.text_detail),
        selectinload(Homework.file_detail),
    )

class HomeworkRepository(IHomeworkRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_lesson_id(self, lesson_id: int) -> Homework | None:
        stmt = select(Homework).options(*_detail_options()).where(Homework.lesson_id == lesson_id)
        result = await self.db.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def create_homework(self, homework: Homework) -> Homework:
        self.db.add(homework)
        await self.db.commit()
        await self.db.refresh(homework)
        res = await self.get_by_lesson_id(homework.lesson_id)
        assert res is not None
        return res

    async def update_homework(self, homework: Homework) -> Homework:
        self.db.add(homework)
        await self.db.commit()
        await self.db.refresh(homework)
        res = await self.get_by_lesson_id(homework.lesson_id)
        assert res is not None
        return res

    async def delete_homework(self, homework: Homework) -> None:
        await self.db.delete(homework)
        await self.db.commit()
