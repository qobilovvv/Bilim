# Bilim backend review

Reviewed on 2026-10-08. Scope: the backend repository, including application code, database models, nine migrations, Docker configuration, deployment workflow, administrator script, and documentation. This is a code and configuration assessment; production traffic, infrastructure, and data were not inspected. Application code was not changed.

## Assessment

Bilim has a useful foundation for a course catalog and teacher authoring platform. Its layered structure is understandable, and the implementation covers accounts, categories, courses, lessons, materials, and homework definitions. It needs security, transaction, and deployment fixes before it should be considered ready for a paid learning platform. Keep the current monolith and improve it incrementally; a rewrite or microservices would not address the immediate problems.

## What exists

| Area | Implemented behavior |
| --- | --- |
| Accounts | User and seller registration; phone/password login; administrator username/password login; profiles, avatars, password changes |
| Authentication | Argon2 password hashes; JWT access and refresh token generation; authenticated user, administrator, and teacher dependencies |
| Password recovery | Eskiz SMS codes, code verification, expiring password reset tokens |
| Teachers | Seller profiles with experience, portfolio, and description; ownership checks for course editing |
| Categories | Parent/child categories, intended two-level hierarchy, Uzbek/Russian/English names, language fallback |
| Course authoring | Course prices and levels, previews, teacher reassignment by administrators, ordered modules and lessons, videos, downloadable materials |
| Homework authoring | Multiple-choice tests with answer keys, text homework, file homework, grading configuration and example files |
| Moderation | Paginated users, teachers, and courses; search, user date/status filters, account updates and deletion |
| Operations | PostgreSQL, async SQLAlchemy, Alembic, development and production Compose files, deployment over SSH, admin creation script, API documentation and liveness endpoint |

There are **41 business endpoints**, plus `/healthz`, and **14 ORM tables**. Redis is provisioned, but no application code currently uses it. The OpenAI SDK is installed, but no application integration uses it. The declared `author` role also has no dedicated workflow.

Not implemented: enrollment/purchases, payment processing, student progress, homework submissions, grading execution, course completion/certificates, refresh-token exchange, logout/session revocation, and a teacher approval/publishing workflow. `bought_courses_count` always returns zero. These are product gaps if Bilim is intended to provide those capabilities, rather than defects in an authoring-only product.

## What is good

- Handlers, services, repositories, infrastructure, and schemas have recognizable responsibilities. This makes targeted fixes practical.
- Database calls and SMS requests use async APIs. Repositories explicitly load relationships, with `selectinload` for large course trees and `joinedload` for small references.
- List responses are smaller than course-detail responses. Course and moderation pagination is capped at 100 records per page.
- SQLAlchemy expressions bind query values rather than constructing raw SQL from user input.
- Passwords use Argon2. JWT verification restricts algorithms and checks token type and required expiration/subject claims.
- Course mutations consistently check teacher ownership or administrator privileges. Authorization uses the current database role rather than trusting only a role claim in the JWT.
- Unique indexes protect phone numbers, usernames, emails, and category paths. Foreign keys and cascades represent the content hierarchy.
- Model imports are centralized for migration discovery. The migration graph has one head and no missing parent revisions.
- API schemas exclude password hashes. Public teacher summaries omit phone numbers, while the administrator course list includes them deliberately.
- Localization and operational documentation provide a useful starting point.

These strengths describe the implementation, not measured throughput or an assurance that all endpoints work under load.

## Fix first: security, data loss, and deployment

### 1. High: blocked accounts still authenticate

Evidence: `src/security/dependencies.py:32`, `src/services/users_scv.py:81`, and `src/services/users_scv.py:118` check `is_active`, but never reject `is_blocked`. Moderation sets the two flags independently. A blocked account can therefore log in and keep using existing tokens when it remains active.

An isolated probe of the actual dependency function returned a user with `is_active=True` and `is_blocked=True`.

Fix: enforce account eligibility consistently at login and on every authenticated request, including administrators and teachers. Test blocking with an already-issued token.

### 2. High: public endpoints expose course content and test answers

Evidence: `src/api/v1/course_handlers.py:80` exposes complete course details without authentication; `src/services/courses_scv.py:54` does not check course activity. The public list also accepts `active_only=False`. The homework GET endpoint is public, and `src/schemas/course_schemas.py:51` includes `is_correct` in returned answer options. `/media` serves all uploads publicly.

Anyone can retrieve inactive course details, lesson video/material paths, and test answer keys. For a paid or assessed learning platform, these bypass the intended access and assessment boundaries. If all content is intentionally free, answer-key visibility and draft visibility still need explicit decisions.

Fix: separate public catalog, teacher authoring, and student learning responses. Public catalog queries should enforce publication visibility. Restrict full learning content to permitted users, omit answer keys from student responses, and authorize protected downloads or issue short-lived signed links. URL randomness alone does not provide authorization.

### 3. High: an invalid homework update deletes existing homework

Evidence: `src/services/homework_scv.py:97` deletes the existing homework before building and validating its replacement. `src/repositories/homework_repo.py:42` commits that deletion immediately.

An isolated probe submitted a replacement test without `pass_ball`: the existing homework was deleted before the request raised HTTP 400. A new insert failure would leave the same gap.

Fix: validate the complete replacement first, then delete/replace in one database transaction. Repositories should flush changes while the service or a unit-of-work boundary owns the commit. The existing request rollback cannot undo an earlier repository commit. SQLAlchemy supports explicit transaction scopes for this purpose. [SQLAlchemy transaction documentation](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html).

### 4. High: failed media replacement can destroy the old file

Evidence: `src/services/lessons_scv.py:51`, `src/services/courses_scv.py:102`, and `src/services/homework_scv.py:124` delete the old file before the new upload is validated and saved. Profile updates also delete the old avatar before the new write and database update finish.

An isolated probe confirmed that video replacement deletes the old video and then rejects an invalid new upload.

Fix: validate and save the replacement, commit the new database reference, then delete the old file. Clean up the new file if the database update fails; retry old-file cleanup if necessary. File operations do not roll back with a database transaction.

### 5. Critical if the fallback is used: JWT signing has a known default

Evidence: `src/infrastructure/config.py:13` sets `JWT_SECRET_KEY` to `secrett`. No configuration check rejects that fallback. Whether production overrides it was not inspected.

Fix: require a sufficiently strong deployment-provided secret and fail startup when it is missing or still the placeholder. Rotate any deployment that has used the fallback. Do not store the replacement secret in source control.

### 6. High: password recovery lacks abuse and concurrency controls

Evidence: `src/services/password_reset_scv.py:32` uses `random.randint`, stores plaintext codes, permits multiple outstanding challenges, and has no attempt cap or resend cooldown. There is no application rate limiter on authentication/reset routes. Sending a code exposes whether the phone is registered and returns raw SMS exception text. Password updates and reset-token invalidation commit separately, and verification/consumption use read-then-write operations without locking.

Consequences include SMS abuse, online guessing, and overlapping requests potentially consuming the same challenge/token. Proxy-level controls, if any, were not inspected.

Fix: use cryptographically secure randomness, store a keyed digest of the low-entropy code, enforce expiration/attempt limits and account/IP throttles, invalidate superseded challenges, return generic client errors, and atomically consume challenges/tokens with the corresponding state change. Python explicitly provides `secrets` for security-sensitive randomness. [Python secrets documentation](https://docs.python.org/3/library/secrets.html).

### 7. High: production Compose resolves incorrect project paths

Evidence: `docker/docker-compose.prod.yml:4` uses build context `.` from inside `docker/`, while the Dockerfile is specified as `docker/Dockerfile`. For the checked-in workflow invocation, that resolves to `backend/docker/docker/Dockerfile`, which does not exist. `env_file: .env` resolves to `backend/docker/.env`, while the deployment guide creates `backend/.env`.

Verified with `docker compose ... config --no-env-resolution --no-interpolate --format json`; no containers were started. Compose resolves relative build paths from the Compose project and Dockerfile paths from the build context. [Docker build specification](https://docs.docker.com/reference/compose-file/build/).

Fix: align production paths with the repository-root context and root environment file, as the development file already does. Verify the exact workflow command on a clean checkout.

### 8. High: production images omit migration files; deployment never runs them

Evidence: `.dockerignore:10` excludes `alembic/versions/*.py`. Development mounts migrations from the host, concealing this problem; production does not. `.github/workflows/deploy.yml` rebuilds/restarts without a migration step, test gate, or deployment smoke test.

Fix: include migrations in the image, verify the expected migration head, apply migrations as an explicit release step, and gate deployment on tests and a smoke check. Use backward-compatible migrations and a documented rollback procedure; do not assume code rollback reverses data changes.

### 9. Medium: startup and production health checks are broken in specific conditions

Evidence: `src/main.py:44` constructs `StaticFiles(directory="media")` before lifespan creates that directory. The reviewed checkout has no `media/`, so a configured local app can fail during import. Starlette's constructor checks the directory by default. [Pinned Starlette source](https://raw.githubusercontent.com/encode/starlette/1.0.0/starlette/staticfiles.py).

The production health check uses `CMD` with `|| exit 1` embedded inside its URL argument. `CMD` does not run a shell. The Dockerfile also does not install curl. `/healthz` only returns a constant and cannot establish database readiness. [Docker health-check reference](https://docs.docker.com/reference/compose-file/services/#healthcheck).

Fix: create/configure media storage before mounting it; use the development Python health-check approach or a valid installed command. Keep liveness simple and add a separate database readiness check. Close the DB engine and shared clients on shutdown.

### 10. High: production publishes Redis and PostgreSQL ports

Evidence: production Compose publishes PostgreSQL and Redis without specifying a loopback address. Redis has no authentication configured. Actual internet reachability depends on the host/network setup, which was not inspected.

Fix: keep database/cache services on the private Compose network; bind any necessary host access to loopback. If host Nginx is the entrypoint, bind the API to loopback too. Run the application container as a non-root user and use a dedicated deployment account.

## Correctness and API improvements

| Finding | Evidence and proposed improvement |
| --- | --- |
| Category depth can exceed two | `categories_scv.py:75` validates the new parent but not the moved subtree. A probe accepted a root with children under another root, producing three actual levels while child `level` stayed 2. Validate descendant depth/cycles and keep stored levels consistent, or derive depth. |
| Inactive children leak through active category lists | `categories_repo.py:24` filters roots only; the serializer includes every loaded child. Apply the visibility policy to children as well. |
| Schema validation is too weak | Most names, phone numbers, passwords, emails, prices, scores, and order indexes have only basic types. Reject blank names, normalize phone numbers consistently, validate emails, enforce password policy and sensible size limits, and prohibit negative price/score/order values. |
| Homework type validation is fragmented | One schema mixes all optional fields; builders validate only selected rules. Use discriminated request variants for test/text/file/none and enforce valid timers, attainable pass scores, and bounded question/option counts. |
| Upload type validation trusts client metadata | General uploads check extensions; avatars trust the supplied MIME type and preserve an arbitrary filename extension. A claimed JPEG can be stored as `.html` and publicly served. Validate actual image content, re-encode images, and choose a trusted output extension. Serve arbitrary downloads with appropriate disposition/origin isolation. |
| Duplicate writes can become 500s | Uniqueness prechecks race with concurrent registration/profile/category updates; repository commits do not translate integrity errors. Preserve DB constraints and map expected unique/FK conflicts to clear 409 responses. |
| Deleting referenced teachers/categories fails | Courses use `RESTRICT`, but delete services do not explain or translate the conflict. Define reassignment/archive behavior and return a useful conflict response. Protect administrator accounts from unintended self/last-admin deletion according to policy. |
| Refresh tokens are issued but unusable | Token verification exists, but no refresh route, rotation, logout, or revocation state exists. Complete the session lifecycle or remove the unfinished refresh contract. Password changes currently leave existing access tokens valid until expiration. |
| Token subject conversion can raise an uncaught error | `int(claims.sub)` is outside verification error handling. Validate numeric identifiers and return a controlled authentication failure. Catch expected token errors rather than every exception. |
| Update semantics differ | Many optional update fields treat null as "leave unchanged," preventing nullable-field clearing. Establish PATCH semantics using explicitly supplied fields; category parent updates already use `model_fields_set`. |
| Course publication is underspecified | New seller registrations are immediately eligible to author courses, and courses default active. Add draft/review/published states and teacher approval only if editorial control is required. |
| Operational details are inconsistent | Administrator login does not update `last_login`; documentation lists `/api/v1/auth/*`, while auth routes are actually directly under `/api/v1`. Update the contract and documentation together. |

## Optimize after correctness

1. **Stream uploads with a running limit.** `file_storage.py:23` reads each entire upload into memory before enforcing size. Videos permit 500 MiB each; concurrent uploads can exhaust the production 2 GiB limit. Read/write bounded chunks and delete partial files on rejection. Align proxy limits: the documented Nginx configuration permits 100 MiB while the application permits 500 MiB videos.
2. **Move password hashing/verification off the event loop.** Async service methods call synchronous Argon2 functions directly. Use bounded thread offloading and authentication throttles. Keep the strong hashing algorithm and measure CPU/memory/concurrency before setting capacity.
3. **Avoid fetching the full content tree just to check ownership.** Course/module/lesson lookups load nested materials and homework/questions for mutations that need only a few identifiers. Add small permission queries; load detailed content only for responses that require it. Existing eager loading is helpful, but the amount loaded is often excessive.
4. **Reduce redundant post-write queries.** Repositories commonly commit, refresh, and then fetch the same object/tree again. Return deliberately loaded response data after one transaction boundary and measure query count. Preserve async-safe relationship loading.
5. **Paginate lesson content independently.** Course detail grows with every module, lesson, material, and question. Return a summary/curriculum separately and fetch lesson content on demand.
6. **Measure queries before adding indexes.** Filter foreign keys already have indexes. Investigate stable `(created_at, id)` ordering and indexes matching common teacher/category/date queries. For measured substring-search bottlenecks, PostgreSQL trigram indexes can support `ILIKE`; index the actual full-name expression if optimizing user search. [PostgreSQL pg_trgm documentation](https://www.postgresql.org/docs/15/pgtrgm.html).
7. **Use cursor pagination when deep offsets become costly.** The current bounded offset pagination is reasonable for an early product. Add a unique tiebreaker now; change the API when measured scale justifies it.
8. **Reuse an HTTP client for SMS.** Eskiz creates a new `httpx.AsyncClient` for each request. Share a lifecycle-managed client with explicit timeouts and coordinated authentication refresh. Do not blindly retry SMS sends without duplicate-send protection.
9. **Handle media lifecycle fully.** Course/module/lesson cascades remove DB rows but do not clean up all descendant files. Add recorded cleanup jobs/retries and orphan reconciliation. Object storage and direct signed uploads can reduce API bandwidth and enable multiple replicas when needed.
10. **Size the pool and workers together.** The pool allows up to 30 connections per process. Multiplying workers multiplies the potential connection count. Use observed DB latency, CPU, memory, and PostgreSQL capacity to configure these settings.
11. **Use Redis for a defined purpose or remove it.** It currently adds startup dependencies and operational overhead. Shared rate-limit state is one concrete use; cache catalog/category responses only after profiling and defining invalidation.

## Maintainability and verification

- Add meaningful API/service tests and PostgreSQL integration tests. Cover owner vs. another teacher vs. admin, blocked accounts, public/private answer visibility, invalid replacement preserving data, upload failures, concurrent uniqueness/reset consumption, and migrations from an empty DB.
- Gate deployment with tests, a formatter/linter, and type checking introduced gradually. Use a development dependency group rather than putting test tools into the runtime image.
- Depend on repository interfaces if retaining the ABC abstraction; services currently annotate concrete implementations. Alternatively simplify the interfaces if no substitution is needed. Avoid an unnecessary generic repository framework.
- Rename `_scv.py` consistently to a conventional service suffix; extract shared upload rules and clear transaction boundaries. Services may continue using FastAPI exceptions for this small application unless independent reuse requires domain errors.
- Add structured logs, request IDs, response latency/error metrics, and private operational alerts. Avoid exposing provider exceptions and unnecessary personal data.
- Make configuration environment-specific, require secrets, restrict production CORS to intended frontends, and provide a tracked `.env.example`. The gitignore currently ignores `.env.*`, so explicitly allow the template.
- Keep a reproducible dependency lock and distinguish direct dependencies from transitive pins. The gitignore currently excludes common lock files. Remove unused packages after checking intended upcoming work; no dependency vulnerability scan was performed.
- Exclude runtime media from Docker build context, keep migration files, and reduce build-only tools in the runtime image where practical.
- Test and document migration downgrade limitations. The older name migration adds a non-null `full_name` column without backfilling existing users; the username migration restores non-null phone despite allowing phone-less admins. Both need a data-aware policy before being advertised as safe rollback steps.
- Add database CHECK constraints for key numeric/type invariants and align nullable flags/defaults between models and migrations. Test actual schema drift against PostgreSQL.
- Document and exercise database/media backup restores. No backup automation is checked into this repository; external backups may exist.

## Suggested order

| Stage | Deliverables | Completion evidence |
| --- | --- | --- |
| 1. Prevent exposure and data loss | Account blocking, required JWT secret, public/private course and answer boundaries, atomic homework/reset changes, safe file replacement, reset throttling | Regression tests for the concrete findings and concurrent reset behavior |
| 2. Make releases dependable | Correct Compose paths, packaged migrations, startup/health fixes, private DB/cache ports, CI gate and migration release step | Clean image build, migration to head on disposable PostgreSQL, health/smoke checks |
| 3. Strengthen the API | Request validation, conflict handling, category hierarchy/visibility, refresh/session contract, consistent updates | Integration tests and reviewed OpenAPI contract |
| 4. Optimize measured bottlenecks | Chunked uploads, bounded password offloading, smaller ownership queries, query/index tuning, media cleanup, metrics | Before/after query counts, memory measurements, and representative load results |
| 5. Complete the learning product | Enrollment/purchases, payments if needed, protected learning, progress, submissions/grading, completion | End-to-end student and teacher workflows with authorization tests |

## Checks actually performed

- Parsed **56 Python files** successfully without writing bytecode.
- Inspected application modules, repository interfaces, model registration, migrations, scripts, Docker configuration, workflow, and documentation.
- Verified **9 migration revisions**, one head (`0843806de7ed`), and no missing parents using static parsing. This does not establish that migrations execute successfully on PostgreSQL.
- Parsed Compose YAML and checked build/environment path resolution; also ran Docker Compose's own configuration normalization without loading environment files or starting containers.
- Executed four isolated probes using the actual extracted functions with fake dependencies: blocked-account acceptance, deletion before homework validation, deletion before video upload validation, and invalid category reparenting.
- Compared relevant library behavior with official Docker, SQLAlchemy, Python, PostgreSQL documentation and the pinned Starlette source.

**Limits:** no application test suite or lint configuration exists. The local environment lacks FastAPI, SQLAlchemy, Pydantic Settings, Argon2, HTTPX, and pytest; there is no project virtual environment or configured environment file in the checkout. No live app, PostgreSQL integration, Docker build, SMS send, load test, dependency audit, or production inspection was performed. Security exploitability that depends on deployment configuration is stated conditionally. Performance suggestions are hypotheses to measure, not benchmark results.
