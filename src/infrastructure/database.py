from typing import AsyncGenerator
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
    pool_size=20,  # Number of connections to keep in the pool
    max_overflow=10,  # Additional connections beyond pool_size
    pool_recycle=3600,  # Recycle connections after 1 hour
    connect_args={"timeout": 10}  # Connection timeout
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
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()