"""Inventory old unreferenced media; --queue schedules deletion by cleanup_media.

Run during a maintenance window with uploads paused when using --queue.
"""

import argparse
import asyncio
import time
from pathlib import Path

from sqlalchemy import select

from src.infrastructure.config import settings
from src.infrastructure.database import AsyncSessionFactory, engine
from src.models.course import Course
from src.models.homework import FileHomework
from src.models.lesson import Lesson
from src.models.material import Material
from src.models.user import User
from src.services.file_storage import queue_media_cleanup


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", action="store_true")
    parser.add_argument("--age-hours", type=int, default=24)
    args = parser.parse_args()
    if args.age_hours < 24:
        parser.error("Use a grace period of at least 24 hours")
    try:
        async with AsyncSessionFactory() as db:
            referenced = set()
            for column in (
                User.avatar,
                Course.preview_image,
                Course.preview_video,
                Lesson.video,
                Material.file,
                FileHomework.example_file,
            ):
                referenced.update((await db.execute(select(column))).scalars().all())
            root = Path(settings.MEDIA_ROOT).resolve()
            cutoff = time.time() - args.age_hours * 3600
            candidates = sorted(
                path.relative_to(root).as_posix()
                for path in root.rglob("*")
                if path.is_file()
                and not path.is_symlink()
                and path.stat().st_mtime < cutoff
                and path.relative_to(root).as_posix() not in referenced
            )
            for path in candidates:
                print(path)
            if args.queue:
                await queue_media_cleanup(db, candidates)
                await db.commit()
            print(
                f"{len(candidates)} unreferenced files {'queued' if args.queue else 'found (dry run)'}"
            )
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
