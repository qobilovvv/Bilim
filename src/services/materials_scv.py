from fastapi import Depends, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.database import get_db_session
from src.models.material import Material
from src.models.user import User
from src.repositories.materials_repo import MaterialsRepository
from src.repositories.lessons_repo import LessonsRepository
from src.services.course_permissions import check_course_permission
from src.services.file_storage import save_upload_file, delete_media_file

MATERIAL_EXTENSIONS = {
    "pdf", "ppt", "pptx", "doc", "docx", "xls", "xlsx", "csv", "zip", "rar", "txt"
}
MAX_MATERIAL_SIZE = 100 * 1024 * 1024

class MaterialsService:
    def __init__(self, repo: MaterialsRepository, lessons_repo: LessonsRepository):
        self.repo = repo
        self.lessons_repo = lessons_repo

    async def create_material(self, lesson_id: int, name: str, file: UploadFile, current_user: User) -> Material:
        lesson = await self.lessons_repo.get_by_id(lesson_id)
        if not lesson:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
        check_course_permission(lesson.module.course, current_user)

        file_path = await save_upload_file(file, "lessons/materials", MATERIAL_EXTENSIONS, MAX_MATERIAL_SIZE)
        material = Material(lesson_id=lesson_id, name=name, file=file_path)
        return await self.repo.create_material(material)

    async def delete_material(self, material_id: int, current_user: User) -> None:
        material = await self.repo.get_by_id(material_id)
        if not material:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")
        check_course_permission(material.lesson.module.course, current_user)
        delete_media_file(material.file)
        await self.repo.delete_material(material)

async def get_materials_service(db: AsyncSession = Depends(get_db_session)) -> MaterialsService:
    return MaterialsService(MaterialsRepository(db), LessonsRepository(db))
