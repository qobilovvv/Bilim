from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db_session
from src.models.course import Course
from src.models.homework import FileHomework, Homework
from src.models.lesson import Lesson
from src.models.material import Material
from src.models.module import Module
from src.models.user import User, UserType
from src.security.dependencies import get_current_user
from src.services.file_storage import media_path

router = APIRouter(tags=["Media"])
optional_bearer = HTTPBearer(auto_error=False)


async def optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_bearer),
    db: AsyncSession = Depends(get_db_session, scope="function"),
):
    if credentials is None:
        return None
    return await get_current_user(credentials, db)


@router.get("/media/{relative_path:path}")
async def get_media(
    relative_path: str,
    user: User | None = Depends(optional_user),
    db: AsyncSession = Depends(get_db_session, scope="function"),
):
    path = media_path(relative_path)
    public = False
    ext = path.suffix.lower()
    if relative_path.startswith("avatars/") and ext in {".jpg", ".jpeg", ".png", ".webp"}:
        public = bool((await db.execute(select(User.id).where(User.avatar == relative_path))).first())
    if relative_path.startswith("courses/previews/") and ext in {
        ".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".webm", ".mkv"
    }:
        public = bool((await db.execute(select(Course.id).where(
            (Course.preview_image == relative_path) | (Course.preview_video == relative_path),
            Course.is_active.is_(True),
        ))).first())
    if not public:
        if user is None:
            raise HTTPException(401, "Authentication required", headers={"WWW-Authenticate": "Bearer"})
        queries = [
            select(Course.teacher_id).where((Course.preview_image == relative_path) | (Course.preview_video == relative_path)),
            select(Course.teacher_id).join(Module).join(Lesson).where(Lesson.video == relative_path),
            select(Course.teacher_id).join(Module).join(Lesson).join(Material).where(Material.file == relative_path),
            select(Course.teacher_id).join(Module).join(Lesson).join(Homework).join(FileHomework)
            .where(FileHomework.example_file == relative_path),
        ]
        owners = set()
        for query in queries:
            owners.update((await db.execute(query)).scalars())
        if not owners or (user.type != UserType.ADMIN and user.id not in owners):
            raise HTTPException(404, "File not found")
    if not path.is_file():
        raise HTTPException(404, "File not found")
    attachment = relative_path.startswith(("lessons/materials/", "homeworks/examples/"))
    return FileResponse(path, filename=Path(relative_path).name if attachment else None,
                        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"})
