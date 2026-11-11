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
| R2 | CI fixes after R2: auth rate limit tripped by the test suite; Docker smoke test did not wait for async ingestion | BUILT | `RATE_AUTH_PER_MIN` setting (test override) + a 429 test; smoke test polls `/status` until `completed`; **CI green** on `8d22382` and `5dff891` (backend, backend-postgres, frontend, Docker smoke) |
| M1 | Market decision gate | OPEN — **owner** | needs interviews; R3 proceeds as low-regret (statements are used by both candidate markets) |
| R3 | Layout-generic text-layer statement extractor (ADR-0011): word boxes → header lexicon (data file) → right-edge amount columns → dated rows + wrapped narrations → special rows (opening, B/F, C/F, closing) | BUILT | StatementBench dev (40 stmts, 2,602 rows): row F1 **1.000**, statement exact **1.000**, reconciled **1.000**, 0.51 s/page. Held-out test (20 stmts, families E–F, scored once with frozen code): F1 **1.000**, exact **1.000**. Caveats in `benchmarks/reports/STATEMENTBENCH.md` (same author, synthetic, clean, text layer only) |
| R3 | Reconciliation with ranked diagnoses (row, segment, opening, closing; reversal pairs; direction inferred from balances; same-date reorder search over blocks up to 12 rows; knock-on failures point to their root row) — values never modified | BUILT | unit tests: dropped-digit amount, swapped direction, missing row, reversal pair, inferred direction, no-balance → `not_checkable`, inputs unchanged after reconcile |
| R3 | `GET /documents/{id}/statement` + row-box page highlight (`/page/{n}/image?box=`) rendered with pypdfium2 (Apache-2.0/BSD) | BUILT | API test: reconciled, rows equal gold, box → PNG with 1 highlight, malformed box 422, bad page 404, other tenant 404; non-statement PDF → `is_statement: false` |
| R3 | Statement panel on the document page (run, status, summary, failed checks with hypotheses, transactions, click a row → page with the row boxed) | BUILT | type-check, lint (0 errors), production build; **checked in a browser** on a local preview: a statement with one misprinted balance showed *Needs review*, row 21 ranked as a misread balance, row 22 labelled as its knock-on, and *View on page* boxed the correct row on page 1 |
| R3 | Statement persistence (migration 0003: `statements`, `statement_txns`, `reconciliation_checks`, BIGINT paise, forced RLS) and automatic analysis of statement-like PDFs after ingestion (`analyse_statement` job); the engine sets the document type to `bank_statement` | BUILT | `tests/test_statement_store.py`: stored once, reused, refreshed, removed with the document; a queued upload is ingested and then analysed by the worker. Migration up/down/up on a clean PostgreSQL database; forced-RLS test covers the new tables. SQLite **85 passed, 6 skipped**; PostgreSQL **91 passed**. Cell-level provenance and a `bank_account` entity are not built yet (R5 needs them) |
| R3 | Account Aggregator deposit import (ADR-0015): `POST /documents/import-aa` (decrypted ReBIT deposit payload, JSON or XML, plus an optional consent reference) and an import card on the Documents page. Strict structural validation against the published schema (checked 2026-11-11), exact decimals, opening balance derived and flagged, closing checked only when the summary balance is dated inside the period. Provenance stored: source, consent reference, payload SHA-256, schema version; per transaction: txnId, reference, value date, mode (migration 0004) | BUILT | `tests/test_aa.py` (18 tests): JSON and XML samples map exactly and reconcile; numeric JSON amounts are exact; a misstated balance is flagged, not fixed; 9 invalid payload types rejected with a reason; DOCTYPE/ENTITY XML and foreign namespaces rejected; API import, refresh keeps the consent reference, duplicates are not re-imported, tenant isolation. **Checked in a browser** (import card → statement with provenance and source-record view). Samples are synthetic, built from the schema; **no real AA payload has been processed**. MindDoc does not act as an FIU/AA and requests no consent |
| R3 | StatementBench v1: fault injection for reconciliation/diagnosis (5 fault types × 300 histories per split) | BUILT | held-out test (scored once): false alarms **0/300**; detection and localisation **1.000** for every fault type; correct hypothesis listed ≥ **0.993**. Top-1 depends on the source prior because a misread amount and a missing row are indistinguishable from the balances alone (`benchmarks/reports/STATEMENTBENCH.md`). Row-level injection only |
| R3 | Full test suite after the R3 changes (engine, persistence, AA import) | BUILT | SQLite **103 passed, 6 skipped** (PostgreSQL-only tests); PostgreSQL 16 **109 passed**; migrations 0001–0004 up/down/up on a clean database; frontend type-check, lint (0 errors), production build |
| R3 | Real-statement accuracy (SB-Real under a DPA; public Apache-2.0 set) | NOT DONE — needs **owner** data agreement | — |

Known limitations introduced or remaining:
- On the free Render demo the uploaded originals live on ephemeral disk; object storage is R9.
- SQLite remains a single-user fallback without RLS or concurrent job claiming.
- The document-type classifier has no bank-statement class (the preview statement was first labelled *Invoice, 47%*).
  The statement engine now overrides the type once its analysis finds transactions. Until that background job runs,
  the classifier's label is shown.
- The pre-check that queues statement analysis is a keyword test (balance + debit/credit vocabulary) on the first pages.
  Its recall on real statements is unmeasured, but the panel can always run the analysis manually.
- Local tests use PostgreSQL 16 / pgvector 0.6 (pgserver); CI uses PostgreSQL 18 / pgvector 0.8.7. No PG18-only SQL is used.
