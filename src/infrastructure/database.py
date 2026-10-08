import logging
from typing import AsyncGenerator

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from src.infrastructure.config import settings

# 1. Create the Async Engine
# The engine is the core interface to the database.
# Optimized for production with connection pooling
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # Set to True to log all SQL queries during development
    future=True,
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_SIZE,  # Number of connections to keep in the pool
    max_overflow=settings.DB_MAX_OVERFLOW,  # Additional connections beyond pool_size
    pool_recycle=3600,  # Recycle connections after 1 hour
    connect_args={"timeout": 10, "command_timeout": 30},  # Connection timeout
)

# 2. Create the Async Session Maker
# expire_on_commit=False is strictly required for async SQLAlchemy.
# It prevents SQLAlchemy from trying to lazily load attributes synchronously after a commit.
AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    expire_on_commit=False,
)

# 3. Define the Base Class for Models
# All your domain models (e.g., in src/domain/models.py) will inherit from this.
Base = declarative_base()


# 4. Dependency Injection Provider
# This generator yields a database session for each request and ensures
# it is safely closed afterward, even if an exception occurs.
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency to inject an asynchronous database session.
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except IntegrityError as exc:
            session.info["transaction_failed"] = True
            await session.rollback()
            raise HTTPException(
                status_code=409, detail="The change conflicts with an existing record or reference"
            ) from exc
        except BaseException:
            session.info["transaction_failed"] = True
            await session.rollback()
            raise
        finally:
            from anyio import to_thread

            from src.services.file_storage import cleanup_pending_files, delete_media_file

            # A committed file reference must never be removed by rollback cleanup.
            if session.in_transaction():
                await session.rollback()
            if session.info.pop("transaction_failed", False):
                for path in session.info.get("new_media", []):
                    try:
                        await to_thread.run_sync(delete_media_file, path)
                    except Exception:
                        logging.getLogger(__name__).exception("Rollback media cleanup failed")
            elif session.info.get("media_cleanup"):
                try:
                    await cleanup_pending_files(session, session.info["media_cleanup"])
                except Exception:
                    await session.rollback()
                    logging.getLogger(__name__).exception(
                        "Deferred media cleanup retained for retry"
                    )
