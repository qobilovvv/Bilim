from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException, UploadFile
from PIL import Image

from src.infrastructure.config import settings
from src.services import file_storage
from src.services.lessons_scv import LessonsService


@pytest.fixture(autouse=True)
def media_root(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "MEDIA_ROOT", str(tmp_path))
    return tmp_path


async def test_oversized_stream_is_removed(media_root):
    upload = SimpleNamespace(filename="large.mp4", read=AsyncMock(side_effect=[b"abc", b"def", b""]))
    with pytest.raises(HTTPException) as exc:
        await file_storage.save_upload_file(upload, "lessons/videos", {"mp4"}, 4)
    assert exc.value.status_code == 413
    assert list(media_root.rglob("*.mp4")) == []
    assert all(call.args == (file_storage.CHUNK_SIZE,) for call in upload.read.call_args_list)


async def test_claimed_image_with_html_content_is_rejected(media_root):
    upload = UploadFile(filename="fake.png", file=BytesIO(b"<script>alert(1)</script>"))
    with pytest.raises(HTTPException):
        await file_storage.save_upload_file(upload, "avatars", file_storage.IMAGE_EXTENSIONS, 500)
    assert list(media_root.rglob("*.webp")) == []


async def test_images_are_reencoded_without_client_extension(media_root):
    buffer = BytesIO()
    Image.new("RGB", (2, 2)).save(buffer, "PNG")
    buffer.seek(0)
    path = await file_storage.save_upload_file(UploadFile(filename="picture.png", file=buffer),
                                              "avatars", file_storage.IMAGE_EXTENSIONS, 1000)
    assert path.endswith(".webp")
    with Image.open(file_storage.media_path(path)) as image:
        assert image.format == "WEBP"


async def test_invalid_replacement_keeps_old_video(media_root):
    old = file_storage.media_path("lessons/videos/old.mp4")
    old.parent.mkdir(parents=True)
    old.write_bytes(b"old")
    lesson = SimpleNamespace(video="lessons/videos/old.mp4")
    repo = SimpleNamespace(db=SimpleNamespace(info={}))
    service = LessonsService(repo, None)
    service._get_owned_lesson = AsyncMock(return_value=lesson)
    with pytest.raises(HTTPException):
        await service.update_video(1, UploadFile(filename="bad.html", file=BytesIO(b"bad")), None)
    assert old.read_bytes() == b"old"
    assert lesson.video == "lessons/videos/old.mp4"


@pytest.mark.parametrize("path", ["../outside", "/etc/passwd", "../../file"])
def test_path_escape_is_rejected(path):
    with pytest.raises(HTTPException):
        file_storage.media_path(path)
