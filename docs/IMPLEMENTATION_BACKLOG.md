# MindDoc — Prioritised Implementation Backlog (Stage E)

> Order is dependency-driven: **stabilise → measure → foundation → evidence → intelligence → agents → validation**.
> Inputs: `docs/audit/CURRENT_STATE_AUDIT.md` (A-refs), `docs/architecture/*`, `docs/adr/*`, `docs/strategy/*`,
> `docs/research/*`. Estimates are for one engineer, full-time-equivalent; they are planning guesses, not commitments.
> **Nothing in Phases 1–8 starts until the owner has reviewed Stages A–E.**

## Phase 0 — Stabilise and decide (≈1 week, no new features)

**Status (2026-11-10, branch `consolidate/v2-base`, uncommitted):** 0.1 decided — local v2 is the base; ported from
`origin/main`: OpenRouter (as a gateway provider), Docker/Render deploy with persistent `/data`, `.dockerignore`; the
~60 stub "manager" modules, Redis and the 3-D landing page were deliberately not ported. 0.4 done (dead code + stale
docs removed, ESLint flat config, `npm audit` 12 → 2 moderate, CI workflow). 0.5 done (UI relabelled). 0.6 done (page,
pixel, DOCX-inflation caps; per-user rate limits). **0.2 and 0.3 are owner actions and still open.**

| # | Task | Why (evidence) | Done when |
|---|---|---|---|
| 0.1 | **DECIDE the base line of code.** GitHub `origin/main` (25 commits: deployed v1.0.0, OpenRouter, docker-compose with Postgres 15 + Redis, landing page, deploy fixes) and local `main` (`1c888a1`, v2 evidence features + tests) diverged from `3245528`. | audit summary; `git rev-list` 1 vs 25 | owner picks; recommended: v2 as base, port the useful origin pieces (deploy fixes, persistent disk, OpenRouter via the OpenAI-compatible gateway, compose services) in a reviewed merge branch |
| 0.2 | **Live security (owner action on Render/GitHub):** set a strong `JWT_SECRET` on the deployed service and redeploy; restrict CORS to the real origin. | live v1 default secret + credentialed wildcard CORS (audit, verified by preflight) | tokens signed with a private secret; preflight from a foreign origin rejected |
| 0.3 | **Personal data in the public repo (owner action):** `origin/main` tracks 14 uploaded documents (`data/uploads/`, incl. a résumé and tax notices) and 3 derived index files. Make the repo private or remove the files *and purge history* (`git filter-repo`, then force-push — destructive, coordinate first). | audit; verified `git ls-tree` = 14 files | files absent from all refs; `data/` and indexes git-ignored on every branch |
| 0.4 | Repo hygiene: commit `frontend/src/lib/` (the `.gitignore` `lib/` rule is now anchored to `/lib/`), add `.dockerignore`, ESLint flat config, `npm audit` fixes (12 advisories, 7 high), delete dead modules (`services/local_llm.py`, `llama_manager.py`, `deepseek_client.py`, `ollama_client.py`, legacy scripts) and stale docs. | audit: clean clone → 104 TS errors | `git clone` + `npm ci && npm run build` + `pytest` pass in CI |
| 0.5 | **Honesty patch for the trust layer** until Phase 5 replaces it: relabel "Grounded"/"Confidence" as "Evidence overlap" and "Evidence score (uncalibrated)"; state that PII is detected, not redacted; describe injection defence as pattern-based. | audit: verifier marked 6/6 planted hallucinations "supported"; off-topic query scored 0.71 | UI copy matches what the code does |
| 0.6 | Guardrails on cost/DoS: page, pixel and decompressed-size caps on upload; rate limits on upload/query/eval. | audit: no caps; 43 s synchronous ingest | limits enforced + tests |

## Phase 1 — Evidence foundation (≈3–4 weeks) — ADR-0001/0002/0003/0004

1. PostgreSQL 18 (+pgvector) via Docker Compose; SQLAlchemy 2 + **Alembic**; test suite runs on Postgres in CI.
2. Canonical schema from `DATA_MODEL.md` (Source, Page, Region, TableCell, Chunk, Embedding, Mention, Entity,
   EntityIdentifier, ResolutionDecision, Claim, Evidence, Relationship, Event, Review, AuditEvent) with RLS policies.
3. Content-addressed `BlobStore` interface (local FS now).
4. Outbox + job table + worker process; ingestion moves out of the request; lifecycle API + Ingestion Center UI; DLQ view.
5. Data migration from v2/SQLite; legacy shared-`default` tenant (26 users, 16 ownerless docs) → quarantined
   "legacy workspace" owned by an admin, not silently shared.

**Exit:** upload returns < 1 s; a 30-page PDF completes in a worker; kill-mid-document test resumes with no duplicates;
property-based cross-tenant tests pass on Postgres + RLS; lineage API returns Source→Region for every chunk.

## Phase 2 — Measure before you change (≈2 weeks, overlaps Phase 1) — EVALUATION_FRAMEWORK

1. **MindDoc-Synth v0**: seeded generator of a fictional borrower group (statements across banks, sanction letters,
   invoices, GST summaries, stock statements, ledgers, director data) rendered to PDF/XLSX and degraded scans, with
   labelled schemes **and benign look-alikes**.
2. DocBench-50 (labelled target pages), retrieval QA set, and a **hallucination test set** seeded from the audit's
   failures (wrong amount, swapped parties, negation, wrong period, invented claim).
3. Benchmark harness (`benchmarks/`), MLflow tracking, CI smoke suite.
4. **Baseline scorecard of the current stack** — the numbers everything later must beat.

**Exit:** `benchmarks/reports/baseline-*.md` exists with CIs; System page reads it.

## Phase 3 — Document intelligence v3 (≈3–4 weeks) — ADR-0006

1. Docling conversion; PaddleOCR PP-OCRv5 + Tesseract; keep OpenCV quality/deskew; **remove PyMuPDF (AGPL)** →
   pypdfium2 renderer + Docling/pdfplumber text; highlighter on pypdfium2.
2. Regions with normalised bboxes for every page (text-layer *and* OCR) → highlights work on scans.
3. Table cells (TableFormer vs PP-StructureV3 by TEDS); **bank-statement parser with running-balance reconciliation**;
   Tally XML/XLSX ledger import; GST summary parser.

**Exit:** CER/TEDS ≥ baseline; ≥99% of synthetic statement pages reconcile; grounding IoU≥0.5 hit-rate ≥0.9; s/page on CPU reported.

## Phase 4 — Claims, entity resolution, graph explorer (≈3–4 weeks) — ADR-0005/0009

1. Claim extraction for ontology pack 1 (rules for structured rows; schema-constrained LLM for prose), every claim with Evidence.
2. Identifier validation (GSTIN/PAN/IFSC/CIN/DIN); Splink ER with cannot-link rules; review queue for merges; reversible merges.
3. Relationship materialisation with epistemic status; co-mentions separated.
4. **Graph Explorer** (Cytoscape.js): node/edge inspectors showing claims, evidence thumbnails, status; expand/collapse,
   type/status/time filters, path finder, time slider, diff overlay, subgraph export; synced with document viewer.

**Exit:** ER high-risk merge precision ≥0.98, recall ≥0.90 on Synth; 100% of edges open their evidence.

## Phase 5 — Verifier v2 + retrieval on Postgres (≈2–3 weeks)

1. Claim verification: numeric/date/party/negation consistency checks against cited cells and claims, plus an NLI
   cross-encoder (licence-checked), plus recomputation for numbers.
2. Calibrated evidence score (isotonic/Platt on labelled data) — show ECE; abstain below threshold.
3. Hybrid retrieval in Postgres (FTS + pgvector + RRF + rerank), structured retrieval over claims/cells, router v0.

**Exit:** hallucination-set catch rate reported and ≥ the agreed target (set after the baseline); ECE ≤ 0.1; R1–R3 ablations stored.

## Phase 6 — Forensic detectors + Discovery Ledger (≈3 weeks) — INVESTIGATION_ENGINE §5

D1–D7, Benford/threshold tests, IsolationForest/LOF + SHAP, MLflow-registered; Discovery Ledger with dispositions;
findings register, review queue, hash-chained audit.

**Exit:** seeded-scheme recall ≥90% with ≤1 false flag per 10 benign look-alikes on Synth (R1 in COMPETITIVE_ANALYSIS).

## Phase 7 — Evidence-constrained investigation (≈3 weeks) — ADR-0007

Plan executor + tool registry with permissions and side-effect classes; Verifier pipeline (completeness, entailment,
recomputation, counter-evidence, **leave-one-source-out fragility**); Hypothesis Lab v0; report + "material relied upon"
evidence-bundle export; Agent Control Room (steps, cost, failures).

**Exit:** scripted investigation suite: task success, tool-selection accuracy, unsupported-claim rate, fragility detection,
cost per investigation — with and without the verifier (ablation A1).

## Phase 8 — Validation, research, launch (≈4–6 weeks, partly parallel from Phase 4)

- 25 customer interviews + one retrospective pilot on a closed case (MARKET_SELECTION §10); kill/pivot review.
- Research direction **E** experiments → workshop paper draft; verify all [K]-tagged references first.
- Public scorecard, datasheet for MindDoc-Synth, demo playbook with deterministic replay mode, recorded demo.
- Kafka (ADR-0003 Step B) **only if** continuous discovery creates the trigger.

## Explicitly not now

Kafka on day one, Neo4j, Temporal, Flink/Spark, Kubernetes, LLM fine-tuning, YOLO/LayoutLMv3 (licences), a swarm of
LLM agents, multi-language OCR, live MCA/GST-portal scraping, any automated "fraud" verdict.

## Summary timeline (solo, indicative)

| Weeks | 1 | 2–4 | 3–5 | 5–8 | 8–11 | 10–12 | 12–15 | 15–18 | 16–24 |
|---|---|---|---|---|---|---|---|---|---|
| Phase | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
