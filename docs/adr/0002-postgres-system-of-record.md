# ADR-0002 — PostgreSQL 18 as the system of record

**Status:** Proposed

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
