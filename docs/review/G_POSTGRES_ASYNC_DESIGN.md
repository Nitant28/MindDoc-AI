# G — Technical design: PostgreSQL, Alembic, row-level security and asynchronous ingestion

**Implements:** ADR-0001 (amended), ADR-0002 (amended), ADR-0003, ADR-0004 (with F), and the proposed ADR-0013
(deployment topology) and ADR-0014 (build profiles).

**Fixes:** audit A9–A13: SQLite, no migrations, no persistence, synchronous ingestion, process-local index.

**Facts used here** come from `research/POSTGRES_INFRA_RESEARCH.md`. **[v]** = verified on a primary page
2026-11-10; **[u]** = unverified, to check during the spike.

## 1. Decisions in one table

| Topic | Decision | Basis |
|---|---|---|
| Version | **PostgreSQL 18** (18.0 released 2025-09-25; supported to 2030-11) | [v] postgresql.org |
| Extensions | `vector` (pgvector **≥ 0.8.3**, checked at startup), `btree_gist`, `pg_trgm` | [v] pgvector changelog: 0.8.2/0.8.3 fixed HNSW build and vacuum bugs |
| IDs | `uuid` from `uuidv7()` for new rows; **content-derived IDs** (pages, regions, transactions) = UUIDv5/hash of their inputs, so re-processing is idempotent | [v] PG18 `uuidv7()` |
| Temporal integrity | PG18 `WITHOUT OVERLAPS` keys on `(logical_key, sys_period)` and `(logical_key, valid_period)` where needed; period splitting in application code | [v] limits: range type only, no empty ranges, needs `btree_gist`, temporal FKs `NO ACTION` only, no `FOR PORTION OF` in 18 |
| Tenancy | RLS on every tenant table with `ENABLE` + `FORCE`; non-owner app role; tenant set per transaction | [v] PG docs; §4 |
| Queue | Thin in-house **job table** in the same database. Enqueuing in the business transaction *is* the outbox. Procrastinate (MIT) as fallback | [v] SKIP LOCKED / NOTIFY semantics; library survey |
| Migrations | Alembic; hand-written ops for RLS, extensions and functions; run under an advisory lock at container start (free tier) or as a pre-deploy command (paid) | [v] Render pre-deploy is paid-only |
| Vectors | pgvector `halfvec(384)` + HNSW, queries always filtered by tenant and case | [u] filtered-search tuning to measure |
| Lexical | Built-in FTS + `pg_trgm` for candidates, plus an **in-process BM25 over case-scoped chunks**, fused by RRF | [v] ParadeDB `pg_search` is AGPL; VectorChord-bm25 is AGPL/ELv2; pg_textsearch (PostgreSQL licence) needs `shared_preload_libraries`, so self-hosted only |
| Hosting | **Demo:** Render free web + **Neon Free** (PG18, no expiry, scale to zero), with Render Basic $6/month as the alternative. **India pilot:** **AWS RDS PG18 in Mumbai** + containers, falling back to Aiven Mumbai or on-premise Docker | [v] Render has no India region and free DBs expire after 30 days; Neon has no India region; Supabase isn't on 18; Mumbai prices not yet checked |

## 2. Deployment topology (proposed ADR-0013)

| Environment | Web | Worker | Database | Why |
|---|---|---|---|---|
| **Local dev** | `uvicorn` | `python -m app.worker` | Docker `pgvector/pgvector:0.8.7-pg18` [v] | parity with production |
| **Public demo** | Render free web service (512 MB, sleeps after 15 min) [v] | **embedded worker**: threads in the web process polling the job table | Render Basic-256mb **$6/month** [v] (PG18 + pgvector; no expiry), or Neon free (PG18, pgvector 0.8.6, scale to zero, 1 GB) [v] | Free Render Postgres **expires after 30 days with no backups** [v]: not acceptable even for a demo that keeps data |
| **First pilot (India)** | paid web service | **separate worker service** (Render Starter $7/month [v], or the same VM) | **India region**: Aiven (Mumbai/Hyderabad/Delhi) [v], AWS RDS Mumbai/Hyderabad [u], or self-host in the partner's VPC | Render and Neon have **no India region** [v]; lenders will ask about data residency (legal analysis in D) |

**Embedded-worker caveat.** The free instance sleeps after 15 minutes without inbound HTTP traffic [v]. Jobs then
pause until the next request. With leases and retries this is *safe* (no loss or duplication) but not
throughput-reliable. It's acceptable for a demo; never for a pilot. No keep-alive pinging.

## 3. Schema rollout (the R2 subset of F)

R2 creates only the foundation. The financial tables arrive in R3.

```sql
CREATE EXTENSION IF NOT EXISTS vector; CREATE EXTENSION IF NOT EXISTS btree_gist; CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE SCHEMA app;  -- helper functions

tenant(id uuid pk default uuidv7(), name text unique)
app_user(id uuid pk, tenant_id uuid fk, email citext unique, password_hash text, created_at timestamptz)
"case"(id uuid pk, tenant_id uuid, title text, status text, period daterange, created_by uuid, created_at timestamptz)
case_member(case_id, user_id, tenant_id, role text, primary key (case_id, user_id))
source(id uuid pk, tenant_id uuid, sha256 bytea, mime text, filename text, bytes bigint, blob_uri text,
       lifecycle_state text, lifecycle_error jsonb, received_at timestamptz, supersedes_source_id uuid,
       sensitivity text, retention_until date, legal_hold bool default false,
       unique (tenant_id, sha256))                         -- tenant in every unique key (RLS covert channel)
case_source(case_id, source_id, tenant_id, added_at, removed_at, primary key (case_id, source_id))
page(id uuid pk /*hash(sha256,n)*/, tenant_id, source_id, number int, width_pt real, height_pt real, rotation int,
     has_text_layer bool, quality jsonb, ocr_engine text, ocr_confidence real)
region(id uuid pk /*hash(page,kind,bbox_q)*/, tenant_id, page_id, parent_region_id, kind text,
       bbox real[4] /*normalised 0..1*/, reading_order int, text text, method text, method_version text, confidence real)
chunk(id uuid pk, tenant_id, source_id, region_ids uuid[], page_span int4range, text text, context_prefix text,
      chunker_version text, tsv tsvector generated always as (to_tsvector('simple', coalesce(context_prefix,'')||' '||text)) stored)
embedding(chunk_id uuid, model text, tenant_id, vec halfvec(384), primary key (chunk_id, model))
job(...)            -- §5
audit_event(id uuid pk, tenant_id, actor uuid, verb text, object_type text, object_id uuid, payload_hash bytea,
            prev_hash bytea, at timestamptz)                -- hash chain; append-only (no UPDATE/DELETE grants)
```

**Indexes.**
- Every tenant table gets `(tenant_id, …)`.
- `chunk` gets a GIN index on `tsv`.
- `embedding` gets HNSW on `vec` (`halfvec_cosine_ops`).
- `region` gets `(tenant_id, page_id, reading_order)`.

**Compatibility with v2.1 code.**
- SQL views named like today's tables (`documents_v`, `document_chunks_v`) let the existing API and chat code run
  unchanged during the move.
- Endpoints are switched one by one, each covered by the existing API tests.

## 4. Row-level security pattern

1. **Roles.**
   - `minddoc_owner` owns the objects and runs migrations.
   - `minddoc_app` is used by the API and workers: `LOGIN NOSUPERUSER NOBYPASSRLS`, not an owner, DML grants only.
   - `audit_event` gets INSERT/SELECT only.
2. **On every table with `tenant_id`:** `ENABLE` + `FORCE ROW LEVEL SECURITY`, and one policy
   `USING (tenant_id = (SELECT app.current_tenant())) WITH CHECK (same)`.
   `app.current_tenant()` = `NULLIF(current_setting('app.tenant_id', true), '')::uuid`, marked `STABLE`. The
   sub-select makes the planner evaluate it once per statement.
3. **Per-transaction context.** A SQLAlchemy `Session` `after_begin` hook runs
   `SELECT set_config('app.tenant_id', :t, true)`. Never use a session-level `SET`: it leaks across pooled
   connections. Missing context matches zero rows (fail closed).
4. **Explicit predicates stay.** Application queries still filter `tenant_id` (and `case_id`); RLS is defence in
   depth.
5. **Workers.**
   - Each job row carries `tenant_id`; the worker sets the context inside the job's transaction.
   - The dispatcher's cross-tenant claim query runs on the `job` table through a `SECURITY DEFINER` function owned
     by `minddoc_owner`, with a pinned `search_path`.
6. **Don't depend on `LEAKPROOF`**: it's superuser-only, so unavailable on managed hosts [v]. Policies are plain
   column equality.
7. **Tests** (in CI, connecting as `minddoc_app`):
   - tenant B sees 0 rows and can't insert with A's ID
   - a "no context" query returns 0 rows, including on a reused pooled connection
   - a schema test fails if any `tenant_id` table lacks `relrowsecurity` or `relforcerowsecurity`, or if the app
     role has `BYPASSRLS` or owns a table

## 5. Jobs, outbox and asynchronous ingestion

### 5.1 Job table
`job(id uuid default uuidv7(), tenant_id, kind, payload jsonb, idempotency_key, state {queued|running|succeeded|failed|dead},
priority, run_after, attempts, max_attempts, locked_by, lease_until, last_error, created_at,
UNIQUE (tenant_id, kind, idempotency_key))` + partial index on ready jobs.
- **Claiming:** one short transaction (`UPDATE … WHERE id IN (SELECT … FOR UPDATE SKIP LOCKED LIMIT 1) RETURNING`).
  The work runs **outside** that transaction; results commit with the success mark in a second transaction.
- **Leases:** a 5-minute lease with a heartbeat during long OCR. A reaper re-queues expired leases.
- **Retries:** backoff 1 s, 5 s, 30 s, 2 m, 10 m with jitter (EVENT_CATALOG), then `dead` (the dead-letter queue is a
  state shown on a DLQ page).
- **Idempotency:** enqueue is `ON CONFLICT DO NOTHING`. Handlers write with deterministic IDs and record
  `processed(event_id)` in the same transaction as their writes.
- **Wake-up:** `NOTIFY job_ready` on enqueue as a hint (delivered only on commit, < 8000-byte payload [v]), plus
  polling every 2–5 s. `LISTEN` needs a direct connection, not a transaction-mode pooler.
- **Fairness:** a per-tenant concurrency cap in the claim query.

### 5.2 Outbox
While every consumer is a job in the same database, **writing the job row in the business transaction is the
transactional outbox**: both commit or neither does. This simplifies ADR-0003's two hops; see C. The `outbox` table
and relay are added only at ADR-0003 step B (Kafka).

### 5.3 Ingestion pipeline as jobs

```
POST /api/documents/upload  →  tx{ store blob (content-addressed) ; insert source(lifecycle=received) ;
                                   enqueue job(kind=parse, key=sha256|parser_ver) }  →  202 {source_id, state}
parse        → pages + regions (+ OCR on scans)          → enqueue chunk_embed, classify, (statement_extract*)
chunk_embed  → chunks + embeddings                        → enqueue graph_extract
classify     → doc type, summary, keywords, PII, injection flags
graph_extract→ entities/mentions (v2 logic for now)
statement_extract (R3) → statement / statement_txn / reconciliation_check
each step: lifecycle_state advanced in the same tx; failures → lifecycle=failed(stage, error) after retries
```

- **Progress API:**
  - `GET /api/documents/{id}/status` returns lifecycle, per-stage state and errors.
  - `GET /api/documents/{id}/events` streams the same over SSE.
  - The Upload page shows stage progress instead of waiting for one long request.
- **Backwards compatibility:** `?wait=true` on upload keeps a synchronous mode for tests and small text files,
  with a 30 s cap.
- **Chat during ingestion:** retrieval only sees chunks of sources at `lifecycle ≥ indexed`.

## 6. Retrieval on Postgres

- **Dense search:** `ORDER BY vec <=> :q` over `embedding` joined to `chunk`, filtered by `tenant_id` and the case's
  sources.
  - pgvector's README warns that **one HNSW index shared across tenants hurts per-tenant recall** under filtering
    [v].
  - Small cases (< ~20k chunks) use an exact scan, which is fast and exact.
  - Larger tenants get either partial HNSW indexes per tenant or iterative index scans (`hnsw.iterative_scan`)
    [u: tune in the spike].
  - The R2 acceptance test measures recall against an exact scan.
- **Lexical search:**
  - Built-in FTS (`tsv @@ websearch_to_tsquery`, `ts_rank_cd`) gives candidates. It's **not BM25**.
  - BM25 scoring stays in process over the case's candidate set, reusing today's `BM25` class. Its per-case
    statistics are cached by `(case_id, sources_version)`.
  - Third-party BM25 extensions are excluded unless their licence is permissive. Some popular ones are AGPL
    [u: confirm per extension before any use].
- **Fusion:** RRF, rerank and MMR stay as today.
- **Gate:** ablation R1 (ADR-0002) on the RB benchmark (H). Results must be within ±1 point of the SQLite-era
  pipeline before switching.

## 7. Alembic and migration from SQLite

- **Baseline revision** creates extensions, roles (when the host allows it; otherwise documented manual steps),
  schema, helper functions, policies and indexes. Autogenerate doesn't track policies, functions, extensions or
  triggers, so those are explicit `op.execute()` steps. Every migration has a downgrade where feasible and a test.
- **Running migrations:**
  - Free tier: at container start, under `pg_advisory_lock(…)`, so only one instance migrates.
  - Paid tier: Render pre-deploy command [v].
- **One-time copy from SQLite** (`tools/migrate_sqlite_to_pg.py`):
  1. Read every v2.1 table.
  2. Map `documents` → `source` + `page` (from `vision_json`), `document_chunks` → `chunk` + `embedding`
     (JSON → halfvec), entities/mentions/relations as-is (`co_occurs` → `co_mention`), users and tenants
     (`default` → quarantined "legacy" tenant, owned by an admin).
  3. Verify row counts and content checksums.
  4. Originals missing from blob storage are marked `lifecycle=failed(parse,'original missing')`.

  On the live demo the data resets anyway (free plan), so the copy matters for local and pilot installs.
- **SQLite support ends** for the application at R2 (RLS, ranges and pgvector have no SQLite equivalent). One dialect
  means one set of behaviours to test.

## 8. Testing and CI

- GitHub Actions service container `pgvector/pgvector:0.8.7-pg18` [v]. The pytest session runs Alembic `upgrade
  head` on a fresh database and connects as `minddoc_app`. Each test runs in a transaction that is rolled back, with
  explicit tenant context.
- New suites:
  - RLS (§4.7)
  - migration up/down
  - job semantics: claim exclusivity under 4 concurrent workers; lease expiry and re-claim; idempotent re-enqueue;
    DLQ after `max_attempts`
  - kill-mid-job resume, without duplicate rows
- The Docker CI job adds a Postgres service and repeats the 512 MB boot plus smoke test with the embedded worker.

## 9. Cost, measures, risks

| Item | Estimate / measure |
|---|---|
| Engineering | ≈ 15–20 days (J R2) |
| Hosting | demo DB about $6/month (or $0 on Neon free); pilot: India-region DB + worker, priced per host when chosen |
| Success | J R2 acceptance: upload < 1 s; kill/resume without duplicates; RLS tests; retrieval parity ±1 point; lossless migration; slim image ≤ 512 MB |
| Risks | RLS misconfiguration → schema test + non-owner role; NOTIFY global lock at high commit rates → one NOTIFY per transaction, polling fallback; free-tier sleep → demo only; pgvector < 0.8.3 on a host → startup check refuses to run |

## 10. Contradictions with the current ADRs (for C)

1. ADR-0003's outbox → dispatcher → job hop isn't needed while jobs live in the same database (§5.2).
2. ADR-0002 assumes one host. In reality the demo and the pilot need different hosts: there's no India region on
   Render or Neon, and free Render DBs expire.
3. "Supabase on Postgres 18" can't be assumed: its images are 15.x/17.x [v]. Use the `btree_gist` exclusion
   fallback if a host lacks 18.
4. Migrations can't use a pre-deploy step on Render's free tier; hence the advisory-lock-at-start pattern.
5. ADR-0001/0003's separate worker processes can't run on Render's free plan; use the embedded worker for the demo.
6. ADR-0002's "benchmark against a BM25 sidecar" has no licence-clean extension to use. The in-process BM25 is the
   reference instead.
7. ADR-0002: a single shared HNSW index degrades per-tenant recall (see §6).
8. ADR-0002: `LEAKPROOF` is superuser-only, so policies must stay plain column comparisons.
9. ADR-0004: Postgres has no native bitemporal tables. The pattern is one append-only table per entity, a
   `sys_period`, and a partial or temporal exclusion constraint (F §3).
