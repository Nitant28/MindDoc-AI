# ADR-0002 — PostgreSQL 18 as the system of record

**Status:** Accepted (owner mandate 2026-11-10) — amended

**Context.** v2 uses SQLite and a per-tenant in-memory NumPy index rebuilt on change; vectors are stored as JSON text.
That limits write concurrency, makes the index process-local (wrong as soon as there is more than one worker) and
cannot enforce row-level security.

**Decision.** PostgreSQL 18 holds the evidence tables, `pgvector` (HNSW, halfvec) embeddings, full-text search (FTS
ranking fused with dense results by RRF in SQL), the job table, outbox and audit chain, with Row-Level Security as
defence in depth. Alembic migrations replace the ad-hoc `ALTER TABLE` auto-migrator.

**Alternatives.** Keep SQLite (single writer, no RLS); Postgres + Qdrant (second store and sync problems at our scale);
OpenSearch for lexical search (another cluster to run).

**Consequences.** Transactions span evidence + index + outbox, so idempotency is tractable. Local development needs
Docker. Lexical ranking must be benchmarked against a BM25 sidecar (ablation R1).

**Revisit when.** More than ~5–10M vectors with filtered p95 over target, or Postgres FTS loses R1 materially.

## Amendment 2026-11-10

Source: `docs/review/C_ADR_REVIEW.md`.
- **Version:** PostgreSQL 18 where the host offers it (Render, Neon, Aiven, AWS RDS do; Supabase images are 15/17).
  PG18-only features (`uuidv7()`, `WITHOUT OVERLAPS`) need a documented fallback (application-side UUIDv7, `btree_gist`
  exclusion constraints).
- **Extensions:** `vector` ≥ 0.8.3 (0.8.2/0.8.3 fixed HNSW build overflow and vacuum corruption), `btree_gist`, `pg_trgm`.
- **RLS:** non-owner application role, `ENABLE` + `FORCE ROW LEVEL SECURITY`, tenant set per transaction with
  `set_config('app.tenant_id', …, true)`, `NULLIF(…,'')` so missing context matches no rows; no reliance on `LEAKPROOF`.
- **Lexical search:** built-in FTS (+ `pg_trgm`) for candidates and in-process BM25 over case-scoped chunks; all BM25
  extensions found are AGPL, AGPL/ELv2 or self-host-only, so none is used.
- **Vectors:** exact scan for small cases; per-tenant partial HNSW or iterative scans for large ones (one shared HNSW
  index degrades per-tenant recall).
- **Hosting** is split between demo and pilot (ADR-0013). Sources: `docs/review/research/POSTGRES_INFRA_RESEARCH.md`.
