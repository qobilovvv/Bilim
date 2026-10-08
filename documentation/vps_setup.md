# Production deployment

Run commands from the repository root. The production image runs as UID 10001 (`app`), includes Alembic migrations, and publishes the API only on localhost. PostgreSQL has no host port. Use a dedicated deployment account, Docker Compose v2 with `--wait` support, and an HTTPS reverse proxy.

## Prepare configuration and data

1. Copy `.env.example` to `.env`, set permissions to 600, generate an independent JWT secret, and fill PostgreSQL/Eskiz credentials. URL-encode special characters in database credentials in `DATABASE_URL`. Use `postgres-db` as the database hostname inside Compose.
2. Set production CORS origins to exact frontend origins. Set `TRUSTED_PROXY_IPS` to the reverse proxy source IP as seen by the container; a host proxy commonly reaches it through the Docker bridge gateway. Do not trust arbitrary forwarded headers. Authentication throttles use the resulting client IP.
3. Preserve existing media and PostgreSQL volumes. Existing media volumes created by root need a one-time ownership adjustment to UID/GID 10001 before starting this image. Inspect the actual named volume and back it up before changing permissions. Never recreate data volumes as an upgrade shortcut.
4. Take and verify database and media backups. Clean invalid historical data identified by new constraints before migrating: duplicate normalized phones, invalid roles/types, negative prices/orders, empty names, and invalid homework values. Legacy NULL account flags become conservative inactive/non-superuser/unblocked values. Review affected accounts.

```bash
docker compose --env-file .env -f docker/docker-compose.prod.yml build api
docker compose --env-file .env -f docker/docker-compose.prod.yml up -d --wait postgres-db
docker compose --env-file .env -f docker/docker-compose.prod.yml run --rm --no-deps api alembic upgrade head
docker compose --env-file .env -f docker/docker-compose.prod.yml up -d --no-build --wait --wait-timeout 120 api
curl --fail http://127.0.0.1:8000/readyz
```

A migration failure stops deployment. Investigate and correct the specific legacy records; migrations do not invent identities or silently alter prices. Existing tokens are invalid after the session migration, so clients must log in again. Refresh is `POST /api/v1/refresh`; logout revokes all account sessions. Frontends must adapt to the catalog/content split, draft publishing, stricter request validation, and authenticated private media. JSON profile updates support explicit clearing of nullable fields; multipart updates treat omitted fields as unchanged.

## Proxy and monitoring

Proxy to `127.0.0.1:8000`, preserve Host, set `X-Forwarded-Proto`, and set a trustworthy client forwarding header. Configure `client_max_body_size 520m` (the API video limit is 500 MiB plus multipart overhead), suitable upload timeouts, and `proxy_request_buffering off` where streamed uploads are intended. TLS certificates, firewall rules, and DNS are deployment responsibilities.

Collect structured application logs and monitor `/readyz`, 5xx rates, latency, disk usage, PostgreSQL connections, and cleanup backlog. Requests include `X-Request-ID`; route templates avoid logging user paths, bodies, credentials, or query strings. Administrator-only `/api/v1/moderation/metrics` returns process-local counters; scrape/aggregate externally for multi-process or historical monitoring. Set alerts in the infrastructure monitoring system.

## CI release gate

Pull requests and pushes to main/master run lint, formatting, targeted type checks, PostgreSQL integration tests, and Docker build/start checks. Deployment runs only for a tested push to master. It fetches and checks out the exact tested SHA and refuses tracked local changes instead of resetting them.

Configure production environment secrets `SERVER_HOST`, `SERVER_USER`, `SERVER_SSH_KEY`, and `SERVER_FINGERPRINT` (verify the SSH server fingerprint independently). Use a dedicated server account. Configure environment protection/branch rules for your organization. No workflow or production deployment was executed during this local hardening work.

## Backups, restore, and maintenance

With writes quiesced, run `BACKUP_DIR=/private/backup/location bash scripts/backup.sh`. It writes a PostgreSQL custom-format dump and media archive with restrictive permissions. Store encrypted copies off-host, define retention, and routinely restore into a separate environment. To restore: stop API writes, restore the dump with `pg_restore` into an appropriate empty database, restore media with UID/GID 10001 ownership, run migration/status checks, then verify readiness and representative content before reopening traffic. Test these steps with your volume layout; never rehearse on production.

Schedule `docker compose --env-file .env -f docker/docker-compose.prod.yml exec -T api python -m scripts.cleanup_media` periodically. Each invocation processes up to 100 queued paths, with failed deletions retained for retry. Increase schedule frequency if the backlog grows.

Inventory legacy orphan media with `python -m scripts.reconcile_media` inside the API container. It defaults to a dry run and ignores files younger than 24 hours. Pause uploads/mutations and inspect the report before `--queue`; cleanup_media then performs deletion. Back up media before enabling reconciliation. Session/reset tables may need retention pruning as deployment volume grows; expired records do not grant access.

Before application rollback, check schema compatibility. Restore a verified backup when necessary; do not automatically downgrade populated production schemas. See the migration guide.
