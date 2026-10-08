from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import Depends, FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError

from src.infrastructure import database
from src.schemas.course_schemas import HomeworkUpsertRequest
from src.services.homework_scv import HomeworkService


async def test_invalid_replacement_preserves_homework():
    repo = SimpleNamespace(get_by_lesson_id=AsyncMock(), delete_homework=AsyncMock())
    service = HomeworkService(repo, None)
    service._get_owned_lesson = AsyncMock()
    with pytest.raises(HTTPException):
        await service.upsert_homework(1, HomeworkUpsertRequest(type="test"), None)
    repo.delete_homework.assert_not_awaited()


async def test_commit_failure_is_returned_before_success(monkeypatch):
    session = AsyncMock()
    session.commit.side_effect = IntegrityError("insert", {}, Exception("duplicate"))
    factory = AsyncMock()
    factory.__aenter__.return_value = session
    monkeypatch.setattr(database, "AsyncSessionFactory", lambda: factory)
    app = FastAPI()

    @app.post("/write")
    async def write(db=Depends(database.get_db_session, scope="function")):
        return {"ok": True}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/write")
    assert response.status_code == 409
    session.rollback.assert_awaited_once()


async def test_failed_request_rolls_back_without_commit(monkeypatch):
    session = AsyncMock()
    factory = AsyncMock()
    factory.__aenter__.return_value = session
    monkeypatch.setattr(database, "AsyncSessionFactory", lambda: factory)
    app = FastAPI()

    @app.post("/write")
    async def write(db=Depends(database.get_db_session, scope="function")):
        raise HTTPException(400, "invalid")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.post("/write")).status_code == 400
    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()
