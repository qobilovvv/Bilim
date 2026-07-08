# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Bilim — an async FastAPI backend for an educational/marketplace platform, backed by PostgreSQL (via SQLAlchemy async + asyncpg) and Alembic migrations. See `documentation/agents.md` for a full architecture reference (layers, models, endpoints, request lifecycle) — read it before making non-trivial changes rather than re-deriving structure from scratch.

## Commands

Run locally (host machine, `.venv` at repo root):
```bash
source .venv/bin/activate
uvicorn src.main:app --reload
```

Run via Docker (dev, includes Postgres + Redis):
```bash
docker compose -f docker/docker-compose.yml up -d --build
```

Migrations (see `documentation/migration.md`):
```bash
alembic upgrade head                                   # apply
alembic revision --autogenerate -m "description"       # generate after model changes
alembic downgrade -1                                    # rollback one

# or inside Docker:
docker compose -f docker/docker-compose.yml run --rm api alembic upgrade head
```

Create an admin user (see `documentation/admin.md`):
```bash
python -m scripts.create_admin --username admin --password secret123 --first-name Admin
# or interactively: python -m scripts.create_admin
```

There is no test suite or lint config in this repo currently — do not assume `pytest`/`ruff`/etc. exist.

## Architecture

Strict one-way layered dependency flow: **API handlers → Services → Repositories → Infrastructure**.

- `src/api/v1/*_handlers.py` — FastAPI routers; only handles HTTP concerns (parsing, status codes, serialization via Pydantic schemas). Registered centrally in `src/api/routes.py`, mounted under `/api/v1` in `src/main.py`.
- `src/services/*_scv.py` — all business logic (validation, uniqueness checks, orchestration). Each has a `get_*_service(db)` factory used as a FastAPI dependency.
- `src/repositories/*_repo.py` — SQLAlchemy queries only, each implementing an ABC from `src/repositories/interfaces.py`. Repositories take an `AsyncSession` via constructor injection.
- `src/infrastructure/` — DB engine/session factory (`database.py`), Pydantic Settings loaded from `.env` (`config.py`), and the Eskiz SMS HTTP client (`eskiz.py`, singleton `eskiz_client`).
- `src/security/` — cross-cutting concerns injected via `Depends()`: Argon2 password hashing (`passwords.py`), JWT access/refresh tokens (`tokens.py`), `get_current_user`/`get_current_admin` dependencies (`dependencies.py`), and `Accept-Language` parsing (`localization.py`).
- `src/models/` — SQLAlchemy models, all registered in `src/models/__init__.py` (which Alembic's `env.py` imports for autogenerate detection).
- `src/domain/` — reserved, currently empty.

Key domain specifics:
- `User.type` distinguishes `admin` (logs in via username), `user`/`seller` (log in via phone). Sellers have a 1:1 `SellerProfile` (cascade delete).
- `Category` is a self-referential tree capped at 2 levels deep; `name` is a JSONB dict keyed by `uz`/`ru`/`en` for localization, resolved per-request via the `Accept-Language` header.
- Password reset is a 3-step SMS flow (send code → verify code for a token → reset with token) — see `PasswordResetService`.

When adding a new resource, follow the existing pattern: interface in `repositories/interfaces.py` → repo implementation → service with a `get_*_service` factory → handler module registered in `src/api/routes.py` → Pydantic schemas in `src/schemas/`.

## Deployment

CI/CD (`.github/workflows/deploy.yml`) triggers on push to `master`: SSHes into the prod server, hard-resets to `origin/master`, and runs `docker compose -f docker/docker-compose.prod.yml up -d --build`. There is no test gate in this pipeline, so verify changes locally before pushing to `master`.
