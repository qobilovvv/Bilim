from fastapi import APIRouter, Depends, status, Query
from src.models.user import User
from src.models.category import Category
from src.schemas.category_schemas import (
    CategoryCreateRequest,
    CategoryUpdateRequest,
    CategoryResponse,
)
from src.services.categories_scv import CategoriesService, get_categories_service
from src.security.dependencies import get_current_admin
from src.security.localization import get_accept_language

router = APIRouter(prefix="/categories", tags=["Categories"])

def serialize_category(cat: Category, lang: str) -> dict:
    """
    Helper to serialize a Category model to CategoryResponse dictionary,
    resolving the localized name from the JSONB name dictionary based on the preferred language.
    """
    # 1. Resolve localized name for parent category
    localized_name = cat.name.get(lang) if isinstance(cat.name, dict) else None
    if not localized_name:
        for l in ["uz", "ru", "en"]:
            if isinstance(cat.name, dict):
                localized_name = cat.name.get(l)
                if localized_name:
                    break
    if not localized_name:
        localized_name = ""

    # 2. Serialize subcategories
    subcategories = []
    if cat.subcategories:
        for sub in cat.subcategories:
            sub_name = sub.name.get(lang) if isinstance(sub.name, dict) else None
            if not sub_name:
                for l in ["uz", "ru", "en"]:
                    if isinstance(sub.name, dict):
                        sub_name = sub.name.get(l)
                        if sub_name:
                            break
            if not sub_name:
                sub_name = ""
            subcategories.append({
                "id": sub.id,
                "name": sub_name,
                "path": sub.path,
                "parent_id": sub.parent_id,
                "level": sub.level,
                "is_active": sub.is_active,
                "created_at": sub.created_at,
                "updated_at": sub.updated_at
            })

    return {
        "id": cat.id,
        "name": localized_name,
        "path": cat.path,
        "parent_id": cat.parent_id,
        "level": cat.level,
        "is_active": cat.is_active,
        "created_at": cat.created_at,
        "updated_at": cat.updated_at,
        "subcategories": subcategories
    }

@router.get("", response_model=list[CategoryResponse])
async def list_categories(
    active_only: bool = Query(True, description="Filter only active categories"),
    lang: str = Depends(get_accept_language),
    service: CategoriesService = Depends(get_categories_service)
):
    categories = await service.list_categories(active_only=active_only)
    return [serialize_category(cat, lang) for cat in categories]

@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    data: CategoryCreateRequest,
    current_admin: User = Depends(get_current_admin),
    lang: str = Depends(get_accept_language),
    service: CategoriesService = Depends(get_categories_service)
):
    cat = await service.create_category(data)
    return serialize_category(cat, lang)

@router.put("/{id}", response_model=CategoryResponse)
async def update_category(
    id: int,
    data: CategoryUpdateRequest,
    current_admin: User = Depends(get_current_admin),
    lang: str = Depends(get_accept_language),
    service: CategoriesService = Depends(get_categories_service)
):
    cat = await service.update_category(id, data)
    return serialize_category(cat, lang)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    id: int,
    current_admin: User = Depends(get_current_admin),
    service: CategoriesService = Depends(get_categories_service)
):
    await service.delete_category(id)
