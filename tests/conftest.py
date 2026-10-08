import os

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://test:test@localhost/bilim_test"
)
os.environ["JWT_SECRET_KEY"] = "test-only-0123456789abcdef0123456789abcdef"
