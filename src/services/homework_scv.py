from fastapi import Depends, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.database import get_db_session
from src.models.homework import (
    Homework,
    HomeworkType,
    TestHomework,
    TestQuestion,
    TestQuestionOption,
    TextHomework,
    FileHomework,
)
from src.models.user import User
from src.repositories.homework_repo import HomeworkRepository
from src.repositories.lessons_repo import LessonsRepository
from src.schemas.course_schemas import HomeworkUpsertRequest
from src.services.course_permissions import check_course_permission
from src.services.file_storage import save_upload_file, delete_media_file

MIN_DEADLINE_DAYS = 2
MAX_DEADLINE_DAYS = 8
EXAMPLE_FILE_EXTENSIONS = {
    "pdf", "ppt", "pptx", "doc", "docx", "xls", "xlsx", "csv", "zip", "rar", "txt"
}
MAX_EXAMPLE_FILE_SIZE = 50 * 1024 * 1024

def _build_test_detail(data: HomeworkUpsertRequest) -> TestHomework:
    if data.pass_ball is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="pass_ball is required for test homework")
    if not data.questions:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Test homework must have at least one question")

    questions = []
    for i, q in enumerate(data.questions):
        if not q.options:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Question '{q.text}' must have options")
        if not any(o.is_correct for o in q.options):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Question '{q.text}' must have at least one correct option")
        options = [
            TestQuestionOption(text=o.text, is_correct=o.is_correct, order_index=j)
            for j, o in enumerate(q.options)
        ]
        questions.append(TestQuestion(text=q.text, ball=q.ball, order_index=i, options=options))

    return TestHomework(timer_minutes=data.timer_minutes, pass_ball=data.pass_ball, questions=questions)

def _build_text_detail(data: HomeworkUpsertRequest) -> TextHomework:
    if data.deadline_days is None or not (MIN_DEADLINE_DAYS <= data.deadline_days <= MAX_DEADLINE_DAYS):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"deadline_days must be between {MIN_DEADLINE_DAYS} and {MAX_DEADLINE_DAYS}")
    if data.pass_ball is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="pass_ball is required for text homework")
    if data.min_words is None or data.min_words <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="min_words must be a positive number")

    return TextHomework(
        deadline_days=data.deadline_days,
        pass_ball=data.pass_ball,
        min_words=data.min_words,
        grading_criteria=data.grading_criteria,
    )

def _build_file_detail(data: HomeworkUpsertRequest) -> FileHomework:
    if data.deadline_days is None or not (MIN_DEADLINE_DAYS <= data.deadline_days <= MAX_DEADLINE_DAYS):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"deadline_days must be between {MIN_DEADLINE_DAYS} and {MAX_DEADLINE_DAYS}")
    if not data.file_formats:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="file_formats must not be empty")
    if data.max_file_size_mb is None or data.max_file_size_mb <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="max_file_size_mb must be a positive number")

    return FileHomework(
        deadline_days=data.deadline_days,
        file_formats=data.file_formats,
        max_file_size_mb=data.max_file_size_mb,
    )

class HomeworkService:
    def __init__(self, repo: HomeworkRepository, lessons_repo: LessonsRepository):
        self.repo = repo
        self.lessons_repo = lessons_repo

    async def _get_owned_lesson(self, lesson_id: int, current_user: User):
        lesson = await self.lessons_repo.get_by_id(lesson_id)
        if not lesson:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
        check_course_permission(lesson.module.course, current_user)
        return lesson

    async def get_homework(self, lesson_id: int) -> Homework | None:
        return await self.repo.get_by_lesson_id(lesson_id)

    async def upsert_homework(self, lesson_id: int, data: HomeworkUpsertRequest, current_user: User) -> Homework | None:
        await self._get_owned_lesson(lesson_id, current_user)

        if data.type not in HomeworkType.ALL:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid type. Allowed: {HomeworkType.ALL}")

        existing = await self.repo.get_by_lesson_id(lesson_id)
        if existing:
            if existing.file_detail and existing.file_detail.example_file:
                delete_media_file(existing.file_detail.example_file)
            await self.repo.delete_homework(existing)

        if data.type == HomeworkType.NONE:
            return None

        homework = Homework(lesson_id=lesson_id, type=data.type, name=data.name, description=data.description)

        if data.type == HomeworkType.TEST:
            homework.test_detail = _build_test_detail(data)
        elif data.type == HomeworkType.TEXT:
            homework.text_detail = _build_text_detail(data)
        elif data.type == HomeworkType.FILE:
            homework.file_detail = _build_file_detail(data)

        return await self.repo.create_homework(homework)

    async def upload_example_file(self, lesson_id: int, file: UploadFile, current_user: User) -> Homework:
        await self._get_owned_lesson(lesson_id, current_user)

        homework = await self.repo.get_by_lesson_id(lesson_id)
        if not homework or homework.type != HomeworkType.FILE or not homework.file_detail:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lesson has no file-type homework")

        delete_media_file(homework.file_detail.example_file)
        homework.file_detail.example_file = await save_upload_file(
            file, "homeworks/examples", EXAMPLE_FILE_EXTENSIONS, MAX_EXAMPLE_FILE_SIZE
        )
        return await self.repo.update_homework(homework)

    async def delete_homework(self, lesson_id: int, current_user: User) -> None:
        await self._get_owned_lesson(lesson_id, current_user)
        homework = await self.repo.get_by_lesson_id(lesson_id)
        if not homework:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Homework not found")
        if homework.file_detail and homework.file_detail.example_file:
            delete_media_file(homework.file_detail.example_file)
        await self.repo.delete_homework(homework)

async def get_homework_service(db: AsyncSession = Depends(get_db_session)) -> HomeworkService:
    return HomeworkService(HomeworkRepository(db), LessonsRepository(db))
