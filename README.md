# Bilim backend

FastAPI backend for accounts, a multilingual course catalog, teacher authoring, homework definitions, and administration. PostgreSQL is the source of truth for content, sessions, authentication throttles, and deferred media cleanup. Redis is not required.

## Development

Use Python 3.11. Copy `.env.example` to `.env`, generate a JWT secret, and fill database/SMS credentials. For local development set `APP_ENV=development` and use localhost in `DATABASE_URL`; containers use `postgres-db`.

```bash
python3.11 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/alembic upgrade head
.venv/bin/python -m uvicorn src.main:app --reload
```

Alternatively, from the repository root:

```bash
docker compose --env-file .env -f docker/docker-compose.yml build api
docker compose --env-file .env -f docker/docker-compose.yml up -d postgres-db
docker compose --env-file .env -f docker/docker-compose.yml run --rm api alembic upgrade head
docker compose --env-file .env -f docker/docker-compose.yml up -d api
```

API documentation: `/docs` and `/redoc`. Routes use `/api/v1`; login is `/api/v1/login`, seller login is `/api/v1/seller/login`, and administrator login is `/api/v1/admin/login`. `/healthz` checks process liveness; `/readyz` also checks PostgreSQL.

## Checks

```bash
ruff check src tests scripts alembic
ruff format --check src tests scripts alembic
mypy
pytest -q
```

Integration tests run only when `TEST_DATABASE_URL` points to a disposable database whose name ends in `_test`. They migrate and truncate that database. Without it, integration tests are skipped. CI runs them with PostgreSQL 15; local verification also passed with PostgreSQL 18. Mypy currently covers configuration, tokens, localization, and shared validation; broader service typing remains incremental.

Dependencies are version-pinned, including transitive dependencies. Edit `.in` inputs and regenerate using Python 3.11:

```bash
pip-compile --strip-extras --no-emit-index-url --no-emit-trusted-host --output-file=requirements.txt requirements.in
pip-compile --strip-extras --no-emit-index-url --no-emit-trusted-host --output-file=requirements-dev.txt requirements-dev.in
```

## Architecture and behavior

Handlers validate input and call services; services enforce permissions and domain rules; repositories operate inside a request-scoped transaction. Repositories flush changes; the request dependency commits before returning a success response and rolls back failures. Integrity conflicts return HTTP 409. Authentication throttles use an independent transaction so rejected requests still count.

Access tokens refer to database sessions and account versions. Refresh tokens rotate once; logout, password changes, password recovery, and account blocking revoke sessions. Password recovery stores digests, expires challenges, and persists failed attempts. Argon2 and image processing run outside the event loop with bounded worker concurrency for password hashing.

Public course responses contain catalog metadata and a module/lesson outline. Teacher/admin content uses `/api/v1/courses/{id}/content`; homework definitions and answer keys require ownership/admin access. New courses start as drafts; publish with `is_active=true`. Public visibility also requires an active category and parent, and an active unblocked teacher. `/media` checks database references and permissions; private playback/download requests need a Bearer header. There is no student entitlement model yet.

Uploads stream in chunks, enforce size limits, and reencode validated images as WebP. New files are removed after transaction rollback. Replaced/deleted files enter a transactional cleanup queue, retried by `python -m scripts.cleanup_media`. Old unreferenced files can be inventoried using `python -m scripts.reconcile_media`; see the deployment guide before enabling deletion.

Enrollment, progress, student submissions, grading execution, payments, and certificates remain outside this hardening work.

See [deployment](documentation/vps_setup.md), [migrations](documentation/migration.md), [admin bootstrap](documentation/admin.md), and [remediation record](documentation/remediation.md). The [original review](documentation/project_review.md) describes the repository before these fixes.
