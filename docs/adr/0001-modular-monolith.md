# ADR-0001 — Modular monolith + worker processes

**Status:** Proposed

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
