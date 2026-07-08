from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.models.course import Course
from src.models.module import Module
from src.models.lesson import Lesson
from src.models.homework import Homework, TestHomework, TestQuestion
from src.repositories.interfaces import ICoursesRepository

def _full_tree_options():
    return (
        selectinload(Course.category),
        selectinload(Course.teacher),
        selectinload(Course.modules)
        .selectinload(Module.lessons)
        .selectinload(Lesson.materials),
        selectinload(Course.modules)
        .selectinload(Module.lessons)
        .selectinload(Lesson.homework)
        .selectinload(Homework.test_detail)
        .selectinload(TestHomework.questions)
        .selectinload(TestQuestion.options),
        selectinload(Course.modules)
        .selectinload(Module.lessons)
        .selectinload(Lesson.homework)
        .selectinload(Homework.text_detail),
        selectinload(Course.modules)
        .selectinload(Module.lessons)
        .selectinload(Lesson.homework)
        .selectinload(Homework.file_detail),
    )

class CoursesRepository(ICoursesRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, id: int) -> Course | None:
        stmt = select(Course).options(*_full_tree_options()).where(Course.id == id)
        result = await self.db.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def list_courses(
        self,
        category_id: int | None,
        type_filter: str | None,
        teacher_id: int | None,
        search: str | None,
        active_only: bool,
        offset: int,
        limit: int,
    ) -> tuple[list[Course], int]:
        stmt = select(Course).options(
            selectinload(Course.category), selectinload(Course.teacher)
        )
        count_stmt = select(func.count()).select_from(Course)

        conditions = []
        if category_id is not None:
            conditions.append(Course.category_id == category_id)
        if type_filter is not None:
            conditions.append(Course.type == type_filter)
        if teacher_id is not None:
            conditions.append(Course.teacher_id == teacher_id)
        if active_only:
            conditions.append(Course.is_active == True)
        if search:
            conditions.append(Course.name.ilike(f"%{search}%"))

        for cond in conditions:
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)

        stmt = stmt.order_by(Course.created_at.desc()).offset(offset).limit(limit)

        result = await self.db.execute(stmt)
        total = (await self.db.execute(count_stmt)).scalar_one()
        return list(result.unique().scalars().all()), total

    async def create_course(self, course: Course) -> Course:
        self.db.add(course)
        await self.db.commit()
        await self.db.refresh(course)
        res = await self.get_by_id(course.id)
        assert res is not None
        return res

    async def update_course(self, course: Course) -> Course:
        self.db.add(course)
        await self.db.commit()
        await self.db.refresh(course)
        res = await self.get_by_id(course.id)
        assert res is not None
        return res

    async def delete_course(self, course: Course) -> None:
        await self.db.delete(course)
        await self.db.commit()
