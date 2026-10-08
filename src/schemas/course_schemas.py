from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from src.schemas.validation import RequestModel, PatchModel, Name, LongText, PositiveId
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

class TeacherModerationInfo(BaseModel):
    id: int
    first_name: str
    last_name: str | None = None
    avatar: str | None = None
    phone: str | None = None

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

class TestQuestionOptionInput(RequestModel):
    text: Name
    is_correct: bool = False

class TestQuestionInput(RequestModel):
    text: LongText = Field(min_length=1)
    ball: int = Field(ge=1, le=1000)
    options: list[TestQuestionOptionInput] = Field(min_length=2, max_length=20)

    @model_validator(mode="after")
    def require_correct_option(self):
        if not any(option.is_correct for option in self.options):
            raise ValueError("Each question needs a correct option")
        return self

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

class HomeworkBaseRequest(RequestModel):
    name: Name | None = None
    description: LongText | None = None


class TestHomeworkRequest(HomeworkBaseRequest):
    type: Literal["test"]
    timer_minutes: int | None = Field(default=None, ge=1, le=1440)
    pass_ball: int = Field(ge=1)
    questions: list[TestQuestionInput] = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def attainable_score(self):
        if self.pass_ball > sum(question.ball for question in self.questions):
            raise ValueError("Pass score exceeds the available points")
        return self


class TextHomeworkRequest(HomeworkBaseRequest):
    type: Literal["text"]
    deadline_days: int = Field(ge=2, le=8)
    pass_ball: int = Field(ge=0, le=100)
    min_words: int = Field(ge=1, le=100000)
    grading_criteria: dict[Name, Name] | None = Field(default=None, max_length=50)


class FileHomeworkRequest(HomeworkBaseRequest):
    type: Literal["file"]
    deadline_days: int = Field(ge=2, le=8)
    file_formats: list[Annotated[str, Field(pattern=r"^\.?[a-z0-9]{1,10}$")]] = Field(min_length=1, max_length=20)
    max_file_size_mb: int = Field(ge=1, le=100)


class NoHomeworkRequest(HomeworkBaseRequest):
    type: Literal["none"]


HomeworkUpsertRequest = Annotated[
    TestHomeworkRequest | TextHomeworkRequest | FileHomeworkRequest | NoHomeworkRequest,
    Field(discriminator="type"),
]

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

class LessonCreateRequest(RequestModel):
    name: Name
    description: LongText | None = None
    order_index: int = Field(default=0, ge=0, le=100000)

class LessonUpdateRequest(PatchModel):
    nullable_fields = {"description"}
    name: Name | None = None
    description: LongText | None = None
    order_index: int | None = Field(default=None, ge=0, le=100000)

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

class ModuleCreateRequest(RequestModel):
    name: Name
    description: LongText | None = None
    order_index: int = Field(default=0, ge=0, le=100000)

class ModuleUpdateRequest(PatchModel):
    nullable_fields = {"description"}
    name: Name | None = None
    description: LongText | None = None
    order_index: int | None = Field(default=None, ge=0, le=100000)

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

class CourseCreateRequest(RequestModel):
    name: Name
    category_id: PositiveId
    price: int = Field(default=0, ge=0, le=2147483647)
    type: Literal["foundation", "middle", "senior"]
    about_teacher: LongText | None = None

class CourseUpdateRequest(PatchModel):
    nullable_fields = {"about_teacher"}
    name: Name | None = None
    category_id: PositiveId | None = None
    teacher_id: PositiveId | None = None
    price: int | None = Field(default=None, ge=0, le=2147483647)
    type: Literal["foundation", "middle", "senior"] | None = None
    about_teacher: LongText | None = None
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
    total: int
    limit: int
    offset: int
    result: list[CourseListItemResponse]

class CourseModerationListItemResponse(BaseModel):
    id: int
    name: str
    category: CategoryBrief
    teacher: TeacherModerationInfo
    price: int
    type: str
    preview_image: str | None = None
    is_active: bool
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

class CourseModerationListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    result: list[CourseModerationListItemResponse]

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


class LessonCatalogResponse(BaseModel):
    id: int
    name: str
    order_index: int
    model_config = ConfigDict(from_attributes=True)


class ModuleCatalogResponse(BaseModel):
    id: int
    name: str
    order_index: int
    lessons: list[LessonCatalogResponse] = []
    model_config = ConfigDict(from_attributes=True)


class CourseCatalogResponse(CourseListItemResponse):
    preview_video: str | None = None
    about_teacher: str | None = None
    modules: list[ModuleCatalogResponse] = []
