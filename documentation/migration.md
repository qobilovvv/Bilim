# Database Migrations

This project uses **Alembic** to manage database schema migrations.

## Running Migrations in Docker

To apply all migrations to the database inside Docker:

```bash
docker compose -f docker/docker-compose.yml run --rm api alembic upgrade head
```

To automatically generate a new migration after editing database models:

```bash
docker compose -f docker/docker-compose.yml run --rm api alembic revision --autogenerate -m "Describe your changes"
```

## Running Migrations Locally (On Host Machine)

Ensure your virtual environment is active and run:

```bash
alembic upgrade head
```