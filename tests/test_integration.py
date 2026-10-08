"""Run only against an explicit disposable TEST_DATABASE_URL ending in _test."""

import asyncio
import os
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from alembic import command
from src.infrastructure import database
from src.main import app
from src.models.password_reset import PasswordResetCode
from src.security import rate_limits
from src.services.password_reset_service import code_digest

URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL is not set"),
]


@pytest.fixture(scope="module", autouse=True)
def migrated_database():
    if not URL:
        return
    from sqlalchemy.engine import make_url

    assert make_url(URL).database.endswith("_test"), (
        "Integration tests require a disposable _test database"
    )
    command.upgrade(Config("alembic.ini"), "head")


@pytest_asyncio.fixture
async def db_factory(monkeypatch):
    engine = create_async_engine(URL, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with factory() as db:
        await db.execute(
            text(
                "TRUNCATE users, categories, password_reset_codes, auth_rate_limits, media_cleanup_queue CASCADE"
            )
        )
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
    login = await client.post(
        "/api/v1/seller/login", json={k: data[k] for k in ["phone", "password"]}
    )
    assert login.status_code == 200, login.text
    return login.json(), data


async def create_course(client, db_factory, tokens):
    from src.models.category import Category

    async with db_factory() as db:
        category = Category(
            name={"uz": "Fan", "ru": "Предмет", "en": "Subject"},
            path="/subject",
            level=1,
            is_active=True,
        )
        db.add(category)
        await db.commit()
        category_id = category.id
    headers = {"Authorization": "Bearer " + tokens["access_token"]}
    course = await client.post(
        "/api/v1/courses",
        headers=headers,
        json={"name": "Course", "category_id": category_id, "type": "foundation"},
    )
    assert course.status_code == 201, course.text
    module = await client.post(
        f"/api/v1/courses/{course.json()['id']}/modules", headers=headers, json={"name": "Module"}
    )
    assert module.status_code == 201, module.text
    lesson = await client.post(
        f"/api/v1/modules/{module.json()['id']}/lessons", headers=headers, json={"name": "Lesson"}
    )
    assert lesson.status_code == 201, lesson.text
    return course.json()["id"], lesson.json()["id"], headers


async def test_session_rotation_password_change_and_logout(client):
    login, _ = await create_teacher(client)
    pair = login["tokens"]
    rotated = await client.post("/api/v1/refresh", json={"refresh_token": pair["refresh_token"]})
    assert rotated.status_code == 200, rotated.text
    assert (
        await client.post("/api/v1/refresh", json={"refresh_token": pair["refresh_token"]})
    ).status_code == 401
    headers = {"Authorization": "Bearer " + rotated.json()["access_token"]}
    changed = await client.put(
        "/api/v1/password",
        headers=headers,
        json={"old_password": "long-password-123", "new_password": "new-long-password-123"},
    )
    assert changed.status_code == 200, changed.text
    assert (await client.get("/api/v1/me", headers=headers)).status_code == 401
    assert (
        await client.post(
            "/api/v1/refresh", json={"refresh_token": rotated.json()["refresh_token"]}
        )
    ).status_code == 401
    relogin = await client.post(
        "/api/v1/seller/login", json={"phone": "998901234567", "password": "new-long-password-123"}
    )
    headers = {"Authorization": "Bearer " + relogin.json()["tokens"]["access_token"]}
    assert (await client.post("/api/v1/logout", headers=headers)).status_code == 204
    assert (await client.get("/api/v1/me", headers=headers)).status_code == 401


async def test_invalid_homework_replacement_preserves_saved_assignment(client, db_factory):
    login, _ = await create_teacher(client)
    _, lesson_id, headers = await create_course(client, db_factory, login["tokens"])
    valid = {
        "type": "test",
        "pass_ball": 1,
        "questions": [
            {
                "text": "Question",
                "ball": 1,
                "options": [
                    {"text": "Answer", "is_correct": True},
                    {"text": "Wrong", "is_correct": False},
                ],
            }
        ],
    }
    path = f"/api/v1/lessons/{lesson_id}/homework"
    saved = await client.put(path, headers=headers, json=valid)
    assert saved.status_code == 200, saved.text
    assert (await client.put(path, headers=headers, json={"type": "test"})).status_code in (
        400,
        422,
    )
    current = await client.get(path, headers=headers)
    assert current.status_code == 200, current.text
    assert current.json()["id"] == saved.json()["id"]
    replacement = {**valid, "name": "Replacement"}
    assert (await client.put(path, headers=headers, json=replacement)).status_code == 200
    assert (await client.get(path)).status_code == 401


async def test_reset_attempts_commit_and_token_consumes_once(client, db_factory):
    login, data = await create_teacher(client)
    async with db_factory() as db:
        db.add(
            PasswordResetCode(
                phone=data["phone"],
                code=code_digest(data["phone"], "123456"),
                attempts=0,
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
                verified=False,
            )
        )
        await db.commit()
    verify = "/api/v1/forgot-password/verify-code"
    assert (
        await client.post(verify, json={"phone": data["phone"], "code": "999999"})
    ).status_code == 400
    async with db_factory() as db:
        row = (await db.execute(select(PasswordResetCode))).scalar_one()
        assert row.attempts == 1
        assert row.code != "123456"
    verified = await client.post(verify, json={"phone": data["phone"], "code": "123456"})
    assert verified.status_code == 200, verified.text
    payload = {
        "phone": data["phone"],
        "token": verified.json()["token"],
        "new_password": "replacement-password",
    }
    responses = await asyncio.gather(
        *[client.post("/api/v1/forgot-password/new-password", json=payload) for _ in range(2)]
    )
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


async def test_category_reparenting_and_active_child_visibility(db_factory):
    from fastapi import HTTPException

    from src.models.category import Category
    from src.repositories.categories_repo import CategoriesRepository
    from src.schemas.category_schemas import CategoryUpdateRequest
    from src.services.categories_service import CategoriesService

    async with db_factory() as db:
        parent = Category(name={"uz": "Parent"}, path="/parent", level=1, is_active=True)
        other = Category(name={"uz": "Other"}, path="/other", level=1, is_active=True)
        db.add_all([parent, other])
        await db.flush()
        child = Category(
            name={"uz": "Hidden"}, path="/hidden", parent_id=parent.id, level=2, is_active=False
        )
        db.add(child)
        await db.commit()
        parent_id, other_id = parent.id, other.id
    async with db_factory() as db:
        repo = CategoriesRepository(db)
        roots = await repo.list_categories(True)
        assert next(root for root in roots if root.id == parent_id).subcategories == []
    async with db_factory() as db:
        service = CategoriesService(CategoriesRepository(db))
        with pytest.raises(HTTPException) as exc:
            await service.update_category(parent_id, CategoryUpdateRequest(parent_id=other_id))
        assert exc.value.status_code == 400
        await db.rollback()


async def test_public_catalog_hides_drafts_and_media_requires_ownership(
    client, db_factory, tmp_path, monkeypatch
):
    from src.infrastructure.config import settings

    monkeypatch.setattr(settings, "MEDIA_ROOT", str(tmp_path))
    login, _ = await create_teacher(client)
    course_id, lesson_id, headers = await create_course(client, db_factory, login["tokens"])
    assert (await client.get(f"/api/v1/courses/{course_id}")).status_code == 404
    assert (await client.get("/api/v1/courses?active_only=false")).json()["total"] == 0
    video = await client.put(
        f"/api/v1/lessons/{lesson_id}/video",
        headers=headers,
        files={"video": ("lesson.mp4", b"test-video", "video/mp4")},
    )
    assert video.status_code == 200, video.text
    media_url = "/media/" + video.json()["video"]
    assert (await client.get(media_url)).status_code == 401
    assert (await client.get(media_url, headers=headers)).content == b"test-video"
    published = await client.put(
        f"/api/v1/courses/{course_id}", headers=headers, json={"is_active": True}
    )
    assert published.status_code == 200, published.text
    public = await client.get(f"/api/v1/courses/{course_id}")
    assert public.status_code == 200, public.text
    assert "video" not in public.json()["modules"][0]["lessons"][0]
    assert (await client.delete(f"/api/v1/courses/{course_id}", headers=headers)).status_code == 204
    assert not list(tmp_path.rglob("*.mp4"))


async def test_permission_lookup_uses_one_query(client, db_factory):
    from sqlalchemy import event

    from src.repositories.courses_repo import CoursesRepository

    login, _ = await create_teacher(client)
    course_id, _, _ = await create_course(client, db_factory, login["tokens"])
    queries = []
    engine = db_factory.kw["bind"]

    def record(conn, cursor, statement, parameters, context, executemany):
        queries.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", record)
    try:
        async with db_factory() as db:
            repo = CoursesRepository(db)
            assert (await repo.get_reference(course_id)).id == course_id
            assert len(queries) == 1
            queries.clear()
            assert (await repo.get_by_id(course_id)).id == course_id
            assert len(queries) > 1
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", record)


async def test_failed_file_cleanup_is_persisted_and_retryable(
    client, db_factory, tmp_path, monkeypatch
):
    from src.infrastructure.config import settings
    from src.models.media_cleanup import MediaCleanup
    from src.services import file_storage

    monkeypatch.setattr(settings, "MEDIA_ROOT", str(tmp_path))
    login, _ = await create_teacher(client)
    course_id, lesson_id, headers = await create_course(client, db_factory, login["tokens"])
    upload = await client.put(
        f"/api/v1/lessons/{lesson_id}/video",
        headers=headers,
        files={"video": ("lesson.mp4", b"video", "video/mp4")},
    )
    path = upload.json()["video"]
    original = file_storage.delete_media_file

    def fail_delete(path):
        raise OSError("temporary failure")

    monkeypatch.setattr(file_storage, "delete_media_file", fail_delete)
    assert (await client.delete(f"/api/v1/courses/{course_id}", headers=headers)).status_code == 204
    async with db_factory() as db:
        assert (await db.execute(select(MediaCleanup.path))).scalar_one() == path
    monkeypatch.setattr(file_storage, "delete_media_file", original)
    async with db_factory() as db:
        await file_storage.cleanup_pending_files(db)
        assert not (await db.execute(select(MediaCleanup.path))).first()
    assert not file_storage.media_path(path).exists()


def test_migration_metadata_has_no_pending_changes():
    command.check(Config("alembic.ini"))
