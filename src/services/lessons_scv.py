from fastapi import Depends, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.database import get_db_session
from src.models.lesson import Lesson
from src.models.user import User
from src.repositories.lessons_repo import LessonsRepository
from src.repositories.modules_repo import ModulesRepository
from src.schemas.course_schemas import LessonCreateRequest, LessonUpdateRequest
from src.services.course_permissions import check_course_permission
from src.services.file_storage import save_upload_file, delete_media_file

VIDEO_EXTENSIONS = {"mp4", "mov", "webm", "mkv"}
MAX_VIDEO_SIZE = 500 * 1024 * 1024

class LessonsService:
    def __init__(self, repo: LessonsRepository, modules_repo: ModulesRepository):
        self.repo = repo
        self.modules_repo = modules_repo

    async def create_lesson(self, module_id: int, data: LessonCreateRequest, current_user: User) -> Lesson:
        module = await self.modules_repo.get_by_id(module_id)
        if not module:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
        check_course_permission(module.course, current_user)

        lesson = Lesson(
            module_id=module_id,
            name=data.name,
            description=data.description,
            order_index=data.order_index,
        )
        return await self.repo.create_lesson(lesson)

    async def _get_owned_lesson(self, lesson_id: int, current_user: User) -> Lesson:
        lesson = await self.repo.get_by_id(lesson_id)
        if not lesson:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
        check_course_permission(lesson.module.course, current_user)
        return lesson

    async def update_lesson(self, lesson_id: int, data: LessonUpdateRequest, current_user: User) -> Lesson:
        lesson = await self._get_owned_lesson(lesson_id, current_user)

        if data.name is not None:
            lesson.name = data.name
        if data.description is not None:
            lesson.description = data.description
        if data.order_index is not None:
            lesson.order_index = data.order_index

        return await self.repo.update_lesson(lesson)

    async def update_video(self, lesson_id: int, video: UploadFile, current_user: User) -> Lesson:
        lesson = await self._get_owned_lesson(lesson_id, current_user)
        delete_media_file(lesson.video)
        lesson.video = await save_upload_file(video, "lessons/videos", VIDEO_EXTENSIONS, MAX_VIDEO_SIZE)
        return await self.repo.update_lesson(lesson)

    async def delete_lesson(self, lesson_id: int, current_user: User) -> None:
        lesson = await self._get_owned_lesson(lesson_id, current_user)
        delete_media_file(lesson.video)
        await self.repo.delete_lesson(lesson)

async def get_lessons_service(db: AsyncSession = Depends(get_db_session)) -> LessonsService:
    return LessonsService(LessonsRepository(db), ModulesRepository(db))
