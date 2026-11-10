# ADR-0001 — Modular monolith + worker processes

**Status:** Accepted (owner mandate 2026-11-10) — amended

**Context.** One engineer; domain boundaries (ingestion, extraction, graph, discovery, investigation) are still moving.
Today everything runs inside the API process, including minutes-long OCR.

**Decision.** One Python codebase with explicit module boundaries (`ingestion/`, `vision/`, `knowledge/`, `retrieval/`,
`intelligence/`, `agents/`), deployed as an API process plus N worker processes that share Postgres. Modules talk through
function interfaces in-process and through jobs/events across processes.

**Alternatives.** Microservices per stage (operational cost, distributed transactions, no team to own them); keep the
single process (blocks requests, no isolation of CPU-heavy parsing).

**Consequences.** Simple deploys and refactors; workers scale horizontally; module boundaries are enforced with
import rules (`import-linter`) instead of network boundaries.

**Revisit when.** A module needs a different runtime (GPU OCR service) or an independent release cadence.

## Amendment 2026-11-10

Source: `docs/review/C_ADR_REVIEW.md`.
- **Worker modes.** The worker runs either as a separate process (`python -m app.worker`, production) or embedded as
  threads in the web process (`EMBEDDED_WORKER=true`, single-container demo hosts such as Render's free plan, which does
  not allow background workers). Both use the same job table and code; switching is configuration only.
- **Module map** (target → today): `ingestion/` → `app/services/ingestion.py`; `vision/` → `app/vision/`;
  `retrieval/` → `app/ml/retrieval.py`, `app/ml/embeddings.py`; `knowledge/` → `app/ai/knowledge.py`;
  new `finance/` (statement parsing, reconciliation, identifiers); `intelligence/` (detectors, R7); `agents/` (R8).
- Acceptance: a long OCR job does not delay `/api/health`; `import-linter` contract added when the module split lands.
