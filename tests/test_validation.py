import pytest
from pydantic import TypeAdapter, ValidationError

from src.schemas.auth_schemas import ProfileUpdateRequest, UserRegisterRequest
from src.schemas.course_schemas import CourseCreateRequest, CourseUpdateRequest, HomeworkUpsertRequest


@pytest.mark.parametrize("updates", [{"first_name": " "}, {"phone": "abc"}, {"password": "short"}])
def test_registration_rejects_invalid_identity(updates):
    payload = {"first_name": "User", "phone": "998901234567", "password": "long-password-123", **updates}
    with pytest.raises(ValidationError):
        UserRegisterRequest(**payload)


def test_phone_normalization_is_consistent():
    user = UserRegisterRequest(first_name=" User ", phone="+998 (90) 123-45-67", password="long-password-123")
    assert user.phone == "998901234567"
    assert user.first_name == "User"


@pytest.mark.parametrize("updates", [{"price": -1}, {"name": " "}, {"type": "invalid"}, {"category_id": 0}])
def test_courses_reject_invalid_domain_values(updates):
    with pytest.raises(ValidationError):
        CourseCreateRequest(**{"name": "Course", "category_id": 1, "type": "foundation", **updates})


def test_nullable_patch_fields_can_be_cleared_but_required_fields_cannot():
    assert ProfileUpdateRequest(email=None).model_dump(exclude_unset=True) == {"email": None}
    assert CourseUpdateRequest(about_teacher=None).model_dump(exclude_unset=True) == {"about_teacher": None}
    with pytest.raises(ValidationError):
        CourseUpdateRequest(name=None)


@pytest.mark.parametrize("payload", [
    {"type": "test", "pass_ball": 1, "questions": []},
    {"type": "test", "pass_ball": 3, "questions": [{"text": "Q", "ball": 1,
        "options": [{"text": "A", "is_correct": True}, {"text": "B"}]}]},
    {"type": "text", "deadline_days": 1, "min_words": 10, "pass_ball": 50},
    {"type": "file", "deadline_days": 3, "file_formats": ["../html"], "max_file_size_mb": 10},
    {"type": "none", "questions": []},
])
def test_homework_variants_enforce_their_own_contract(payload):
    with pytest.raises(ValidationError):
        TypeAdapter(HomeworkUpsertRequest).validate_python(payload)
