from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.database import get_db_session
from src.models.module import Module
from src.models.user import User
from src.repositories.modules_repo import ModulesRepository
from src.repositories.courses_repo import CoursesRepository
from src.schemas.course_schemas import ModuleCreateRequest, ModuleUpdateRequest
from src.services.course_permissions import check_course_permission

class ModulesService:
    def __init__(self, repo: ModulesRepository, courses_repo: CoursesRepository):
        self.repo = repo
        self.courses_repo = courses_repo

    async def create_module(self, course_id: int, data: ModuleCreateRequest, current_user: User) -> Module:
        course = await self.courses_repo.get_by_id(course_id)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
        check_course_permission(course, current_user)

        module = Module(
            course_id=course_id,
            name=data.name,
            description=data.description,
            order_index=data.order_index,
        )
        return await self.repo.create_module(module)

    async def _get_owned_module(self, module_id: int, current_user: User) -> Module:
        module = await self.repo.get_by_id(module_id)
        if not module:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
        check_course_permission(module.course, current_user)
        return module

    async def update_module(self, module_id: int, data: ModuleUpdateRequest, current_user: User) -> Module:
        module = await self._get_owned_module(module_id, current_user)

        if data.name is not None:
            module.name = data.name
        if data.description is not None:
            module.description = data.description
        if data.order_index is not None:
            module.order_index = data.order_index

        return await self.repo.update_module(module)

    async def delete_module(self, module_id: int, current_user: User) -> None:
        module = await self._get_owned_module(module_id, current_user)
        await self.repo.delete_module(module)

async def get_modules_service(db: AsyncSession = Depends(get_db_session)) -> ModulesService:
    return ModulesService(ModulesRepository(db), CoursesRepository(db))
