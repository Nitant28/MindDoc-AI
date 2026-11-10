# MindDoc AI 2.1.0 — review deliverables A–J (2026-11-10)

Requested by the owner before any further implementation: "produce the ten deliverables … Do not implement until
these deliverables are ready and reviewed." Baseline: commit `ee814b0` (`main` = `consolidate/v2-base`).
Authoritative project context: `docs/PROJECT_CONTEXT.md`.

| | Deliverable | File | Author / sources |
|---|---|---|---|
| A | Repository audit at `ee814b0` | [A_REPOSITORY_AUDIT.md](A_REPOSITORY_AUDIT.md) | code, tests, CI, live probes |
| B | BUILT / EXPERIMENTAL / IN PROGRESS / PLANNED / NOT DONE matrix | [B_CAPABILITY_MATRIX.md](B_CAPABILITY_MATRIX.md) | code + measurements |
| C | Review of ADRs 0001–0009 (+ six proposed ADRs) | [C_ADR_REVIEW.md](C_ADR_REVIEW.md) | ADRs vs code, research |
| D | Research report: Indian borrower fund-flow forensics | [D_MARKET_RESEARCH.md](D_MARKET_RESEARCH.md) | web research, cited, [verified]/[unverified] |
| E | Bank-statement parsing and reconciliation design | [E_BANK_STATEMENT_DESIGN.md](E_BANK_STATEMENT_DESIGN.md) | design; facts tagged [u] until confirmed by `research/BANK_STATEMENT_RESEARCH.md` |
| F | Claim-centric bitemporal evidence schema review | [F_EVIDENCE_SCHEMA_REVIEW.md](F_EVIDENCE_SCHEMA_REVIEW.md) | DATA_MODEL.md vs code and E |
| G | PostgreSQL, Alembic, RLS, async ingestion design | [G_POSTGRES_ASYNC_DESIGN.md](G_POSTGRES_ASYNC_DESIGN.md) | `research/POSTGRES_INFRA_RESEARCH.md` (verified) |
| H | Benchmark and dataset strategy | [H_BENCHMARK_STRATEGY.md](H_BENCHMARK_STRATEGY.md) | design |
| I | Leave-one-source-out fragility research proposal | [I_FRAGILITY_RESEARCH_PROPOSAL.md](I_FRAGILITY_RESEARCH_PROPOSAL.md) | literature, verified references only |
| J | Revised roadmap with dependencies and acceptance criteria | [J_ROADMAP.md](J_ROADMAP.md) | all of the above |

## Headline findings

1. **The market (D) is inconclusive, and commercially weaker than the strategy docs assumed.**
   - The regulatory problem is real: RBI's 2026 fraud directions, the 2024 wilful-defaulter direction, and *Amit
     Iron* (2026), under which the forensic report goes to the borrower.
   - But competitors already flag round-tripping (IDfy, Cygnet Finalyze, iAcuity, CypherSOL, Valid8), and published
     fees look capped.
   - Rescored, it's roughly level with the procure-to-pay fallback.
   - → A **market decision gate (M1) after R2**. The foundation work is market-agnostic.
2. **The flagship design is sound and partly novel (E).**
   - The only published comparison found (AI-BAAM, arXiv 2510.16066) shows template-style extraction beating LLM
     pipelines, both on known formats and on speed.
   - **No published work uses running balances to locate extraction errors.** MindDoc's reconciliation diagnosis
     would be new.
3. **The ADRs mostly hold (C)**, with one real tension and several factual fixes:
   - ADR-0006's Docling/PaddleOCR need torch or Paddle. The slim path uses pdfplumber, pypdfium2, Tesseract and
     RapidOCR (ONNX).
   - The outbox hop is redundant while jobs live in the same database.
   - Splink's GPL dependency (igraph) is only an optional extra.
   - There's no licence-clean BM25 extension.
   - Render has no India region, and its free databases expire after 30 days.
4. **The evidence schema needs a financial observation layer, money in paise, case scope and finding snapshots
   (F)** before any statement code is written.
5. **Fragility research (I) is well-defined but blocked.** Its prerequisites don't exist yet; it's an R8 item with
   explicit kill criteria.

## Recommendations at a glance

Each row: why it is necessary · limitation addressed (audit id) · interaction with current code · cost · how success
is measured · main risk.

| Recommendation | Why | Fixes | Touches | Cost | Success measure | Risk |
|---|---|---|---|---|---|---|
| Close exposures (R0) | public old commits; unknown live secret | A1, A2 | settings only | days | old-commit API → 404; default-secret token → 401 | none |
| Postgres + Alembic + RLS + jobs (R2, G) | durability, concurrency, isolation, async work | A9–A13 | models, ingestion, retrieval source | 15–20 d | upload < 1 s; kill/resume no duplicates; RLS tests; retrieval parity ±1 pt | RLS misconfig, migration bugs |
| Money type + financial tables (ADR-0010, F) | exact arithmetic, typed transactions | A14, A15 | new `finance/` | part of R3 | no floats in finance (CI grep); reconciliation false alarms = 0 | over-modelling |
| Statement engine (R3/R4, E) | flagship; evidence-grade transactions | A15, A16 | new module, Document page tab | 27–35 d | StatementBench targets (H §3.4) | synthetic ≠ real layouts |
| AA JSON input (ADR-0015) | lenders receive structured data | market fit | importer | days | sample AA files import and reconcile | schema drift |
| Splink ER + reversible merges (R5) | identity drives fund-flow truth | A20, A19 | entities, graph | 15–20 d | 0 high-risk wrong merges; F §11 tests | over-merging |
| Verifier round 2 + calibration (R6) | measured gaps; uncalibrated score | A17, A18 | `verifier.py`, `rag.py` | 8–10 d | HB v1 independent test; ECE ≤ 0.1 | overfitting |
| Detectors + ledger (R7) | analytical value | — | new `intelligence/` | 15 d | FB recall ≥ 0.9, ≤ 1 false flag / 10 look-alikes | benign look-alikes |
| Executor + LOSO fragility + frozen reports (R8, I) | defensible findings | — | new `agents/` | 15–20 d | I's experiment; lineage ≤ 2 clicks | compute cost |
| Customer discovery (R9, D) | market unproven | — | none | ongoing | D's pass/fail thresholds | slow access to buyers |
| Build profiles slim/ML (ADR-0014) | keep 512 MB path | ADR-0006 tension | Docker, CI | 2–3 d | both profiles build and boot in CI | drift between profiles |

## Status of this review
- Written by the assistant from the repository at `ee814b0`, live probes and web research on 2026-11-10.
- **Nothing in the code was changed.** ADR texts were not edited; amendments and new ADRs are proposals awaiting
  owner acceptance (C).
- Tags: [verified]/[v] = read on a primary source on that date; [unverified]/[u] = to confirm.
