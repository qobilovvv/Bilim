from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.schemas.course_schemas import CourseCatalogResponse
from src.services.courses_scv import CoursesService
from src.services.homework_scv import HomeworkService


async def test_answer_keys_require_authentication():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/lessons/1/homework")
        assert response.status_code == 401
        response = await client.get("/api/v1/courses/1/content")
        assert response.status_code == 401


async def test_course_content_requires_ownership():
    course = SimpleNamespace(teacher_id=1)
    service = CoursesService(SimpleNamespace(get_by_id=AsyncMock(return_value=course)), None, None)
    with pytest.raises(HTTPException) as exc:
        await service.get_owned_course(1, SimpleNamespace(id=2, type="seller"))
    assert exc.value.status_code == 403


async def test_homework_read_requires_ownership():
    service = HomeworkService(None, SimpleNamespace(get_by_id=AsyncMock(return_value=SimpleNamespace(
        module=SimpleNamespace(course=SimpleNamespace(teacher_id=1))))))
    with pytest.raises(HTTPException) as exc:
        await service.get_homework(1, SimpleNamespace(id=2, type="seller"))
    assert exc.value.status_code == 403


def test_catalog_schema_contains_no_learning_files_or_answers():
    course = SimpleNamespace(id=1, name="Course", category=SimpleNamespace(id=1, path="/cat"),
        teacher=SimpleNamespace(id=1, first_name="Teacher"), price=0, type="foundation", is_active=True,
        modules=[SimpleNamespace(id=1, name="Module", order_index=0, lessons=[SimpleNamespace(
            id=1, name="Lesson", order_index=0, video="secret.mp4", homework={"answer": True})])])
    result = CourseCatalogResponse.model_validate(course).model_dump()
    lesson = result["modules"][0]["lessons"][0]
    assert set(lesson) == {"id", "name", "order_index"}
