# Deployment, operations, backup and recovery

Topology decisions: ADR-0013. Database design: `docs/review/G_POSTGRES_ASYNC_DESIGN.md`.

## 1. Environments

| | Development | Demo (Render free) | India pilot (proposed) |
|---|---|---|---|
| Database | local PostgreSQL 18 + pgvector (Docker `pgvector/pgvector:0.8.7-pg18`), or `pgserver` for tests; SQLite only as a single-user fallback | Neon Free (PG18 + pgvector), owner creates the project (docs/OWNER_ACTIONS.md §3) | AWS RDS PG18, Mumbai (pricing and residency check pending) |
| Worker | `python -m app.worker` or embedded | **embedded** (`EMBEDDED_WORKER=true`, default) | separate worker service, `EMBEDDED_WORKER=false` |
| Files | `STORAGE_DIR` folder | container disk is ephemeral on the free plan: originals are lost on restart (documented limitation) | S3 (Mumbai) — not yet implemented |

SQLite remains supported as a **single-user development fallback**: no row-level security, no concurrent job claiming
(`SKIP LOCKED`), and tenant isolation relies on application filters only. Do not run multi-user deployments on SQLite.

## 2. Configuration (environment variables)

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./minddoc.db` | PostgreSQL: `postgresql+pg8000://USER:PASSWORD@HOST:5432/DB` (pg8000 driver, BSD) |
| `DB_APP_ROLE` | `minddoc_app` | non-owner role created by migration 0002; every app connection runs `SET ROLE` to it |
| `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` | 5 / 5 | per process |
| `EMBEDDED_WORKER` | `true` | run worker threads inside the web process |
| `WORKER_THREADS` | 1 | worker threads per process |
| `ASYNC_INGESTION` | `true` | uploads are queued (HTTP 202); `?wait=true` processes inside the request |
| `JWT_SECRET`, `CORS_ORIGINS`, provider keys | — | see `docs/MANUAL.md` §4 |

## 3. Database migrations

- PostgreSQL schema is managed by Alembic (`migrations/`). On startup the app runs `upgrade head` under an advisory
  lock (`app/database/migrate.py`), so several instances can start at once safely. Hosts with a pre-deploy hook can run
  `python -m app.database.migrate` there instead.
- Migration `0002` creates the role `minddoc_app` (NOLOGIN, non-owner, no BYPASSRLS), grants it table privileges and
  enables **forced** row-level security on every tenant table.
- **Production hardening (owner action):** log in as a dedicated role that is only a member of `minddoc_app`, not as
  the owner, so a compromised connection cannot `RESET ROLE` to the owner:
  ```sql
  CREATE ROLE minddoc_web LOGIN PASSWORD '<from your secret manager>' IN ROLE minddoc_app;
  ```
  and run migrations with the owner credentials only in the deploy step.
- Existing SQLite installations: `python tools/migrate_sqlite_to_pg.py --sqlite ./minddoc.db --postgres <url>`
  (copies tenant by tenant under RLS, verifies row counts, never merges into a non-empty database).

## 4. Backup and restore (PostgreSQL)

**Backup** (logical, consistent snapshot; run as the owner role):
```bash
pg_dump --format=custom --no-owner --file=minddoc-$(date +%F).dump "$OWNER_DATABASE_URL_LIBPQ"
```
(`OWNER_DATABASE_URL_LIBPQ` is the plain `postgresql://…` form without `+pg8000`.) Managed hosts also provide
point-in-time recovery: Neon (history retention per plan), RDS (automated backups, choose ≥ 7 days for a pilot).

**Restore into a new, empty database:**
```bash
createdb minddoc_restore
pg_restore --no-owner --dbname=minddoc_restore minddoc-YYYY-MM-DD.dump
DATABASE_URL=postgresql+pg8000://…/minddoc_restore python -m app.database.migrate   # ensures role + grants
```
Row-level security policies are part of the dump; the role `minddoc_app` is cluster-wide and is re-created by the
migration step if missing.

**Restore test (do this monthly and before a pilot):** restore the latest dump into a scratch database, start the app
against it with `EMBEDDED_WORKER=false`, log in as a known test user, and check that their documents, chats and the
`/api/intel/overview` counts match the production values recorded at backup time. Record date, dump size, restore time
and result in `docs/ops/RESTORE_LOG.md`.

**Uploaded originals** live in `STORAGE_DIR` and must be backed up alongside the database (pilot: S3 versioning).
Without them, page-highlight citations and re-processing are unavailable for the affected documents.

## 5. Health and rollback
- `GET /api/health` — process is up (liveness). Readiness/database checks and structured metrics are R9 work.
- Rollback: redeploy the previous image. Migrations are additive within a release; a release that needs a
  non-reversible migration must say so in its notes and requires a fresh backup before deploying.
- Jobs survive restarts: queued jobs stay queued; running jobs whose worker died are re-queued after their lease
  (5 minutes) expires.
