"""Run only against an explicit disposable TEST_DATABASE_URL ending in _test."""
import asyncio
import os
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.infrastructure import database
from src.main import app
from src.models.homework import Homework
from src.models.password_reset import PasswordResetCode
from src.models.user import User
from src.security import rate_limits
from src.security.passwords import hash_password
from src.services.password_reset_scv import code_digest

URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = [pytest.mark.integration, pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL is not set")]


@pytest.fixture(scope="module", autouse=True)
def migrated_database():
    if not URL:
        return
    from sqlalchemy.engine import make_url
    assert make_url(URL).database.endswith("_test"), "Integration tests require a disposable _test database"
    command.upgrade(Config("alembic.ini"), "head")


@pytest_asyncio.fixture
async def db_factory(monkeypatch):
    engine = create_async_engine(URL, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with factory() as db:
        await db.execute(text('TRUNCATE users, categories, password_reset_codes, auth_rate_limits, media_cleanup_queue CASCADE'))
        await db.commit()
    monkeypatch.setattr(database, "AsyncSessionFactory", factory)
    monkeypatch.setattr(rate_limits, "AsyncSessionFactory", factory)
    yield factory
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_factory):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


async def create_teacher(client):
    data = {"phone": "998901234567", "password": "long-password-123", "first_name": "Teacher"}
    response = await client.post("/api/v1/seller/register", json=data)
    assert response.status_code == 201, response.text
    login = await client.post("/api/v1/seller/login", json={k: data[k] for k in ["phone", "password"]})
    assert login.status_code == 200, login.text
    return login.json(), data


async def create_course(client, db_factory, tokens):
    from src.models.category import Category
    async with db_factory() as db:
        category = Category(name={"uz": "Fan", "ru": "Предмет", "en": "Subject"}, path="/subject", level=1, is_active=True)
        db.add(category)
        await db.commit()
        category_id = category.id
    headers = {"Authorization": "Bearer " + tokens["access_token"]}
    course = await client.post("/api/v1/courses", headers=headers,
                              json={"name": "Course", "category_id": category_id, "type": "foundation"})
    assert course.status_code == 201, course.text
    module = await client.post(f'/api/v1/courses/{course.json()["id"]}/modules', headers=headers, json={"name": "Module"})
    assert module.status_code == 201, module.text
    lesson = await client.post(f'/api/v1/modules/{module.json()["id"]}/lessons', headers=headers, json={"name": "Lesson"})
    assert lesson.status_code == 201, lesson.text
    return course.json()["id"], lesson.json()["id"], headers


async def test_session_rotation_password_change_and_logout(client):
    login, _ = await create_teacher(client)
    pair = login["tokens"]
    rotated = await client.post("/api/v1/refresh", json={"refresh_token": pair["refresh_token"]})
    assert rotated.status_code == 200, rotated.text
    assert (await client.post("/api/v1/refresh", json={"refresh_token": pair["refresh_token"]})).status_code == 401
    headers = {"Authorization": "Bearer " + rotated.json()["access_token"]}
    changed = await client.put("/api/v1/password", headers=headers,
        json={"old_password": "long-password-123", "new_password": "new-long-password-123"})
    assert changed.status_code == 200, changed.text
    assert (await client.get("/api/v1/me", headers=headers)).status_code == 401
    assert (await client.post("/api/v1/refresh", json={"refresh_token": rotated.json()["refresh_token"]})).status_code == 401
    relogin = await client.post("/api/v1/seller/login", json={"phone": "998901234567", "password": "new-long-password-123"})
    headers = {"Authorization": "Bearer " + relogin.json()["tokens"]["access_token"]}
    assert (await client.post("/api/v1/logout", headers=headers)).status_code == 204
    assert (await client.get("/api/v1/me", headers=headers)).status_code == 401


async def test_invalid_homework_replacement_preserves_saved_assignment(client, db_factory):
    login, _ = await create_teacher(client)
    _, lesson_id, headers = await create_course(client, db_factory, login["tokens"])
    valid = {"type": "test", "pass_ball": 1, "questions": [{"text": "Question", "ball": 1,
                "options": [{"text": "Answer", "is_correct": True}]}]}
    path = f"/api/v1/lessons/{lesson_id}/homework"
    saved = await client.put(path, headers=headers, json=valid)
    assert saved.status_code == 200, saved.text
    assert (await client.put(path, headers=headers, json={"type": "test"})).status_code in (400, 422)
    current = await client.get(path, headers=headers)
    assert current.status_code == 200, current.text
    assert current.json()["id"] == saved.json()["id"]
    replacement = {**valid, "name": "Replacement"}
    assert (await client.put(path, headers=headers, json=replacement)).status_code == 200
    assert (await client.get(path)).status_code == 401


async def test_reset_attempts_commit_and_token_consumes_once(client, db_factory):
    login, data = await create_teacher(client)
    async with db_factory() as db:
        db.add(PasswordResetCode(phone=data["phone"], code=code_digest(data["phone"], "123456"), attempts=0,
                                expires_at=datetime.now(timezone.utc) + timedelta(minutes=5), verified=False))
        await db.commit()
    verify = "/api/v1/forgot-password/verify-code"
    assert (await client.post(verify, json={"phone": data["phone"], "code": "999999"})).status_code == 400
    async with db_factory() as db:
        row = (await db.execute(select(PasswordResetCode))).scalar_one()
        assert row.attempts == 1
        assert row.code != "123456"
    verified = await client.post(verify, json={"phone": data["phone"], "code": "123456"})
    assert verified.status_code == 200, verified.text
    payload = {"phone": data["phone"], "token": verified.json()["token"], "new_password": "replacement-password"}
    responses = await asyncio.gather(*[client.post("/api/v1/forgot-password/new-password", json=payload) for _ in range(2)])
    assert sorted(response.status_code for response in responses) == [200, 400]
    headers = {"Authorization": "Bearer " + login["tokens"]["access_token"]}
    assert (await client.get("/api/v1/me", headers=headers)).status_code == 401


async def test_rate_limits_persist_rejected_attempts(db_factory):
    for _ in range(2):
        await rate_limits.check_rate_limit("test", "identity", 2, 60)
    from fastapi import HTTPException
    for _ in range(2):
        with pytest.raises(HTTPException) as error:
            await rate_limits.check_rate_limit("test", "identity", 2, 60)
        assert error.value.status_code == 429
