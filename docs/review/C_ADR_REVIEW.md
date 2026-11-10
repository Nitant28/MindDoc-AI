# C — Review of ADRs 0001–0009 (2026-11-10)

**Method.** Each ADR was checked against:
1. the current code at `ee814b0` (audit A, matrix B)
2. the new primary direction: Indian borrower fund-flow forensics, with bank-statement intelligence as the flagship
3. the hard constraints: slim install without torch, 512 MB demo host, no AGPL/GPL/non-commercial components
4. new research in this review: D (market), E (statements), G and `research/POSTGRES_INFRA_RESEARCH.md` (infra), I
   (fragility)

**Verdicts:**
- **Keep:** the decision stands as written.
- **Amend:** the decision stands, but the text needs additions or corrections.
- **Replace:** propose a successor ADR.

No ADR is silently changed by this review. Amendments are proposals for the owner to accept.

## 1. Summary

| ADR | Decision | Verdict | Main reason |
|---|---|---|---|
| 0001 | Modular monolith + worker processes | **Amend** | add an "embedded worker" mode for single-container hosts; map the target modules to today's packages |
| 0002 | PostgreSQL 18 as system of record | **Amend** | pin the version by hosting availability; spell out the RLS pattern; FTS isn't BM25; India data residency; SQLite migration path |
| 0003 | Job table + outbox, Kafka at a trigger | **Keep** (+ detail) | add a lease/retry/DLQ contract; the job row in the same transaction *is* the outbox until Kafka; build in-house |
| 0004 | Claim-centric bitemporal model | **Amend** | adopt F: observation layer, version IDs, one system-time rule, finding snapshots, case scope |
| 0005 | Graph in Postgres + NetworkX/graspologic | **Keep** (+ note) | move co-occurrence out of relationships (audit A19); keep graspologic optional |
| 0006 | Docling + PaddleOCR + Tesseract | **Amend** (significant) | the heavy stack can't be the slim default; statements need a layout-generic path, not a model-first one |
| 0007 | Own plan executor, four LLM roles | **Keep, defer** | nothing to build before Phase 6; add "LLMs never compute numbers" |
| 0008 | Primary market: borrower fund-flow forensics | **Keep as a contested hypothesis** | D: the problem is real and regulation-driven, but competitors and capped fees make it roughly level with the fallback. Decision gate after R2 |
| 0009 | Splink + human-confirmed merges | **Amend** (factual fix) | igraph is an optional extra in Splink 5, not a dependency; Splink also has a Postgres backend |

Six **new ADRs** are proposed (§3): money representation, statement extraction strategy, case scoping, deployment
topology, build profiles, and AA ingestion.

## 2. Per-ADR review

### ADR-0001 — Modular monolith + worker processes → **Amend**
- **Still right:** one codebase, an API process plus worker processes, module boundaries enforced by import rules.
  It fits a solo developer.
- **Gap 1, hosting.** A separate worker is a separate paid service on most PaaS free tiers (details in G). Add an
  **embedded worker mode**: the same container starts *k* worker threads or processes that poll the job table. The
  job-table contract is identical, so moving to a separate worker service is a config change, not a code change.
- **Gap 2, module map.** The ADR names target modules (`ingestion/`, `vision/`, `knowledge/`, `retrieval/`,
  `intelligence/`, `agents/`) that don't match today's packages (`app/api`, `ai`, `ml`, `vision`, `services`). Add a
  mapping table and a new `finance/` module (statement parsing, reconciliation, identifiers) so the flagship has a
  home.
- **Measure:** the `import-linter` contract passes in CI; a long OCR job doesn't block `/api/health` (latency test).

### ADR-0002 — PostgreSQL 18 → **Amend**
- **Still right:** one transactional store for evidence, vectors, lexical index, jobs, outbox and audit.
- **Amendments:**
  1. **Version pin by availability.** Use 18 where the host offers it. The schema must not depend on 18-only
     features without a fallback: temporal `WITHOUT OVERLAPS` → `btree_gist` exclusion constraint;
     `uuidv7()` → application-side ULID/UUIDv7. Availability is checked in G.
  2. **RLS pattern** (G §RLS): a non-owner application role, `FORCE ROW LEVEL SECURITY`, tenant set per transaction
     with `set_config('app.tenant_id', …, true)`, policies on every table, and a per-table cross-tenant test.
  3. **Lexical search.** Built-in FTS ranking (`ts_rank_cd`) is not BM25. Every BM25 extension found is AGPL
     (ParadeDB `pg_search`), AGPL/ELv2 (VectorChord-bm25) or self-host-only (pg_textsearch needs
     `shared_preload_libraries`) [verified]. Keep the in-process BM25 over case-scoped chunks as the reference for
     ablation R1.
  4. **Vector index.** One HNSW index shared across tenants hurts per-tenant recall (pgvector README) [verified]. Use
     exact scans for small cases, and partial indexes per tenant or iterative scans for large ones.
  5. **Data residency and hosting reality** (verified 2026-11-10, see G):
     - Render offers PG18 (now the default) with pgvector and `btree_gist`, but it has **no India region**, and free
       databases **expire after 30 days with no backups**.
     - Neon has no India region either.
     - Supabase has Mumbai, but its images are on 15.x/17.x, not 18.
     - Aiven and AWS RDS offer PG18 in Mumbai and Hyderabad.

     The ADR should therefore separate demo hosting from pilot hosting (proposed ADR-0013) and require
     pgvector ≥ 0.8.3 (HNSW build and vacuum fixes).
  6. **Migration path** from SQLite: Alembic baseline; copy script with JSON-text → JSONB and vectors JSON → pgvector;
     dual-run tests in CI with a Postgres service.
- **Splink note:** Splink 5 ships a `postgres` extra, so entity resolution can run inside the same database instead
  of DuckDB (to evaluate in Phase 4).

### ADR-0003 — Job table + transactional outbox; Kafka at a trigger → **Keep**, add a contract
- Add a **job contract**:

  | Rule | Detail |
  |---|---|
  | Job identity | `job(id, kind, idempotency_key UNIQUE, payload, state {queued\|running\|succeeded\|failed\|dead}, attempts, max_attempts, run_after, lease_until, last_error)` |
  | Claiming | `FOR UPDATE SKIP LOCKED` with a lease |
  | Retries | exponential backoff; DLQ after `max_attempts` |
  | Wake-up | `LISTEN/NOTIFY` (polling fallback) |
  | Idempotency | handlers keyed by deterministic IDs |

- **Build vs adopt:** G compared Procrastinate (MIT, 3.10.0), PGQueuer (MIT, 2.0.0 released the day before the
  check), oban-py (Apache-2.0, pre-1.0), pgmq (PostgreSQL licence) and Hatchet (MIT, a separate engine). Decision:
  a thin in-house job table, with Procrastinate as the fallback.
- **Simplification:** while every consumer is a job in the same database, inserting the job row in the business
  transaction *is* the transactional outbox. The outbox → dispatcher → job hop in the ADR is only needed at step B
  (Kafka). Amend the ADR text accordingly.
- **Kafka trigger:** unchanged (≥ 3 independent consumer groups needing replay, or > ~200 events/s sustained).

### ADR-0004 — Claim-centric, bitemporal evidence model → **Amend** (adopt F)
- Add:
  1. a **financial observation layer** (`statement`, `statement_txn`, `statement_cell`, `bank_account`,
     `reconciliation_check`): transactions are observations, and claims are built from them
  2. **logical key + version id**, with evidence, reviews and findings referencing versions
  3. **one system-time rule**: `sys_period`, close-and-insert only
  4. **finding snapshots** and frozen reports
  5. **case scope** and `tenant_id` on every row
  6. **source clusters** for independence
  7. **governance fields**
- Acceptance tests: F §11.

### ADR-0005 — Graph in Postgres + NetworkX/graspologic → **Keep**
- The licence reasoning still holds: Neo4j Community, igraph and leidenalg are GPL.
- **Add:** co-occurrence moves to a `co_mention` table and is styled as a weak signal (fixes A19).
- **Add:** graspologic is heavy (scientific stack). Keep it in the optional ML profile and run community detection
  only on case-scoped graphs.
- No change to the AGE upgrade path.

### ADR-0006 — Docling + PaddleOCR + Tesseract → **Amend (significant)**
- **Still right:** remove PyMuPDF (AGPL) from the default build; keep licence-clean models only; gate swaps on
  benchmark results.
- **Problem 1: weight.** Confirmed in `research/BANK_STATEMENT_RESEARCH.md`: Docling's models need torch (via
  `docling-ibm-models`), and PaddleOCR needs PaddlePaddle. Neither fits the "slim, no torch, 512 MB" profile, so as
  written the ADR would make the default build heavy. The torch-free alternatives:
  - **RapidOCR** (Apache-2.0, verified): PP-OCR models on ONNX Runtime.
  - **img2table** and **RapidTable** (SLANet+) for tables.
  - **Camelot 2.0** (MIT; torch only in an optional extra).
- **Exclusions:**
  - OCRmyPDF (MPL-2.0) pulls in Ghostscript (AGPL, to confirm), so it stays out of the shipped image.
  - Surya/Marker weights remain excluded.
- **Problem 2: wrong default for statements.** Most bank e-statements have a text layer. For them, word boxes plus
  layout-generic column detection plus balance validation (E) is more accurate, explainable and cheaper than a
  layout model. Models matter for scans.
- **Amended decision, two tiers:**

  | Tier | Components |
  |---|---|
  | **Slim (default)** | pypdfium2 for rendering and highlights; pdfplumber/pdfminer for text and word boxes; OpenCV preprocessing; Tesseract OCR; MindDoc's layout-generic statement extractor |
  | **ML (optional)** | Docling (conversion, TableFormer); PaddleOCR-VL (Apache-2.0 weights); chosen per benchmark. RapidOCR (ONNX, no torch or paddle) can sit in the **slim** tier if it beats Tesseract on StatementBench |

  Gate: statement-benchmark metrics (H) ≥ the slim baseline before an ML component becomes default for any document
  class.
- **Sequencing:** replace the PyMuPDF highlighter and renderer first (smallest blast radius), then text extraction.

### ADR-0007 — Own typed plan executor, four LLM roles → **Keep, defer**
- Nothing in Phases 1–5 needs it.
- **Add a rule:** LLM roles never compute or alter numbers. Every amount, total, balance or date interval in a
  finding comes from a deterministic tool, with its inputs recorded. The Verifier role checks prose against claims;
  the reconciliation engine checks numbers.
- **Add:** every tool in the registry declares whether it's deterministic. Leave-one-source-out (I) re-runs only
  deterministic stages by default, and LLM stages under fixed seeds and prompts.

### ADR-0008 — Primary market → **Keep as a hypothesis; now contested** (evidence in D)
D's verdict is **inconclusive and commercially weaker than the strategy docs assumed**. Rescored on verified
evidence, the primary market falls to about 3.70–3.85, roughly level with the procure-to-pay fallback (3.70).

- **Stronger than assumed: the problem** (all [verified] in D).
  - RBI's 2026 directions keep a 180-day, notice-and-reasoned-order process for red-flagged accounts.
  - The 2024 wilful-defaulter direction defines diversion and siphoning, and says lenders "shall consider" a forensic
    audit.
  - The Supreme Court in *Amit Iron* (2026) made giving the forensic report to the borrower mandatory, with only
    third-party material withheld.

  Evidence-grade, shareable, redactable findings are exactly what the regulation rewards.
- **Weaker than assumed: the business.**
  - RBI's operative text asks for "an external audit or an internal audit", so outsourced forensic firms aren't the
    only buyer.
  - Competitors already flag round-tripping and related parties: IDfy's Transaction Intelligence Platform and Cygnet
    Finalyze [verified], plus iAcuity, CypherSOL and Valid8.
  - The only published fee schedule found caps a forensic audit at about ₹80,000 for accounts up to ₹50 crore
    [unverified].
- **Account Aggregator** only delivers data to regulated institutions, so CA and forensic firms can't use it. PDFs
  stay central for them [verified]. Lenders themselves can use AA, so both inputs matter (ADR-0015).
- **Amendments:**
  1. Status stays *Proposed*, with a **market decision gate after R2** (J).
  2. The differentiator is restated as *traceable, reconciled, reviewable and redactable evidence*, not anomaly
     detection.
  3. The buyer list adds bank internal-audit and FRM units.
  4. Citations move from the 2024 directions to the 2026 consolidated ones.

### ADR-0009 — Splink + human-confirmed merges → **Amend (factual)**
- **Correction:** Splink 5.0.0 (MIT) has no hard dependency on igraph; `igraph` is the optional `splink[igraph]`
  extra, used by edge and graph-metric helpers. (Checked 2026-11-10 against the wheel metadata of
  `splink-5.0.0-py3-none-any.whl`.) Install core Splink without that extra; confirm in a spike that clustering at a
  threshold works without igraph.
- **Add:** identifier validation (GSTIN check character, PAN structure, IFSC format, CIN structure) runs *before*
  any identifier can drive a merge. Validation rules and their sources go in E.
- **Add:** UPI VPA and account + IFSC pairs as strong identifiers for counterparties found in statements.

## 3. Proposed new ADRs

| ADR | Title | Decision (short) | Why now |
|---|---|---|---|
| 0010 | Money and numeric representation | Integer paise (`BIGINT`) + currency in the database; `int`/`Decimal` in Python; raw text kept beside every value; no floats anywhere in the financial path (lint + CI grep) | Reconciliation correctness (A14) |
| 0011 | Bank-statement extraction strategy | A layout-generic extractor (word boxes → column roles → row segmentation) validated by the balance constraint; bank templates only as optional, data-driven overrides; never edit values to force reconciliation | Flagship capability (E) |
| 0012 | Case (engagement) scoping | Sources, graphs, findings and reports are case-scoped; case roles; tenant = organisation | Forensic workflow and access control (F §2.1) |
| 0013 | Deployment topology and environments | Demo: one container with an embedded worker. Pilot: managed Postgres in an India region + a separate worker | Free-tier limits, data residency (G) |
| 0014 | Build profiles | `slim` (default, no torch, ≤ 512 MB) and `ml` (optional models); every new component declares its profile; CI builds and boots both | Keeps the low-memory path alive (constraint) |
| 0015 | Account Aggregator ingestion | Accept ReBIT FI JSON (deposit accounts) as an input mapped to the same `statement`/`statement_txn` model; no PDF needed when AA data exists | Market reality (D, E) |

Each new ADR is written in full only after the owner accepts this review.

## 4. Cross-cutting observations

- The ADRs are internally consistent. The one tension is **ADR-0006 vs the slim-profile constraint**, resolved by
  ADR-0014.
- None of the ADRs over-engineers, and the "explicitly not now" list (Kafka, Neo4j, Temporal, agent swarms) holds up.
  No fashionable replacement is recommended.
- The biggest missing piece wasn't architecture but the **financial domain model** (ADR-0010/0011 and F). Without
  it, the evidence model has nothing precise to hold.
