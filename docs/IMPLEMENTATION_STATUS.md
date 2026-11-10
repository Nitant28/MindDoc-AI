# Implementation status (execution log)

Integration branch: `consolidate/v2-base`. `main` (deployed to Render) is updated only with owner approval.
Statuses: BUILT (code + tests + verified) · EXPERIMENTAL · IN PROGRESS · PLANNED · NOT DONE.

| Milestone | Item | Status | Verification (actual) |
|---|---|---|---|
| R0 | ADR statuses + amendments 0001–0009; new ADRs 0010–0015 | BUILT (docs) | `docs/adr/README.md` |
| R0 | Owner actions runbook (secrets, repo exposure, Neon, interviews) | BUILT (docs); actions themselves **require owner** | `docs/OWNER_ACTIONS.md` |
| R1 | Exact `Money` type (ADR-0010) | BUILT | 26 tests incl. 2,000 random round-trips and a no-float CI guard |
| R1 | StatementBench v0 generator + scorer | BUILT | 60 synthetic statements (40 dev A–D, 20 held-out test E–F), 3,839 rows |
| R1 | Baseline of the 2.1.0 pipeline | BUILT | dev: row F1 **0.000** (0 of 2,602 rows) — no transaction extractor exists yet |
| R1 | Customer interviews | NOT DONE — **owner** | plan in `docs/review/D_MARKET_RESEARCH.md` §7 |
| R2 | PostgreSQL support (pg8000, pooling), Alembic baseline (15 tables) | BUILT | full suite on PostgreSQL 16 (local) **70 passed**; CI job on PG18 + pgvector 0.8.7 added |
| R2 | Row-level security: non-owner role, FORCE RLS on 12 tables, per-transaction tenant context, append-only audit | BUILT | 5 database-level tests on the real app role (select/update/delete/insert isolation, fail-closed, pooled-connection reuse, child-row tenant default, audit immutability) |
| R2 | Bug found and fixed: pooled connections opened before migrations bypassed RLS | BUILT | `engine.dispose()` after migrations; full-suite RLS tests pass |
| R2 | Durable job queue (claim/lease/heartbeat/backoff/dead-letter/idempotent enqueue) + embedded and standalone worker | BUILT | `tests/test_jobs.py`: async upload → worker → completed; crash + lease expiry → re-claim, no duplicate chunks; retry → dead-letter; permanent failure visible + reprocess; 24 jobs × 4 concurrent workers → no duplicate claims (PostgreSQL) |
| R2 | Asynchronous ingestion (202 + status + reprocess), Upload page follows progress, document list shows state | BUILT | API tests; frontend type-check + lint (0 errors); **not yet checked in a browser** |
| R2 | Case scoping (default "General" case per tenant; uploads linked) | IN PROGRESS | data model + linking done; case API/UI not yet |
| R2 | SQLite → PostgreSQL data migration tool | BUILT | real install (2 users, 4 docs, chats) copied: 14/14 tables exact, inserts validated by RLS, app queries work after migration; refuses non-empty targets |
| R2 | Backup/restore procedure | BUILT (docs) | `docs/DEPLOYMENT.md` §4; **restore drill not yet executed** against a hosted database |
| R2 | pgvector embeddings, FTS retrieval on PostgreSQL | PLANNED (R6) | embeddings still JSON text; in-process index unchanged |
| R2 | Demo on Neon | NOT DONE — **owner** (Neon account) | `docs/OWNER_ACTIONS.md` §3 |

Known limitations introduced or remaining:
- On the free Render demo the uploaded originals live on ephemeral disk; object storage is R9.
- SQLite remains a single-user fallback without RLS or concurrent job claiming.
- Local tests use PostgreSQL 16 / pgvector 0.6 (pgserver); CI uses PostgreSQL 18 / pgvector 0.8.7. No PG18-only SQL is used.
