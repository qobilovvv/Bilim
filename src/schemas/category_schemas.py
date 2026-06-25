from pydantic import BaseModel, ConfigDict
from datetime import datetime

class LocalizedString(BaseModel):
    ru: str
    uz: str
    en: str

class CategoryCreateRequest(BaseModel):
    name: LocalizedString
    path: str
    parent_id: int | None = None
    is_active: bool = True

class CategoryUpdateRequest(BaseModel):
    name: LocalizedString | None = None
    path: str | None = None
    parent_id: int | None = None
    is_active: bool | None = None

class SubcategoryResponse(BaseModel):
    id: int
    name: str  # Localized name depending on Accept-Language
    path: str
    parent_id: int | None
    level: int
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

class CategoryResponse(BaseModel):
    id: int
    name: str  # Localized name depending on Accept-Language
    path: str
    parent_id: int | None
    level: int
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None
    subcategories: list[SubcategoryResponse] = []

    model_config = ConfigDict(from_attributes=True)
