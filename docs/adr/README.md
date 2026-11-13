# Architecture Decision Records

Format: Context · Decision · Alternatives · Consequences · Acceptance / Revisit when. Statuses: **Proposed**,
**Accepted**, **Superseded** (links forward), **Rejected**. ADRs are never deleted; changes are dated **Amendment**
sections.

On 2026-11-10 the owner's execution mandate stated the architecture baseline explicitly; decisions it states are
recorded as *Accepted (owner mandate)*. Review behind every amendment: `docs/review/C_ADR_REVIEW.md`.

**Reconciled amendment count:** of 0001–0009, seven carry amendments (0001, 0002, 0003, 0004, 0006, 0008, 0009), two carry
notes only (0005: co-mention separation; 0007: "LLMs never compute numbers"). The earlier summary "4 amended + 1 factual
fix" undercounted 0003 and 0008.

| # | Decision | Status |
|---|---|---|
| [0001](0001-modular-monolith.md) | Modular monolith + worker processes (embedded worker for demo hosts) | Accepted — amended |
| [0002](0002-postgres-system-of-record.md) | PostgreSQL 18 + pgvector + FTS + RLS + Alembic | Accepted — amended |
| [0003](0003-job-table-outbox-then-kafka.md) | Job table (= outbox while in one DB); Kafka at a trigger | Accepted — amended |
| [0004](0004-claim-centric-bitemporal-model.md) | Claim-centric bitemporal evidence model (+ financial observation layer) | Accepted — amended |
| [0005](0005-graph-in-postgres-networkx.md) | Graph in Postgres + NetworkX/graspologic | Accepted — note |
| [0006](0006-document-parsing-stack.md) | Parsing: slim (pdfplumber/pypdfium2/Tesseract/RapidOCR) + optional ML (Docling, PaddleOCR-VL) | Accepted — amended |
| [0007](0007-own-plan-executor.md) | Own typed plan executor, 4 LLM roles, deterministic tools | Accepted — deferred to R8 |
| [0008](0008-primary-market-lender-forensics.md) | Primary market: borrower fund-flow forensics (India) | **Proposed — contested, gate M1** |
| [0009](0009-entity-resolution-splink.md) | Splink (core, no igraph) + human-confirmed reversible merges | Accepted — amended |
| [0010](0010-money-integer-paise.md) | Money as integer minor units + explicit currency | Accepted |
| [0011](0011-statement-extraction-strategy.md) | Statement extraction: layout-generic geometry + balance arbitration | Accepted |
| [0012](0012-case-scoping.md) | Case (engagement) scoping inside tenants | Accepted |
| [0013](0013-deployment-topology.md) | Deployment topology (dev / demo / India pilot) | Accepted (pilot host Proposed) |
| [0014](0014-build-profiles.md) | Build profiles: slim (default, torch-free) and ML (optional) | Accepted |
| [0015](0015-account-aggregator-input.md) | Account Aggregator data as a consent-scoped import | Accepted |
