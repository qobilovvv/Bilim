# Bilim backend

See README.md for setup and architecture and documentation/agents.md for development conventions. Python 3.11, FastAPI, async SQLAlchemy/PostgreSQL, Alembic. Services use `*_service.py`; no Redis dependency. Request transactions, database-backed sessions/throttles, ownership-protected media, and deferred file cleanup are required invariants.

Checks: `ruff check src tests scripts alembic`, `ruff format --check src tests scripts alembic`, `mypy`, `pytest -q`. Full integration tests additionally require a disposable `TEST_DATABASE_URL` database ending in `_test`.
