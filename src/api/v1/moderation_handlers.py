from datetime import date, datetime, time

from fastapi import APIRouter, Depends, Query, status
from src.models.user import User, UserType
from src.schemas.auth_schemas import UserListResponse, UserResponse, AdminUserUpdateRequest
from src.schemas.course_schemas import CourseModerationListResponse, CourseModerationListItemResponse
from src.services.users_scv import UsersService, get_users_service
from src.services.courses_scv import CoursesService, get_courses_service
from src.security.dependencies import get_current_admin

router = APIRouter(prefix="/moderation", tags=["moderation"])


@router.get("/users", response_model=UserListResponse)
async def list_users(
    status_filter: str = Query("all", alias="status", description="Filter: all, active, inactive, blocked"),
    search: str | None = Query(None, description="Search by full name"),
    date_from: date | None = Query(None, description="Filter users created from this date"),
    date_to: date | None = Query(None, description="Filter users created until this date"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_admin: User = Depends(get_current_admin),
    service: UsersService = Depends(get_users_service),
):
    # Convert date to datetime for range filtering
    dt_from = datetime.combine(date_from, time.min) if date_from else None
    dt_to = datetime.combine(date_to, time.max) if date_to else None

    filter_value = status_filter if status_filter != "all" else None
    items, total = await service.list_users(
        status_filter=filter_value,
        search=search,
        date_from=dt_from,
        date_to=dt_to,
        limit=limit,
        offset=offset,
        user_type=UserType.USER,
    )
    return UserListResponse(total=total, limit=limit, offset=offset, result=items)


@router.get("/teachers", response_model=UserListResponse)
async def list_teachers(
    status_filter: str = Query("all", alias="status", description="Filter: all, active, inactive, blocked"),
    search: str | None = Query(None, description="Search by full name"),
    date_from: date | None = Query(None, description="Filter teachers created from this date"),
    date_to: date | None = Query(None, description="Filter teachers created until this date"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_admin: User = Depends(get_current_admin),
    service: UsersService = Depends(get_users_service),
):
    dt_from = datetime.combine(date_from, time.min) if date_from else None
    dt_to = datetime.combine(date_to, time.max) if date_to else None

    filter_value = status_filter if status_filter != "all" else None
    items, total = await service.list_users(
        status_filter=filter_value,
        search=search,
        date_from=dt_from,
        date_to=dt_to,
        limit=limit,
        offset=offset,
        user_type=UserType.SELLER,
    )
    return UserListResponse(total=total, limit=limit, offset=offset, result=items)


@router.get("/courses", response_model=CourseModerationListResponse)
async def list_courses_for_moderation(
    category_id: int | None = Query(None),
    type: str | None = Query(None),
    teacher_id: int | None = Query(None),
    search: str | None = Query(None),
    active_only: bool = Query(False, description="Set true to only show active courses"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_admin: User = Depends(get_current_admin),
    service: CoursesService = Depends(get_courses_service),
):
    """Admin endpoint listing all courses (active and inactive), with full teacher contact info."""
    items, total = await service.list_courses(category_id, type, teacher_id, search, active_only, limit, offset)
    return CourseModerationListResponse(
        total=total,
        limit=limit,
        offset=offset,
        result=[CourseModerationListItemResponse.model_validate(c) for c in items],
    )


@router.put("/users/{user_id}", response_model=UserResponse)
async def edit_user(
    user_id: int,
    data: AdminUserUpdateRequest,
    current_admin: User = Depends(get_current_admin),
    service: UsersService = Depends(get_users_service),
):
    """Admin endpoint to update user details, including active/blocked status."""
    return await service.admin_update_user(user_id, data)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_admin: User = Depends(get_current_admin),
    service: UsersService = Depends(get_users_service),
):
    """Admin endpoint to hard delete a user."""
    await service.admin_delete_user(user_id)

