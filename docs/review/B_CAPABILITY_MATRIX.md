# B — Capability matrix (commit `ee814b0`, 2026-11-10)

**Statuses**

| Status | Meaning |
|---|---|
| **BUILT** | implemented, covered by automated tests, running live |
| **EXPERIMENTAL** | implemented, but its quality is unmeasured or measured as weak; must not be marketed as reliable |
| **IN PROGRESS** | partly implemented |
| **PLANNED** | designed in docs/ADRs, no code |
| **NOT DONE** | known gap with no design yet |

"Quality" below means a measured accuracy figure. Unit tests prove the code runs as written, not that its output is
good.

## 1. Platform and security

| Capability | Status | Where | Validation |
|---|---|---|---|
| Register / login, PBKDF2-310k, JWT HS256, insecure-secret rejection | BUILT | `app/core/security.py`, `app/api/auth.py` | tests; live forged-token check |
| Per-user tenant isolation on every query path | BUILT | `app/api/*`, `rag.run` | cross-tenant tests |
| Upload caps (size, pages, pixels, DOCX inflation), extension allow-list, duplicate detection | BUILT | `document_service.py`, `documents.py` | `test_hardening.py` |
| Per-user rate limits (upload, query, eval), auth limit per IP | BUILT (single process only) | `security.py`, `deps.py` | tests |
| Query audit log (provider, model, latency, prompt hash, chunk IDs) | BUILT | `QueryLog` | API tests |
| PII detection (Luhn-checked cards, PAN, Aadhaar, IBAN …) | BUILT | `guardrails.py` | unit tests; no precision/recall measured |
| PII redaction | NOT DONE | `redact()` exists but nothing calls it | — |
| Prompt-injection detection and context sanitising | EXPERIMENTAL | `guardrails.py` | pattern tests only; no attack-set evaluation |
| RBAC, case-level access, SSO, token revocation | NOT DONE | — | — |
| Hash-chained audit events, reviewer action log | PLANNED | `DATA_MODEL.md` §7 | — |
| Row-level security | PLANNED | ADR-0002 | — |

## 2. Storage, processing, operations

| Capability | Status | Where | Validation |
|---|---|---|---|
| SQLite store with startup column auto-add | BUILT | `models.py` | tests |
| PostgreSQL + pgvector + Alembic | PLANNED | ADR-0002 | — |
| Synchronous ingestion pipeline | BUILT | `ingestion.py` | API tests |
| Job table + outbox + workers, async ingestion, DLQ, progress | PLANNED | ADR-0001, ADR-0003 | — |
| Content-addressed blob store | PLANNED | backlog 1.3 | — |
| Docker (slim / ML), Render blueprint, CI (backend, frontend, Docker 512 MB smoke) | BUILT | `Dockerfile`, `render.yaml`, `ci.yml` | CI green on `ee814b0` |
| Persistent storage, backups, monitoring on the live site | NOT DONE | free plan | — |

## 3. Document intelligence (computer vision and parsing)

| Capability | Status | Where | Validation |
|---|---|---|---|
| PDF text layer + `find_tables` → Markdown; pdfplumber fallback; DOCX; images; text | BUILT | `document_service.py` | tests |
| Per-page scan quality (Laplacian blur, brightness, contrast) | BUILT | `cv.py` | unit test; thresholds not validated |
| Denoise, CLAHE, Otsu/adaptive threshold, deskew | BUILT | `cv.py` | unit test |
| Morphological layout detection (text / table / figure) | EXPERIMENTAL | `cv.py` | no layout accuracy measured |
| OCR (Tesseract, EasyOCR fallback) with confidence | EXPERIMENTAL | `cv.py` | no CER/WER measured |
| Vision-LLM captions | EXPERIMENTAL | `cv.caption_image` | not evaluated |
| Pixel highlight of cited passage | BUILT for text-layer PDFs; NOT DONE for scans | `highlight.py` | API test |
| Region bounding boxes stored per value | PLANNED | `DATA_MODEL.md` §3 | — |
| Docling / PaddleOCR stack; PyMuPDF (AGPL) removed | PLANNED | ADR-0006 | — |
| Table cells with normalised values | PLANNED | backlog Phase 3 | — |

## 4. Retrieval and machine learning

| Capability | Status | Where | Validation |
|---|---|---|---|
| Page-aware chunking (900/150) | BUILT | `insights.chunk_pages` | tests |
| MiniLM embeddings + offline hashing fallback, model-tagged vectors | BUILT | `embeddings.py` | tests (CI requires the model) |
| BM25 + dense → RRF, cross-encoder rerank, MMR | BUILT | `retrieval.py`, `rag.py` | unit tests; no stored retrieval baseline |
| Self-supervised retrieval eval (Hit@5, MRR, ablation) | BUILT | `evaluation.py`, `/intel/eval` | runs; pseudo-queries are biased toward lexical match (known) |
| Zero-shot document-type classification | EXPERIMENTAL | `insights.py` | unit test; accuracy unmeasured |
| Keyphrases, extractive summary, readability, K-Means + c-TF-IDF topics | EXPERIMENTAL | `insights.py` | unit tests; quality unmeasured |

## 5. Generative AI and reasoning

| Capability | Status | Where | Validation |
|---|---|---|---|
| LLM gateway: 7 providers, order, 60 s circuit breaker, streaming, JSON repair | BUILT | `llm.py` | unit test (OpenRouter wiring); live |
| Cited RAG answers, streaming over SSE, extractive no-LLM fallback | BUILT | `rag.py`, `chat.py` | API tests |
| Deep mode: rewrite, sub-questions, HyDE | EXPERIMENTAL | `rag._plan` | benefit unmeasured |
| GraphRAG-lite expansion | EXPERIMENTAL | `knowledge.entity_linked_chunks` | benefit unmeasured |
| **Claim verifier v2, value checks** (red) | BUILT | `verifier.py` | held-out: 68% caught, 11% wrongly flagged (n=72, synthetic) |
| Claim verifier v2, wording heuristics (amber) | EXPERIMENTAL | `verifier.py` | held-out: +12 catches, +9 false flags |
| NLI layer (LettuceDetect tiny) | EXPERIMENTAL (off) | `verifier.py` | no gain on held-out |
| LLM-as-judge (deep mode) | EXPERIMENTAL | `rag._verify` | not evaluated |
| Evidence score | EXPERIMENTAL (uncalibrated) | `rag._confidence` | no calibration data |
| Abstention | BUILT | `rag.run` | API test; thresholds not validated |
| Recomputation of derived numbers (percentages, from→to) | IN PROGRESS | sums, differences and date intervals only | partial |
| Knowledge graph: rule-based + LLM entities and relations; timeline | EXPERIMENTAL | `knowledge.py` | unit tests; extraction precision/recall unmeasured; co-occurrence shown as edges (A19) |
| Structured field extraction | EXPERIMENTAL | `extraction.py` | API test (keys returned); accuracy unmeasured |
| Hallucination benchmark v0 (146 claims) | IN PROGRESS | `benchmarks/hallucination` | needs an independent set |

## 6. Target-market capabilities (Indian borrower fund-flow forensics)

| Capability | Status | Where |
|---|---|---|
| Bank-statement parser (rows, dates, debit/credit, balance, narration, references) | PLANNED → designed in `E_BANK_STATEMENT_DESIGN.md` | backlog 3.3 |
| Running-balance reconciliation | PLANNED → designed in E | `DATA_MODEL.md` §6 integrity rule |
| Money as exact paise; transaction and account model | NOT DONE → designed in F | — |
| Account Aggregator (ReBIT JSON) ingestion | NOT DONE → proposed in E | — |
| Identifier validation (GSTIN, PAN, CIN, DIN, IFSC) | PLANNED | ADR-0009 |
| Splink entity resolution, reversible human merges | PLANNED | ADR-0009 |
| Claim-centric bitemporal evidence model | PLANNED → reviewed in F | ADR-0004 |
| Tally/ledger, GST-summary parsers | PLANNED | backlog 3.3 |
| Forensic detectors D1–D7, discovery ledger | PLANNED | `INVESTIGATION_ENGINE.md` |
| Plan executor (Planner, Extractor, Verifier, Writer) | PLANNED | ADR-0007 |
| Leave-one-source-out fragility | PLANNED → proposal in `I_FRAGILITY_RESEARCH_PROPOSAL.md` | research direction E |
| Report and evidence-bundle export, graph explorer | PLANNED | backlog Phases 4 and 7 |
| MindDoc-Synth generator, DocBench-50, statement benchmark | PLANNED → strategy in `H_BENCHMARK_STRATEGY.md` | backlog Phase 2 |
| Customer validation (25 interviews, retrospective pilot) | NOT DONE → plan in `D_MARKET_RESEARCH.md` | backlog Phase 8 |

## 7. Reading the matrix

- The general document-AI product is BUILT, but much of its intelligence is EXPERIMENTAL: it runs, but its quality
  hasn't been measured.
- **Every capability that defines the target product is PLANNED or NOT DONE.** The honest pitch today is "a
  measured, glass-box document-QA base with a verified claim checker, about to gain a financial evidence layer", not
  "a forensic platform".
- Promotion rule: EXPERIMENTAL → BUILT needs a stored benchmark result with confidence intervals and a regression
  test. PLANNED → IN PROGRESS needs merged code behind a setting; → BUILT needs its acceptance criteria in
  `J_ROADMAP.md` met.
