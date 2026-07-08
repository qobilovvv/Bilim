from fastapi import Depends, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.database import get_db_session
from src.models.course import Course, CourseType
from src.models.user import User, UserType
from src.repositories.courses_repo import CoursesRepository
from src.repositories.categories_repo import CategoriesRepository
from src.repositories.users_repo import UsersRepository
from src.schemas.course_schemas import CourseCreateRequest, CourseUpdateRequest
from src.services.course_permissions import check_course_permission
from src.services.file_storage import save_upload_file, delete_media_file

IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
VIDEO_EXTENSIONS = {"mp4", "mov", "webm", "mkv"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024
MAX_VIDEO_SIZE = 500 * 1024 * 1024

class CoursesService:
    def __init__(self, repo: CoursesRepository, categories_repo: CategoriesRepository, users_repo: UsersRepository):
        self.repo = repo
        self.categories_repo = categories_repo
        self.users_repo = users_repo

    async def create_course(self, data: CourseCreateRequest, current_user: User) -> Course:
        if data.type not in CourseType.ALL:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid type. Allowed: {CourseType.ALL}")

        category = await self.categories_repo.get_by_id(data.category_id)
        if not category:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category not found")

        course = Course(
            name=data.name,
            category_id=data.category_id,
            teacher_id=current_user.id,
            price=data.price,
            type=data.type,
            about_teacher=data.about_teacher,
        )
        return await self.repo.create_course(course)

    async def list_courses(
        self,
        category_id: int | None,
        type_filter: str | None,
        teacher_id: int | None,
        search: str | None,
        active_only: bool,
        page: int,
        page_size: int,
    ) -> tuple[list[Course], int]:
        offset = (page - 1) * page_size
        return await self.repo.list_courses(category_id, type_filter, teacher_id, search, active_only, offset, page_size)

    async def get_course(self, id: int) -> Course:
        course = await self.repo.get_by_id(id)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
        return course

    async def update_course(self, id: int, data: CourseUpdateRequest, current_user: User) -> Course:
        course = await self.get_course(id)
        check_course_permission(course, current_user)

        if data.category_id is not None:
            category = await self.categories_repo.get_by_id(data.category_id)
            if not category:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category not found")
            course.category_id = data.category_id

        if data.teacher_id is not None:
            if current_user.type != UserType.ADMIN:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin can reassign the teacher")
            teacher = await self.users_repo.get_by_id(data.teacher_id)
            if not teacher or teacher.type != UserType.SELLER:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid teacher_id")
            course.teacher_id = data.teacher_id

        if data.type is not None:
            if data.type not in CourseType.ALL:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid type. Allowed: {CourseType.ALL}")
            course.type = data.type

        if data.name is not None:
            course.name = data.name
        if data.price is not None:
            course.price = data.price
        if data.about_teacher is not None:
            course.about_teacher = data.about_teacher
        if data.is_active is not None:
            course.is_active = data.is_active

        return await self.repo.update_course(course)

    async def update_media(
        self,
        id: int,
        current_user: User,
        preview_image: UploadFile | None,
        preview_video: UploadFile | None,
    ) -> Course:
        course = await self.get_course(id)
        check_course_permission(course, current_user)

        if preview_image:
            delete_media_file(course.preview_image)
            course.preview_image = await save_upload_file(
                preview_image, "courses/previews", IMAGE_EXTENSIONS, MAX_IMAGE_SIZE
            )

        if preview_video:
            delete_media_file(course.preview_video)
            course.preview_video = await save_upload_file(
                preview_video, "courses/previews", VIDEO_EXTENSIONS, MAX_VIDEO_SIZE
            )

        return await self.repo.update_course(course)

    async def delete_course(self, id: int, current_user: User) -> None:
        course = await self.get_course(id)
        check_course_permission(course, current_user)
        delete_media_file(course.preview_image)
        delete_media_file(course.preview_video)
        await self.repo.delete_course(course)

async def get_courses_service(db: AsyncSession = Depends(get_db_session)) -> CoursesService:
    return CoursesService(CoursesRepository(db), CategoriesRepository(db), UsersRepository(db))
