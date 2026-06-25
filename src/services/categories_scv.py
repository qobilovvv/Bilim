from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.database import get_db_session
from src.models.category import Category
from src.repositories.categories_repo import CategoriesRepository
from src.schemas.category_schemas import CategoryCreateRequest, CategoryUpdateRequest

class CategoriesService:
    def __init__(self, repo: CategoriesRepository):
        self.repo = repo

    async def create_category(self, data: CategoryCreateRequest) -> Category:
        # Normalize path to ensure it starts with / and is clean
        clean_path = "/" + data.path.strip("/")
        
        # Check uniqueness of the path
        existing = await self.repo.get_by_path(clean_path)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category path '{clean_path}' already exists"
            )

        level = 1
        if data.parent_id is not None:
            parent = await self.repo.get_by_id(data.parent_id)
            if not parent:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Parent category not found"
                )
            if parent.level >= 2:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot nest categories below level 2 (max depth exceeded)"
                )
            level = 2

        new_cat = Category(
            name=data.name.model_dump(),
            path=clean_path,
            parent_id=data.parent_id,
            level=level,
            is_active=data.is_active
        )
        return await self.repo.create_category(new_cat)

    async def list_categories(self, active_only: bool = True) -> list[Category]:
        return await self.repo.list_categories(active_only)

    async def update_category(self, id: int, data: CategoryUpdateRequest) -> Category:
        category = await self.repo.get_by_id(id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )

        # Update path
        if data.path is not None:
            clean_path = "/" + data.path.strip("/")
            if clean_path != category.path:
                existing = await self.repo.get_by_path(clean_path)
                if existing:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Category path '{clean_path}' already exists"
                    )
                category.path = clean_path

        # Update parent_id and level hierarchy
        if data.parent_id is not None:
            if data.parent_id == category.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A category cannot be its own parent"
                )
            
            if data.parent_id != category.parent_id:
                parent = await self.repo.get_by_id(data.parent_id)
                if not parent:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Parent category not found"
                    )
                if parent.level >= 2:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Cannot nest categories below level 2 (max depth exceeded)"
                    )
                category.parent_id = data.parent_id
                category.level = 2
        elif "parent_id" in data.model_fields_set and data.parent_id is None:
            # Explicitly setting parent_id to None (moving subcategory to top-level category)
            category.parent_id = None
            category.level = 1

        if data.name is not None:
            category.name = data.name.model_dump()

        if data.is_active is not None:
            category.is_active = data.is_active

        return await self.repo.update_category(category)

    async def delete_category(self, id: int) -> None:
        category = await self.repo.get_by_id(id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        await self.repo.delete_category(category)

async def get_categories_service(db: AsyncSession = Depends(get_db_session)) -> CategoriesService:
    repo = CategoriesRepository(db)
    return CategoriesService(repo)
