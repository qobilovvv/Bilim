import logging
import uuid
import warnings
from pathlib import Path

import aiofiles
from anyio import to_thread
from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert

from src.infrastructure.config import settings
from src.models.media_cleanup import MediaCleanup

logger = logging.getLogger(__name__)
CHUNK_SIZE = 1024 * 1024
IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}


def media_path(relative_path: str) -> Path:
    root = Path(settings.MEDIA_ROOT).resolve()
    path = (root / relative_path).resolve()
    if path == root or not path.is_relative_to(root):
        raise HTTPException(400, "Invalid media path")
    return path


def _reencode_image(path: Path) -> None:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(path) as image:
                if (
                    image.format not in {"JPEG", "PNG", "WEBP"}
                    or image.width * image.height > 20_000_000
                ):
                    raise ValueError("Unsupported or oversized image")
                image.load()
                image.convert("RGB").save(path, format="WEBP", quality=85)
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as exc:
        raise HTTPException(400, "Invalid image content") from exc


async def save_upload_file(
    upload: UploadFile,
    subdir: str,
    allowed_extensions: set[str] | None = None,
    max_size_bytes: int | None = None,
) -> str:
    ext = Path(upload.filename or "").suffix.lstrip(".").lower()
    if allowed_extensions is not None and ext not in allowed_extensions:
        raise HTTPException(400, "Invalid file type")
    image = allowed_extensions == IMAGE_EXTENSIONS
    filename = f"{uuid.uuid4().hex}.{('webp' if image else ext)}" if ext else uuid.uuid4().hex
    relative_path = f"{subdir}/{filename}"
    path = media_path(relative_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    size = 0
    try:
        async with aiofiles.open(path, "xb") as output:
            while chunk := await upload.read(CHUNK_SIZE):
                size += len(chunk)
                if max_size_bytes is not None and size > max_size_bytes:
                    raise HTTPException(413, "File too large")
                await output.write(chunk)
        if size == 0:
            raise HTTPException(400, "Empty file")
        if image:
            await to_thread.run_sync(_reencode_image, path)
    except BaseException:
        await to_thread.run_sync(path.unlink, True)
        raise
    return relative_path


def delete_media_file(relative_path: str | None) -> None:
    if relative_path:
        media_path(relative_path).unlink(missing_ok=True)


async def queue_media_cleanup(db, paths) -> None:
    for path in set(filter(None, paths)):
        media_path(path)
        await db.execute(insert(MediaCleanup).values(path=path).on_conflict_do_nothing())
        db.info.setdefault("media_cleanup", set()).add(path)


async def stage_upload(db, upload, subdir, allowed_extensions, max_size_bytes, old_path=None):
    path = await save_upload_file(upload, subdir, allowed_extensions, max_size_bytes)
    db.info.setdefault("new_media", []).append(path)
    if old_path:
        await queue_media_cleanup(db, [old_path])
    return path


async def cleanup_pending_files(db, paths=None, limit=100):
    query = (
        select(MediaCleanup)
        .order_by(MediaCleanup.created_at)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    if paths is not None:
        query = query.where(MediaCleanup.path.in_(paths))
    entries = (await db.execute(query)).scalars().all()
    for entry in entries:
        try:
            await to_thread.run_sync(delete_media_file, entry.path)
        except Exception:
            logger.exception("Media cleanup failed; retained for retry")
        else:
            await db.execute(delete(MediaCleanup).where(MediaCleanup.path == entry.path))
    await db.commit()


def lesson_media_paths(lesson):
    paths = [lesson.video, *(material.file for material in lesson.materials)]
    if lesson.homework and lesson.homework.file_detail:
        paths.append(lesson.homework.file_detail.example_file)
    return paths


def module_media_paths(module):
    return [path for lesson in module.lessons for path in lesson_media_paths(lesson)]


def course_media_paths(course):
    return [
        course.preview_image,
        course.preview_video,
        *(path for module in course.modules for path in module_media_paths(module)),
    ]
