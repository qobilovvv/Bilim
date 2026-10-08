#!/usr/bin/env bash
# Snapshot data before a release. Quiesce writes for a mutually consistent DB/media backup.
set -euo pipefail
umask 077
backup_dir="${BACKUP_DIR:?Set BACKUP_DIR to a private backup directory outside the checkout}"
mkdir -p "$backup_dir"
backup_stamp="$(date -u +%Y%m%dT%H%M%SZ)"
compose=(docker compose --env-file .env -f docker/docker-compose.prod.yml)
"${compose[@]}" exec -T postgres-db sh -c 'pg_dump --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" --format=custom' > "$backup_dir/database-$backup_stamp.dump"
"${compose[@]}" exec -T api tar -C /app/media -czf - . > "$backup_dir/media-$backup_stamp.tar.gz"
printf 'Backup created in %s\n' "$backup_dir"
