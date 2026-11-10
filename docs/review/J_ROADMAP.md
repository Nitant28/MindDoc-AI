# J — Revised roadmap: dependencies and acceptance criteria

**Supersedes the ordering in** `docs/IMPLEMENTATION_BACKLOG.md` (its content and phase numbers stay valid as a
catalogue). This roadmap re-orders work around the decided flagship — bank-statement intelligence — on top of the
evidence foundation, as the owner's brief requires: foundation first, flagship second, no flashy agents early.

Estimates are for one engineer, full-time-equivalent, and are planning guesses. Every milestone ships behind tests,
keeps the slim profile working, and updates PROJECT_CONTEXT + the capability matrix (B).

## 1. Dependency graph

```
R0 Decide & secure ─┬─> R1 Measure (StatementBench v0, HB v1 plan, interviews start) ─────────────┐
                    └─> R2 Evidence foundation (Postgres, Alembic, RLS, jobs, async ingestion) ─┐ │
                                                                                                 v v
                                          R3 Statement engine v1 (text-layer, reconciliation, AA) ──> R4 Scans + identifiers
                                                                                                         │
                         R6 Verifier round 2 + calibration (parallel) <──────── R5 Claims + entities + case graph
                                                                                                         │
                                                                         R7 Forensic discovery (D1–D7, ledger)
                                                                                                         │
                                                       R8 Investigation + fragility + evidence-bundle reports
R9 Market validation runs alongside from R0 (interviews) and gates the domain work:
   GATE M1 (end of R2, ≈ week 6): ≥ 15 interviews analysed → confirm lender forensics, switch to procure-to-pay,
   or narrow the buyer (e.g. bank internal audit / FRM units). R0–R2 are market-agnostic, so nothing is wasted.
   GATE M2 (before R7): retrospective pilot result → kill / pivot / continue.
```

**Why a gate** (from D): the problem is real and regulation-driven, but competitors already flag round-tripping and
related parties, and published fees are capped. Rescored, the primary market is roughly level with the fallback.
- The evidence foundation (R2) serves both markets.
- The statement engine (R3) is lower-regret than it looks: procure-to-pay integrity also reconciles payments against
  bank statements.
- Forensic-specific detectors (R7) wait for M1 and M2.

## 2. Milestones

### R0 — Decide and secure (≈ 1 week)
| | |
|---|---|
| Why | Review deliverables need owner acceptance before code changes; open exposures must close first |
| Scope | Owner accepts or edits C (ADR verdicts); write ADR-0010…0015 in full; set strong `JWT_SECRET` + CORS on Render; make the repo private **or** file the GitHub Support request for `refs/pull/1/*` (audit A1); commit the review docs; **book the first interviews** (D §7) so gate M1 has data by week 6 |
| Interacts with code | none (docs + settings) |
| Cost | 2–4 days |
| Acceptance | ADRs merged with status Accepted/Rejected; anonymous request for old commit `6f4a21b` content returns 404; live token check with default secret still 401 |
| Risk | delay; mitigated by time-boxing to one week |

### R1 — Measure first (≈ 1–2 weeks, overlaps R2)
| | |
|---|---|
| Why | No flagship work without a benchmark (H); the market is unvalidated (D) |
| Scope | StatementBench **SB-Synth v0** generator (≥ 4 layout families, text-layer + 3 degradation levels), gold labels, metrics runner; **baseline of the current parser** on SB; HB v1 annotation guideline + recruit two independent annotators; start interviews (10 of 25) per D |
| Interacts with code | new `benchmarks/statements/`; no app changes |
| Cost | ≈ 8–10 days |
| Acceptance | SB report committed for the current code (expected to be poor) with intervals; datasheet; 10 interview notes stored (outside git if they contain personal data) |
| Risk | synthetic layouts too clean → mitigated by held-out layout families and degradation; recruiting delays |

### R2 — Evidence foundation (≈ 3–4 weeks) — ADR-0001/0002/0003/0004/0012/0013/0014, design in G and F
| | |
|---|---|
| Why | Fixes audit A9–A13 (SQLite, no migrations, no persistence, synchronous ingestion, process-local index); everything later needs durable, versioned evidence |
| Scope | Postgres (version per G) + pgvector + Alembic baseline; tables `tenant, case, case_member, source, page, region, chunk, embedding, job, outbox, audit_event`; RLS with a non-owner role; content-addressed blob store (local FS); job table + outbox + embedded-worker mode; async ingestion with lifecycle states and progress API; SQLite → Postgres migration script; CI on a Postgres service; current endpoints keep working (compatibility layer) |
| Interacts with code | replaces `app/database/models.py` auto-migrator, `ingestion.py` call path, `retrieval.py` index source; API contracts unchanged except upload returning a job/lifecycle |
| Cost | ≈ 15–20 days |
| Acceptance | upload returns < 1 s; a 30-page PDF completes in the worker; killing the worker mid-document and restarting resumes with **no duplicate rows** (idempotency test); RLS cross-tenant test per table passes; retrieval results on HB/RB within ±1 point of the SQLite version; migration of a seeded SQLite DB is lossless (row counts + checksums); slim image still ≤ 512 MB at runtime |
| Risk | migration bugs, RLS misconfiguration (owner bypass), hosting cost; mitigated by dual-run tests, non-owner role, the demo/pilot split in ADR-0013 |

### R3 — Statement engine v1: text-layer + reconciliation + AA (≈ 3–4 weeks) — ADR-0010/0011/0015, design in E
| | |
|---|---|
| Why | The flagship; fixes A14–A15 (no money type, no transaction model) |
| Scope | Money type (paise) everywhere in `finance/`; `statement, statement_txn, statement_cell, bank_account, reconciliation_check` (F §2.3); layout-generic extractor on word boxes (pypdfium2/pdfplumber); deterministic reconciliation engine (row, page, statement, cross-statement continuity) with explicit reason codes; **review UI** listing failing checks with original values, expected vs observed balance, difference, page + bbox highlight; AA JSON (ReBIT deposit) importer mapped to the same tables; replace the PyMuPDF highlighter with pypdfium2 |
| Interacts with code | new `app/finance/`; ingestion routes statement-classified documents to it; Document page gains a "Transactions" tab; chat retrieval unchanged |
| Cost | ≈ 15–20 days |
| Acceptance | SB text-layer held-out layouts: row F1 ≥ 0.99, amount/direction ≥ 0.995, reconciliation rate ≥ 0.98, **false alarms = 0**; error localisation ≥ 0.9 on injected single-row errors; no float in `finance/` (CI grep); AA sample files import and reconcile; every failing check shows page + bbox |
| Risk | real layouts differ from synthetic → SB-Real tier and pilot data in R9; multi-line narration segmentation errors → measured separately |

### R4 — Scanned statements + identifiers (≈ 3 weeks)
| | |
|---|---|
| Why | Fixes A16 (no word boxes for scans) and A20 (no identifier validation); scans are common in forensic engagements |
| Scope | Tesseract word boxes (TSV) → same extractor; OCR-confidence-aware review flags; identifier extraction + validation (IFSC, GSTIN, PAN, CIN, DIN, UPI VPA, UTR) from narrations and documents; counterparty normalisation; optional ML-profile OCR evaluated on SB/DB per ADR-0006 amended |
| Cost | ≈ 12–15 days |
| Acceptance | SB scanned (moderate): row F1 ≥ 0.95 and silent-error rate ≤ 0.5% of rows; validators pass published test vectors 100%; ML-profile component adopted only if it beats slim on SB/DB by a pre-registered margin |
| Risk | OCR quality on poor scans → explicit "not reconcilable, needs review" outcomes rather than guesses |

### R5 — Claims, entity resolution, case graph (≈ 3–4 weeks) — ADR-0004/0005/0009
| | |
|---|---|
| Why | Fund-flow reasoning needs resolved identities and claims with evidence; fixes A19/A20 |
| Scope | claim + evidence for transfers built from `statement_txn`; `entity`, `entity_identifier`, `identity_event`, `entity_canonical`; Splink (core, no igraph extra) with cannot-link on conflicting identifiers; review queue for merges; reversible merge/unmerge; co-mentions moved out of relationships; case-scoped graph view with evidence on every edge |
| Cost | ≈ 15–20 days |
| Acceptance | EB: high-risk wrong merges = 0, pairwise precision ≥ 0.98 / recall ≥ 0.90 at the auto band; F §11 property tests (as-of stability across merge/unmerge) pass; every graph edge opens its evidence |
| Risk | over-merging → conservative bands + human review |

### R6 — Verifier round 2 + calibration (≈ 2 weeks, parallel with R5)
| | |
|---|---|
| Why | Verifier gaps from the held-out test (PROJECT_CONTEXT §9); uncalibrated score (A18) |
| Scope | recomputation engine (percentages, from→to arithmetic, totals) using the finance tools; fixes for converse verbs, local passive, "declined", possessive spans; table-column semantics; HB v1 independent test; CB calibration |
| Cost | ≈ 8–10 days |
| Acceptance | HB v1 test: red-tier catch ≥ v0 result and false flags ≤ 10% with intervals reported; ECE ≤ 0.1 before any probability is displayed |
| Risk | overfitting again → independent annotators, one-shot test scoring |

### R7 — Forensic discovery (≈ 3 weeks) — INVESTIGATION_ENGINE §5
| | |
|---|---|
| Why | The product's analytical value; depends on reconciled transactions + resolved entities |
| Scope | deterministic detectors D1–D7 over transactions (e.g. round-tripping, related-party diversion, circular flows, structuring, end-use deviation vs sanction terms); explainable anomaly signals; Discovery Ledger with dispositions; never "fraud" labels |
| Cost | ≈ 15 days |
| Acceptance | FB: seeded-scheme recall ≥ 0.9 with ≤ 1 false flag per 10 benign look-alikes; every discovery lists its transactions and evidence |
| Risk | benign look-alikes flagged → measured explicitly; thresholds per case |

### R8 — Evidence-constrained investigation + fragility (≈ 3–4 weeks) — ADR-0007, proposal I
| | |
|---|---|
| Why | Turn discoveries into reviewable findings and reports that survive challenge |
| Scope | minimal plan executor (four roles, deterministic tools, LLM never computes numbers); findings with claim-version snapshots; LOSO fragility per finding; frozen reports with evidence bundle ("material relied upon"); **report redaction of third-party personal data** (required: under *Amit Iron* (2026) the report goes to the borrower with third-party parts withheld, see D; fixes audit A4) |
| Cost | ≈ 15–20 days |
| Acceptance | per I's experimental design; report → finding → claim → region in ≤ 2 clicks; fragility computed for every finding in FB cases |
| Risk | compute cost of re-runs → incremental recomputation of deterministic stages |

### R9 — Market validation and launch (continuous, from R0)
| | |
|---|---|
| Scope | 25 interviews (D §7), including bank internal-audit and FRM units, not only forensic firms; gate M1 after ≥ 15 interviews; one retrospective pilot on a closed engagement (redacted or partner-hosted); gate M2 before R7; public scorecard; paper draft for direction E only if I's experiment clears its kill criteria |
| Acceptance | D's pass/fail thresholds; pilot KPIs (time to partner-reviewed draft, recall vs final report, 100% traceability, 0 numeric mismatches) |

## 3. Timeline (indicative, solo)

| Weeks | 1 | 2–3 | 3–6 | 7–10 | 10–13 | 13–16 | 14–16 | 17–19 | 20–23 | ongoing |
|---|---|---|---|---|---|---|---|---|---|---|
| Milestone | R0 | R1 | R2 | R3 | R4 | R5 | R6 | R7 | R8 | R9 |

## 4. What is deliberately not scheduled
Kafka, Neo4j, Temporal, Flink/Spark, Kubernetes, fine-tuning, YOLO/LayoutLMv3, agent swarms, government-portal
scraping, automated fraud verdicts, a 3-D/marketing landing page. Any of these needs a measured trigger and a new ADR.
