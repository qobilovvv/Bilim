# Database migrations

From a configured environment run `alembic upgrade head`. In production use:

```bash
docker compose --env-file .env -f docker/docker-compose.prod.yml run --rm --no-deps api alembic upgrade head
```

The current migration head is `b10000000005`. New revisions add media cleanup, database sessions/rate limits, reset controls, domain constraints, ordering indexes, and explicit account flags. Phone identifiers normalize to international digits; collisions or invalid legacy records stop the transaction. Back up and audit populated data before upgrading. Newly created courses default to drafts; existing publication values remain intact. Previously issued JWTs require a new login.

For model changes, generate a candidate with `alembic revision --autogenerate -m "description"`, review data conversions/defaults/constraints, and verify with `alembic check`. Run tests against an explicit disposable `_test` database. Never point integration tests at retained data.

Downgrades are data-aware: older fullname schemas reconstruct a name before enforcing NOT NULL; downgrading nullable phones refuses phoneless accounts instead of inventing numbers. Session/reset schema rollback expires challenges. Production rollback requires schema compatibility analysis and a verified restore plan; automatic downgrade is not part of deployment.
