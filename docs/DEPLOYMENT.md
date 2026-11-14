# Deployment, operations, backup and recovery

Topology decisions: ADR-0013. Database design: `docs/review/G_POSTGRES_ASYNC_DESIGN.md`.

## 1. Environments

| | Development | Demo (Render free) | India pilot (proposed) |
|---|---|---|---|
| Database | local PostgreSQL 18 + pgvector (Docker `pgvector/pgvector:0.8.7-pg18`), or `pgserver` for tests; SQLite only as a single-user fallback | Neon Free (PG18 + pgvector), owner creates the project (docs/OWNER_ACTIONS.md §3) | AWS RDS PG18, Mumbai (pricing and residency check pending) |
| Worker | `python -m app.worker` or embedded | **embedded** (`EMBEDDED_WORKER=true`, default) | separate worker service, `EMBEDDED_WORKER=false` |
| Files | `STORAGE_DIR` folder | container disk is ephemeral on the free plan: originals are lost on restart (documented limitation) | S3 (Mumbai) — not yet implemented |

**Frontend on Vercel (owner decision 2026-11-12).** The Vercel projects linked to this repository host only the static
frontend. `vercel.json` (repo root) and `frontend/vercel.json` (for a project whose Root Directory is `frontend`) build
`frontend/` and serve `frontend/dist` with an SPA fallback. They rewrite `/api/*` to the Render backend
(`https://minddoc-ai-2.onrender.com`), so the browser stays same-origin and needs no CORS change. `.vercelignore`
keeps backend code and Python manifests out of Vercel builds.

Known limits:
- Vercel **preview** deployments of a branch call the **main** deployment on Render. Endpoints that exist only on the
  branch return errors there until the branch is merged and Render redeploys.
- Previews sit behind Vercel's login (deployment protection).
- Production Vercel deployments come from `main`, which needs these files merged first.
- Every request reaches Render from Vercel's servers. The login rate limit keys on the connecting address
  (`request.client.host`), so users may share one limit. Trusting a forwarded-for header would be spoofable unless the
  proxy chain is pinned; it is not changed yet.
- Vercel's limits on proxied request size and duration apply to uploads and long requests and have not been measured.
  Large uploads may need to go to the Render URL directly.

**Search on PostgreSQL (migration 0007).** The migration creates the `vector` extension if the server offers it
(Neon and the `pgvector/pgvector` image do). Without it, the full-text column is still created and search stays in
process. Rows that row-level security hid from the migration get their vectors at the first search for each
tenant. There is no HNSW index: exact scans suit case-sized corpora; a per-tenant partial index is the step for large
tenants (ADR-0002).

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
| `RETRIEVAL_BACKEND` | `auto` | `auto`: hybrid search inside PostgreSQL (needs the `vector` extension, migration 0007, and a 384-d embedding model) when every chunk of the tenant has a vector, else in process; `memory`: always in process (rollback switch) |
| `JWT_SECRET`, `CORS_ORIGINS`, provider keys | — | see `docs/MANUAL.md` §4 |
| `ACCOUNT_HASH_KEY` | derived from `JWT_SECRET` | key for the keyed hash of bank account numbers (only the masked number is stored). Set it explicitly and keep it stable: a new key gives the same account a new hash until statements are re-analysed |

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

## 6. Release log

**2026-11-13: `main` = `2ceb33c`** (merge of `consolidate/v2-base`, R0–R6 and the R5 leftovers; owner-approved).
- **Render** (`minddoc-ai-2.onrender.com`, Docker, free plan, SQLite) was live with the new build about 2 minutes
  after the push.
  - `/api/health` returns 200.
  - Every new route is present (accounts, findings, reports, claims, statements, PostgreSQL search).
  - Protected routes answer 401 without a token; no errors.
  - The single-page app and `/findings` are served.
  - The health endpoint still reports version "2.1.0": the version string was not bumped.
- **Vercel production:** `mind-doc-ai`, `mind-doc-ai-lxft` and `mind-doc-ai-msb6` serve the frontend and proxy
  `/api` to the new Render build (health 200, `/api/findings` 401).
  - `mind-doc-ai-ny1m` builds but returns 500 `FUNCTION_INVOCATION_FAILED` at runtime. Its project settings evidently
    run code as a serverless function rather than serving `frontend/dist`. It needs a settings fix in Vercel, or
    deleting as a duplicate (owner action; not reachable with the assistant's access).
- **Not done:** no production account was created and no data was uploaded; signed-in flows were tested locally and
  in CI only.
- **Known limits of this deployment:**
  - The free plan resets the SQLite database and uploads on every deploy, including this one.
  - `ACCOUNT_HASH_KEY` is unset, so it is derived from the Render-generated `JWT_SECRET`.
- **Rollback:** redeploy `f11a241` (the previous `main`) from the Render dashboard. On SQLite the schema is recreated,
  so there is no migration to reverse.

**2026-11-14: `main` = `e808bc3`, version 2.2.0** (merge of `consolidate/v2-base`: cases and roles (ADR-0012), PyMuPDF
removed (ADR-0006), R8 fragility, disclosure copies and evidence bundles; owner-approved).
- **Render** reported version 2.2.0 about 1.5 minutes after the push.
  - The new routes are in the API schema (cases, team, disclosures, bundle; 66 paths); protected routes answer 401
    without a token.
  - `/cases`, `/findings`, `/settings` and an invitation sign-up link are served.
  - The Render app serves the new frontend build.
- **CI on `main`:** backend, backend-postgres, frontend and Docker all green.
- **Vercel production:**
  - `mind-doc-ai` and `mind-doc-ai-msb6` serve the new frontend and proxy `/api` to version 2.2.0.
  - `mind-doc-ai-lxft` proxies `/api` to 2.2.0; its frontend serves the new frontend.
  - `mind-doc-ai-ny1m` still returns 500 (owner action, unchanged).
- **Not done:** no production account, organisation, invitation or data was created; signed-in flows were tested
  locally, in CI and on a local preview only.
- **Known limits:**
  - The free plan reset the SQLite database and uploads again, so earlier accounts are gone.
  - Organisations, cases and invitations made on this deployment will be lost at the next deploy.
- **Rollback:** redeploy `2ceb33c` (the previous `main`) from the Render dashboard.
  - On SQLite the schema is recreated, so there is nothing to reverse.
  - On PostgreSQL, downgrade to `0008` first: this drops `case_members`, `tenant_invites` and `report_disclosures`.

**2026-11-14 (evening): `main` = `bd04ab5`** (merge of `consolidate/v2-base`: R7 detectors and discovery ledger, the UI
redesign; owner-approved).
- **Render** served the new build about 1.5 minutes after the push.
  - The discovery routes are in the API schema (72 paths); protected routes and `POST /api/discoveries/run` answer
    401 without a token.
  - `/discoveries` and the new frontend are served.
  - The health version still reads 2.2.0: it was not bumped for this release.
- **CI on `main`:** backend, backend-postgres, frontend and Docker all green.
- **Vercel:** `mind-doc-ai`, `mind-doc-ai-lxft` and `mind-doc-ai-msb6` serve the new frontend about 5 minutes after the
  push and proxy `/api` to the new build. `mind-doc-ai-ny1m` still returns 500 (owner action, unchanged).
- **Not done:** no production account or data was created.
- **Known limits:** the free plan reset the SQLite database and uploads again.
- **Rollback:** redeploy `e808bc3` from the Render dashboard.
  - On SQLite there is nothing to reverse.
  - On PostgreSQL, downgrade to `0010` first: this drops `discoveries`, `discovery_runs` and `party_tags`.
