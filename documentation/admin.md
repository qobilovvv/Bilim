# Administrator bootstrap

Apply migrations first. From the repository root:

```bash
docker compose --env-file .env -f docker/docker-compose.prod.yml exec api python -m scripts.create_admin
```

The command prompts for username, name, optional surname/email, and a hidden password. Username must have 3–64 letters/digits/underscore/dot/hyphen; password must have 12–128 characters. API validation also applies to account details. Duplicate identifiers are rejected. Prefer the interactive password prompt over command arguments to avoid shell history/process exposure.

Log in through `POST /api/v1/admin/login` using username/password. Administrator endpoints use `/api/v1/moderation`; use a Bearer access token. Blocking/inactivating accounts revokes their sessions. Administrator accounts cannot be disabled/deleted through ordinary user moderation endpoints.
