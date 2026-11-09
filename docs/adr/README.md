# Architecture Decision Records

Format: Context · Decision · Alternatives considered · Consequences · Revisit when. Status is **Proposed** until the
owner reviews Stage C; then **Accepted** or **Rejected** (never deleted — superseded ADRs link forward).

| # | Decision | Status |
|---|---|---|
| [0001](0001-modular-monolith.md) | Modular monolith + worker processes, not microservices | Proposed |
| [0002](0002-postgres-system-of-record.md) | PostgreSQL 18 (+pgvector, FTS, RLS) replaces SQLite + in-memory index | Proposed |
| [0003](0003-job-table-outbox-then-kafka.md) | Postgres job table + outbox now; Kafka at a measurable trigger | Proposed |
| [0004](0004-claim-centric-bitemporal-model.md) | Claim-centric, bitemporal evidence model | Proposed |
| [0005](0005-graph-in-postgres-networkx.md) | Graph in Postgres + NetworkX/graspologic; no graph DB yet | Proposed |
| [0006](0006-document-parsing-stack.md) | Docling + PaddleOCR + Tesseract; licence-clean model policy | Proposed |
| [0007](0007-own-plan-executor.md) | Own typed plan executor with 4 LLM roles; no agent framework | Proposed |
| [0008](0008-primary-market-lender-forensics.md) | Primary market: forensic review of borrower fund flows (India) | Proposed |
| [0009](0009-entity-resolution-splink.md) | Splink-based entity resolution with human-confirmed merges | Proposed |
