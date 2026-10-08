"""Retry persisted file cleanup: python -m scripts.cleanup_media."""
import asyncio

from src.infrastructure.database import AsyncSessionFactory, engine
from src.services.file_storage import cleanup_pending_files


async def main():
    try:
        async with AsyncSessionFactory() as db:
            await cleanup_pending_files(db)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
