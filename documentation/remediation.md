# Backend remediation record

Completed locally on 2026-10-08. Scope agreed with the owner: fix and harden the existing Bilim backend; student/payments features are excluded. The original assessment in project_review.md is historical and references pre-remediation filenames/behavior.

## Changes committed separately

| Commit | Result |
| --- | --- |
| `cd36142` | Blocked/inactive accounts fail authentication; signing secrets are mandatory and validated. |
| `1ca4dc5` | Request writes are atomic; invalid homework replacements preserve previous content; integrity conflicts return 409. |
| `c430d45` | Chunked bounded uploads, image reencoding, rollback cleanup, and durable deferred file deletion. |
| `70e7307` | Public catalog separated from owner/admin content; private files and homework answer keys require authorization. |
| `9edef53` | Database sessions, refresh rotation, account-wide logout/revocation, recovery attempt limits and locking, persistent throttles, bounded Argon2 offloading, pooled SMS client. |
| `f8e9b6d` | Strict input validation, discriminated homework requests, normalized phones, nullable update semantics, domain constraints, draft-by-default courses. |
| `9e4aa87` | Serialized category mutations, enforced two-level trees, consistent active child/parent visibility, language quality parsing. |
| `c642b4f` | Lightweight ownership queries, fewer redundant reads, stable pagination ordering, configurable smaller connection pools, ordering indexes. |
| `ab79d30` | Explicit nonnullable account flags and data-aware historical downgrade behavior. |
| `2517b6f` | Conventional service filenames, repository interface contracts, formatting/lint cleanup, incremental type checks. |
| `cfb2059` | Direct dependency inputs and pinned transitive graphs; unused runtime dependencies removed; orphan inventory/cleanup scheduling command. |
| `d7d2ddc` | Administrator bootstrap uses account validation and async password hashing without raw database error disclosure. |
| `6f87873` | Concurrent refresh and duplicate registration regression tests. |
| `28d8a77` | Correct Compose paths, migrations packaged/executed, readiness checks, private ports, Redis removal, nonroot runtime, production CORS/proxy settings, structured logs/metrics, backup script, and CI-gated exact-revision deployment. |
| `b788a76` | Standalone Alembic loads the full model registry; subprocess schema-drift regression check. |

README and deployment/admin/migration/development guides now describe the resulting behavior. The review itself was committed as `0adc1c1` before fixes.

## Verification and limits

- 60 tests passed with Python 3.11 against a disposable PostgreSQL 18 database, including authentication/ownership, file rollback/cleanup, draft visibility, category invariants, concurrent registration/reset/refresh, and standalone schema comparison.
- Ruff lint and formatting checks passed; configured Mypy checks passed for four security/configuration/validation modules. This is incremental typing, not full application static verification.
- Alembic upgraded the initially empty test database, downgraded latest invariants/indexes/flags to `b10000000002`, and upgraded back to `b10000000005`. Standalone `alembic check` reported no differences.
- A custom-format PostgreSQL dump restored into a second disposable database; retained account data and migration head were checked, and the restored schema matched the models. Production volume/media restore remains an operator rehearsal.
- Dependency consistency (`pip check`) and backup script shell syntax passed. CI defines PostgreSQL 15 integration tests and Docker image/start checks, but CI has not run here.
- Local Docker build/start was unavailable: daemon access was denied and passwordless sudo was unavailable. Production deployment, Eskiz delivery, and realistic traffic/load tests were not performed. No changes were pushed or deployed.

## Follow-up that depends on deployment or product decisions

Apply migrations with backups and audited legacy data, rotate/configure secrets, adapt frontend contracts, correct existing media ownership, configure exact proxy/CORS settings and CI SSH secrets, schedule cleanup, and set monitoring/off-site backup retention. Existing tokens require login again. See vps_setup.md for the rollout sequence.

Search trigram indexes, keyset pagination, caching, object storage/direct uploads, and additional workers need real query plans and workload measurements. Offset/count behavior remains compatible, with deterministic ordering and targeted indexes; speculative infrastructure changes were avoided. Benchmark before choosing these changes. Expired authentication record retention should be sized and scheduled with production volume.

Enrollment, student progress, submissions/grading, payments, certificates, and teacher approval/review workflows are intentionally excluded. Publication now requires an explicit active flag; a complete editorial approval state machine is a separate product change.
