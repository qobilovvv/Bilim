from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from src.models.user import User
from src.schemas.course_schemas import (
    CourseCreateRequest,
    CourseUpdateRequest,
    CourseResponse,
    CourseListResponse,
    CourseListItemResponse,
    ModuleCreateRequest,
    ModuleUpdateRequest,
    ModuleResponse,
    LessonCreateRequest,
    LessonUpdateRequest,
    LessonResponse,
    MaterialResponse,
    HomeworkUpsertRequest,
    HomeworkResponse,
)
from src.services.courses_scv import CoursesService, get_courses_service
from src.services.modules_scv import ModulesService, get_modules_service
from src.services.lessons_scv import LessonsService, get_lessons_service
from src.services.materials_scv import MaterialsService, get_materials_service
from src.services.homework_scv import HomeworkService, get_homework_service
from src.security.dependencies import get_current_teacher_or_admin

router = APIRouter(tags=["Courses"])

# ---------- Courses ----------

@router.get("/courses", response_model=CourseListResponse)
async def list_courses(
    category_id: int | None = Query(None),
    type: str | None = Query(None),
    teacher_id: int | None = Query(None),
    search: str | None = Query(None),
    active_only: bool = Query(True),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: CoursesService = Depends(get_courses_service),
):
    items, total = await service.list_courses(category_id, type, teacher_id, search, active_only, page, page_size)
    return CourseListResponse(
        items=[CourseListItemResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
    )

@router.post("/courses", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
async def create_course(
    data: CourseCreateRequest,
    current_user: User = Depends(get_current_teacher_or_admin),
    service: CoursesService = Depends(get_courses_service),
):
    return await service.create_course(data, current_user)

@router.get("/courses/{id}", response_model=CourseResponse)
async def get_course(id: int, service: CoursesService = Depends(get_courses_service)):
    return await service.get_course(id)

@router.put("/courses/{id}", response_model=CourseResponse)
async def update_course(
    id: int,
    data: CourseUpdateRequest,
    current_user: User = Depends(get_current_teacher_or_admin),
    service: CoursesService = Depends(get_courses_service),
):
    return await service.update_course(id, data, current_user)

@router.put("/courses/{id}/media", response_model=CourseResponse)
async def update_course_media(
    id: int,
    preview_image: UploadFile | None = File(None),
    preview_video: UploadFile | None = File(None),
    current_user: User = Depends(get_current_teacher_or_admin),
    service: CoursesService = Depends(get_courses_service),
):
    return await service.update_media(id, current_user, preview_image, preview_video)

@router.delete("/courses/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(
    id: int,
    current_user: User = Depends(get_current_teacher_or_admin),
    service: CoursesService = Depends(get_courses_service),
):
    await service.delete_course(id, current_user)

# ---------- Modules ----------

@router.post("/courses/{course_id}/modules", response_model=ModuleResponse, status_code=status.HTTP_201_CREATED)
async def create_module(
    course_id: int,
    data: ModuleCreateRequest,
    current_user: User = Depends(get_current_teacher_or_admin),
    service: ModulesService = Depends(get_modules_service),
):
    return await service.create_module(course_id, data, current_user)

@router.put("/modules/{module_id}", response_model=ModuleResponse)
async def update_module(
    module_id: int,
    data: ModuleUpdateRequest,
    current_user: User = Depends(get_current_teacher_or_admin),
    service: ModulesService = Depends(get_modules_service),
):
    return await service.update_module(module_id, data, current_user)

@router.delete("/modules/{module_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_module(
    module_id: int,
    current_user: User = Depends(get_current_teacher_or_admin),
    service: ModulesService = Depends(get_modules_service),
):
    await service.delete_module(module_id, current_user)

# ---------- Lessons ----------

@router.post("/modules/{module_id}/lessons", response_model=LessonResponse, status_code=status.HTTP_201_CREATED)
async def create_lesson(
    module_id: int,
    data: LessonCreateRequest,
    current_user: User = Depends(get_current_teacher_or_admin),
    service: LessonsService = Depends(get_lessons_service),
):
    return await service.create_lesson(module_id, data, current_user)

@router.put("/lessons/{lesson_id}", response_model=LessonResponse)
async def update_lesson(
    lesson_id: int,
    data: LessonUpdateRequest,
    current_user: User = Depends(get_current_teacher_or_admin),
    service: LessonsService = Depends(get_lessons_service),
):
    return await service.update_lesson(lesson_id, data, current_user)

@router.put("/lessons/{lesson_id}/video", response_model=LessonResponse)
async def update_lesson_video(
    lesson_id: int,
    video: UploadFile = File(...),
    current_user: User = Depends(get_current_teacher_or_admin),
    service: LessonsService = Depends(get_lessons_service),
):
    return await service.update_video(lesson_id, video, current_user)

@router.delete("/lessons/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lesson(
    lesson_id: int,
    current_user: User = Depends(get_current_teacher_or_admin),
    service: LessonsService = Depends(get_lessons_service),
):
    await service.delete_lesson(lesson_id, current_user)

# ---------- Materials ----------

@router.post("/lessons/{lesson_id}/materials", response_model=MaterialResponse, status_code=status.HTTP_201_CREATED)
async def create_material(
    lesson_id: int,
    name: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_teacher_or_admin),
    service: MaterialsService = Depends(get_materials_service),
):
    return await service.create_material(lesson_id, name, file, current_user)

@router.delete("/materials/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_material(
    material_id: int,
    current_user: User = Depends(get_current_teacher_or_admin),
    service: MaterialsService = Depends(get_materials_service),
):
    await service.delete_material(material_id, current_user)

# ---------- Homework ----------

@router.get("/lessons/{lesson_id}/homework", response_model=HomeworkResponse | None)
async def get_homework(
    lesson_id: int,
    service: HomeworkService = Depends(get_homework_service),
):
    return await service.get_homework(lesson_id)

@router.put("/lessons/{lesson_id}/homework", response_model=HomeworkResponse | None)
async def upsert_homework(
    lesson_id: int,
    data: HomeworkUpsertRequest,
    current_user: User = Depends(get_current_teacher_or_admin),
    service: HomeworkService = Depends(get_homework_service),
):
    return await service.upsert_homework(lesson_id, data, current_user)

@router.put("/lessons/{lesson_id}/homework/example-file", response_model=HomeworkResponse)
async def upload_homework_example_file(
    lesson_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_teacher_or_admin),
    service: HomeworkService = Depends(get_homework_service),
):
    return await service.upload_example_file(lesson_id, file, current_user)

@router.delete("/lessons/{lesson_id}/homework", status_code=status.HTTP_204_NO_CONTENT)
async def delete_homework(
    lesson_id: int,
    current_user: User = Depends(get_current_teacher_or_admin),
    service: HomeworkService = Depends(get_homework_service),
):
    await service.delete_homework(lesson_id, current_user)
