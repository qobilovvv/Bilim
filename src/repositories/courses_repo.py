from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.models.category import Category
from src.models.user import User
from src.models.course import Course
from src.models.module import Module
from src.models.lesson import Lesson
from src.models.homework import Homework, TestHomework, TestQuestion
from src.repositories.interfaces import ICoursesRepository
from src.repositories.course_visibility import public_course_conditions

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

    async def get_reference(self, id: int) -> Course | None:
        stmt = select(Course).where(Course.id == id)
        return (await self.db.execute(stmt)).unique().scalar_one_or_none()

    async def get_by_id(self, id: int) -> Course | None:
        stmt = select(Course).options(*_full_tree_options()).where(Course.id == id)
        result = await self.db.execute(stmt.execution_options(populate_existing=True))
        return result.unique().scalar_one_or_none()

    async def get_public_by_id(self, id: int) -> Course | None:
        stmt = (select(Course).join(Course.category).join(Course.teacher)
                .where(Course.id == id, *public_course_conditions())
                .options(selectinload(Course.category), selectinload(Course.teacher),
                         selectinload(Course.modules).selectinload(Module.lessons)))
        return (await self.db.execute(stmt)).scalar_one_or_none()

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
            conditions.extend(public_course_conditions())
        if search:
            conditions.append(Course.name.ilike(f"%{search}%"))

        for cond in conditions:
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)

        stmt = stmt.order_by(Course.created_at.desc(), Course.id.desc()).offset(offset).limit(limit)

        result = await self.db.execute(stmt.execution_options(populate_existing=True))
        total = (await self.db.execute(count_stmt)).scalar_one()
        return list(result.unique().scalars().all()), total

    async def create_course(self, course: Course) -> Course:
        self.db.add(course)
        await self.db.flush()
        res = await self.get_by_id(course.id)
        assert res is not None
        return res

    async def update_course(self, course: Course) -> Course:
        self.db.add(course)
        await self.db.flush()
        res = await self.get_by_id(course.id)
        assert res is not None
        return res

    async def delete_course(self, course: Course) -> None:
        await self.db.delete(course)
        await self.db.flush()
