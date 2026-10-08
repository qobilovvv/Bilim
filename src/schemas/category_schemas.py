from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.schemas.validation import Name, PatchModel, PositiveId, RequestModel


class LocalizedString(RequestModel):
    ru: Name
    uz: Name
    en: Name


class CategoryCreateRequest(RequestModel):
    name: LocalizedString
    path: str = Field(
        min_length=1, max_length=200, pattern=r"^/?[a-zA-Z0-9_-]+(?:/[a-zA-Z0-9_-]+)*/?$"
    )
    parent_id: PositiveId | None = None
    is_active: bool = True


class CategoryUpdateRequest(PatchModel):
    nullable_fields = {"parent_id"}
    name: LocalizedString | None = None
    path: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
        pattern=r"^/?[a-zA-Z0-9_-]+(?:/[a-zA-Z0-9_-]+)*/?$",
    )
    parent_id: PositiveId | None = None
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
