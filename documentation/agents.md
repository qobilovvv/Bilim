# Backend development conventions

Read README.md for setup and API behavior. Source is organized as handlers, services (`*_service.py`), repositories, schemas, security, and infrastructure. Keep authorization in services and shared permission helpers. Service constructors depend on repository interfaces; factories wire SQLAlchemy implementations.

Use request-scoped transactions. Repository mutations flush, never independently commit; request dependencies commit before sending success. Preserve independent authentication throttles. Validate replacement content before deleting existing data. Account/session changes take user row locks consistently.

Upload through file_storage helpers. Register new files for rollback and queue old files transactionally. Never serve the media directory as an unrestricted static mount. Public catalog schemas must not include private lesson files or correct-answer flags.

Keep ORM constraints and migrations aligned. Add migrations for schema changes; preserve historical data or fail clearly. Database integration tests must use an explicit disposable `_test` database. Run Ruff, formatting, the configured Mypy scope, and meaningful regression tests before committing. CI owns container validation when local Docker access is unavailable.

Do not store credentials, backups, media, or database files in Git. Keep dependency inputs and generated version pins synchronized. Production releases must run migrations and readiness checks against the exact tested revision. Product additions require their own scope; this repository currently provides authoring/catalog capabilities without student enrollment or payment processing.
