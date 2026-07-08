from pydantic import BaseModel, ConfigDict
from datetime import datetime

# ---------- Brief nested references ----------

class TeacherBrief(BaseModel):
    id: int
    first_name: str
    last_name: str | None = None
    avatar: str | None = None

    model_config = ConfigDict(from_attributes=True)

class CategoryBrief(BaseModel):
    id: int
    path: str

    model_config = ConfigDict(from_attributes=True)

# ---------- Materials ----------

class MaterialResponse(BaseModel):
    id: int
    lesson_id: int
    name: str
    file: str
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

# ---------- Homework ----------

class TestQuestionOptionInput(BaseModel):
    text: str
    is_correct: bool = False

class TestQuestionInput(BaseModel):
    text: str
    ball: int
    options: list[TestQuestionOptionInput]

class TestQuestionOptionResponse(BaseModel):
    id: int
    text: str
    is_correct: bool
    order_index: int

    model_config = ConfigDict(from_attributes=True)

class TestQuestionResponse(BaseModel):
    id: int
    text: str
    ball: int
    order_index: int
    options: list[TestQuestionOptionResponse] = []

    model_config = ConfigDict(from_attributes=True)

class TestHomeworkResponse(BaseModel):
    timer_minutes: int | None = None
    pass_ball: int
    questions: list[TestQuestionResponse] = []

    model_config = ConfigDict(from_attributes=True)

class TextHomeworkResponse(BaseModel):
    deadline_days: int
    pass_ball: int
    min_words: int
    grading_criteria: dict[str, str] | None = None

    model_config = ConfigDict(from_attributes=True)

class FileHomeworkResponse(BaseModel):
    deadline_days: int
    file_formats: list[str]
    max_file_size_mb: int
    example_file: str | None = None

    model_config = ConfigDict(from_attributes=True)

class HomeworkUpsertRequest(BaseModel):
    type: str  # "test" | "text" | "file" | "none"
    name: str | None = None
    description: str | None = None

    # test fields
    timer_minutes: int | None = None
    pass_ball: int | None = None
    questions: list[TestQuestionInput] | None = None

    # text fields
    deadline_days: int | None = None
    min_words: int | None = None
    grading_criteria: dict[str, str] | None = None

    # file fields
    file_formats: list[str] | None = None
    max_file_size_mb: int | None = None

class HomeworkResponse(BaseModel):
    id: int
    lesson_id: int
    type: str
    name: str | None = None
    description: str | None = None
    test_detail: TestHomeworkResponse | None = None
    text_detail: TextHomeworkResponse | None = None
    file_detail: FileHomeworkResponse | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

# ---------- Lessons ----------

class LessonCreateRequest(BaseModel):
    name: str
    description: str | None = None
    order_index: int = 0

class LessonUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    order_index: int | None = None

class LessonResponse(BaseModel):
    id: int
    module_id: int
    name: str
    description: str | None = None
    video: str | None = None
    order_index: int
    materials: list[MaterialResponse] = []
    homework: HomeworkResponse | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

# ---------- Modules ----------

class ModuleCreateRequest(BaseModel):
    name: str
    description: str | None = None
    order_index: int = 0

class ModuleUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    order_index: int | None = None

class ModuleResponse(BaseModel):
    id: int
    course_id: int
    name: str
    description: str | None = None
    order_index: int
    lessons: list[LessonResponse] = []
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

# ---------- Courses ----------

class CourseCreateRequest(BaseModel):
    name: str
    category_id: int
    price: int = 0
    type: str
    about_teacher: str | None = None

class CourseUpdateRequest(BaseModel):
    name: str | None = None
    category_id: int | None = None
    teacher_id: int | None = None
    price: int | None = None
    type: str | None = None
    about_teacher: str | None = None
    is_active: bool | None = None

class CourseListItemResponse(BaseModel):
    id: int
    name: str
    category: CategoryBrief
    teacher: TeacherBrief
    price: int
    type: str
    preview_image: str | None = None
    is_active: bool
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

class CourseListResponse(BaseModel):
    items: list[CourseListItemResponse]
    total: int
    page: int
    page_size: int

class CourseResponse(BaseModel):
    id: int
    name: str
    category: CategoryBrief
    teacher: TeacherBrief
    price: int
    type: str
    preview_image: str | None = None
    preview_video: str | None = None
    about_teacher: str | None = None
    is_active: bool
    modules: list[ModuleResponse] = []
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
