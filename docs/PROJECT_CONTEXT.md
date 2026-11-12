# MindDoc AI — complete project context (for humans and AI assistants)

> **Read this first if you are an AI assistant helping on this project.**
> - Every capability below is labelled **BUILT** (in the code, tested, live), **PLANNED** (designed in docs/ADRs,
>   not implemented) or **NOT DONE** (known gap).
> - Do not describe a PLANNED item as existing, and do not invent metrics. The only measured numbers are in §9.
> - When proposing work, follow the rules in §14 and the order in §13.
> - Snapshot date: **2026-11-10**. Code version **2.1.0**. Commit `ee814b0` on `main`.

---

## 1. What MindDoc is, in one paragraph

MindDoc AI is a **glass-box document intelligence** web app.
- **Upload:** PDFs (digital or scanned), Word files, images and text.
- **Read:** it extracts text with a computer-vision and OCR pipeline, analyses each document with classical ML and
  embeddings, and builds a knowledge graph of entities and relations.
- **Answer:** questions get cited answers through a hybrid retrieval-augmented generation (RAG) pipeline.
- **Check:** every answer sentence is checked against the passage it cites, the full reasoning trace is shown, and
  citations can be opened as highlighted regions on the original PDF page.
- **Run anywhere:** it works with seven LLM providers or **fully offline** (no LLM: extractive answers).

The **target product** (PLANNED) is narrower and deeper: forensic review of a borrower's fund flows for lenders in
India, built on a claim-centric evidence graph (§12).

- **Live:** https://minddoc-ai-2.onrender.com (Render, free plan, Docker)
- **Repo:** https://github.com/Nitant28/MindDoc-AI (public). The `main` branch is deployed; `consolidate/v2-base`
  is the working branch.

---

## 2. Technology stack (BUILT)

| Layer | Technology |
|---|---|
| Backend | Python 3.11, FastAPI, Uvicorn, SQLAlchemy 2, Pydantic Settings, python-jose (JWT), httpx |
| Database | SQLite (WAL) by default; any SQLAlchemy URL. Schema is created and extended automatically on start; no Alembic yet |
| Search index | in-memory NumPy index per workspace (dense vectors + BM25), rebuilt lazily from the DB |
| Document parsing | PyMuPDF (AGPL-3.0, to be replaced), pdfplumber (fallback), python-docx, Pillow |
| Computer vision | OpenCV (headless), Tesseract via pytesseract, EasyOCR (optional ML extra) |
| ML | NumPy, scikit-learn (TF-IDF, K-Means), sentence-transformers (optional): `all-MiniLM-L6-v2` embeddings and the `ms-marco-MiniLM-L-6-v2` cross-encoder |
| LLMs | one plain-HTTP gateway for Anthropic, OpenAI (and compatible), OpenRouter, Gemini, NVIDIA NIM, DeepSeek, Ollama |
| Frontend | React 18, TypeScript, Vite 7, Tailwind CSS 3, React Router 6, axios. A dependency-free canvas force graph |
| Packaging | multi-stage Dockerfile (Node 20 builds the UI; Python 3.11-slim with Tesseract runs it; non-root user) |
| Deploy | Render blueprint `render.yaml` (Docker, free plan, health check `/api/health`) |
| CI | GitHub Actions: backend tests, frontend lint and build, and a Docker job that builds the image, boots it with 512 MB and runs a smoke test |

There are two install profiles:
- `requirements.txt` is slim: no torch. It fits Render's 512 MB, and embeddings fall back to hashing.
- `requirements-ml.txt` adds sentence-transformers and EasyOCR.
- In Docker: `--build-arg INSTALL_ML=true`.

---

## 3. Architecture of the current code (BUILT)

```
React SPA ──HTTP/SSE──> FastAPI  /api/auth · /api/documents · /api/chat · /api/intel · /api/vision
                           │
     upload ──> ingestion: parse (text layer or CV+OCR per page) → chunk → embed → classify · keywords ·
                summary · PII · injection scan → store → entity/relation extraction → invalidate index
     question ─> rag.run: [plan] → hybrid retrieve (BM25 + dense → RRF) → GraphRAG-lite expansion →
                cross-encoder rerank → MMR → cited generation (stream) → claim verifier v2 → evidence score
                → abstention → persist message + query log
                           │
        LLM gateway (7 providers, circuit breaker)      SQLite: documents, chunks+vectors, entities,
                                                        relations, sessions, messages, query_logs
```

The backend is a **modular monolith**: one process, in which ingestion runs synchronously inside the upload
request.

Module map:
- `app/api/*` contains the routes.
- `app/services/*` handles parsing and ingestion.
- `app/vision/*` holds the CV pipeline and the PDF highlighter.
- `app/ml/*` holds embeddings, retrieval, insights and evaluation.
- `app/ai/*` holds the LLM gateway, RAG, claim verifier, knowledge graph, extraction and guardrails.
- `app/database/models.py` holds the tables.
- `app/core/*` holds config and security.

---

## 4. Concepts used, and exactly where (BUILT)

### 4.1 Computer vision and OCR — `app/vision/cv.py`, `app/services/document_service.py`

**Quality gating.** Blur is measured as the variance of the Laplacian, with brightness (mean) and contrast
(standard deviation). The page score is 0.5·sharpness + 0.25·exposure + 0.25·contrast, labelled good, fair or
poor.

**Preprocessing for OCR.**
- Non-local-means denoising (`fastNlMeansDenoising`).
- CLAHE contrast equalisation.
- Otsu and adaptive Gaussian thresholding.
- Deskew: the angle comes from `minAreaRect` over ink pixels, then the page is rotated.

**Layout detection, done without deep learning.**
- Long horizontal and vertical morphological kernels find table grid lines, and line intersections confirm a
  table.
- Dilation merges words into text blocks, and contours give region boxes.
- A block covering more than 4% of the page that is densely inked or tonally rich (photo-like mid-grey pixels) is
  classed as a figure.
- Blocks are sorted into reading order and drawn on the image for the Vision Lab.

**OCR.** Engines are tried in order (`OCR_ENGINE_ORDER`): Tesseract (`--oem 3 --psm 3`) first, then EasyOCR
(CRAFT detector + CRNN recogniser). Each page gets a mean word confidence and a word count. EasyOCR is detected
with `find_spec` and loaded lazily, so it doesn't slow startup.

**Per-page routing for PDFs.**
- A page with a usable text layer uses it, and PyMuPDF `find_tables()` turns its tables into Markdown.
- Otherwise the page is rendered and sent through CV + OCR. Render zoom is capped by `MAX_IMAGE_PIXELS`.
- pdfplumber is the fallback parser.

**Vision-LLM captions.** Figures and photos get a description from a multimodal LLM when one is configured.

**Pixel-level provenance** (`app/vision/highlight.py`). The cited passage is located on the PDF page with PyMuPDF
text search, and the page is rendered with highlight boxes (`GET /api/documents/{id}/page/{n}/image`, header
`X-Highlight-Boxes`). Limitation: this only works for PDFs with a text layer. Scanned pages have no word boxes
stored yet.

### 4.2 Machine learning and retrieval — `app/ml/*`

**Chunking.** Chunks are about 900 characters with 150 characters of overlap, split on paragraph and sentence
boundaries, and never cross a page, so citations are page-exact.

**Embeddings.**
- MiniLM-L6-v2 gives 384-dimension, L2-normalised vectors.
- The **offline fallback** is a deterministic feature-hashing embedder over word unigrams, bigrams and character
  trigrams.
- Each vector records the model that made it, so incompatible vectors are never compared.
- Models load from the local cache only; a missing model downloads in the background, so requests never block on
  the network.

**BM25** uses k1 = 1.5 and b = 0.75, with a light stemmer and a stopword list.

**Hybrid fusion.** BM25 and dense ranks are combined with **Reciprocal Rank Fusion**: Σ 1/(60 + rank).

**Reranking.** A cross-encoder (`ms-marco-MiniLM-L-6-v2`) reorders the top candidates, with final score
0.7·rerank + 0.3·fused. It is loaded in a background thread and skipped while it isn't ready.

**Diversity.** **MMR** with λ = 0.75 picks the final top-k passages.

**Document analytics** (`insights.py`):
- Zero-shot **document-type classification**: cosine similarity to label-description prototypes, then softmax.
  The types include legal_contract, invoice_financial, research_paper and resume_cv.
- **Keyphrases:** TF-IDF n-gram candidates, re-ranked KeyBERT-style by embedding similarity, then diversified with
  MMR.
- **Extractive summary**, or an LLM summary when an LLM is configured.
- **Flesch reading ease** and reading time.
- **Topic discovery** across the workspace: K-Means over document embeddings, with clusters labelled by
  **c-TF-IDF** terms.

**Self-supervised retrieval evaluation** (`evaluation.py`, `POST /api/intel/eval`).
- Pseudo-queries are built from each chunk's highest-IDF terms, or LLM-written questions when an LLM is available.
- It reports **Hit-Rate@5 and MRR** for hybrid, dense-only and BM25-only search: an ablation on your own data,
  with no labels needed.

### 4.3 Generative AI — `app/ai/*`

**LLM gateway** (`llm.py`).
- One plain-HTTP adapter covers seven providers: Anthropic, OpenAI or any OpenAI-compatible endpoint via
  `OPENAI_BASE_URL`, OpenRouter, Gemini, NVIDIA NIM, DeepSeek and Ollama.
- It handles priority order, a 60-second **circuit breaker** per failing provider, streaming over SSE, vision input
  and JSON-mode generation with one repair retry.
- Without any provider, the app runs offline.

**RAG pipeline** (`rag.py`, run as `fast` or `deep` mode):

| Step | What it does |
|---|---|
| Plan (deep mode, needs an LLM) | rewrites the question as standalone, decomposes it into sub-questions, writes a **HyDE** passage |
| Follow-up handling | merges a short follow-up question with the previous one for retrieval |
| Summary intent | for "summarise this document", samples chunks across the whole document instead of searching |
| Retrieve | hybrid search over all queries, fused with RRF |
| **GraphRAG-lite** | adds chunks that mention entities named in the question, plus their 1-hop neighbours |
| Rerank and select | cross-encoder rerank, then MMR |
| Context | numbered sources, a 14,000-character budget, and sanitising of instruction-like text inside documents |
| Generate | a system prompt that requires `[n]` citations and treats source text as untrusted data; streamed |
| No LLM | an **extractive answer** built from the top sentences of the best passages |
| Verify | **claim verifier v2** (below); in deep mode an **LLM-as-judge** gives a second faithfulness opinion |
| Score | the **evidence score** = 0.4·retrieval strength + 0.4·support ratio + 0.2·citation coverage. **Uncalibrated, not a probability** |
| Abstain | when the answer says the sources don't cover the question, or the evidence score is below 0.25 |
| Log | the message and its metadata are stored; `query_logs` records provider, model, latency, score, a SHA-256 **prompt hash** and the chunk IDs used |

**Claim verifier v3** (`verifier.py`; v2 shipped in 2.1.0, v3 in R6). Each answer sentence is checked against the
passages it cites.

*Value checks (red, "contradicts source").* These decide whether a sentence is supported.
- Numbers: ₹, Rs, INR and $ amounts; Indian digit grouping; lakh, crore and million scales; number words;
  percentages.
- "About X" allows 5%. Sums and differences of two source numbers, and intervals between source dates, count as
  derived values.
- Dates: full dates, day-month, month-year, FY ranges and years.
- Identifiers such as account numbers, DINs, and invoice or policy numbers must match exactly.
- Payment periods (per month vs per annum) are bound to the number they qualify.
- Every party name must appear in the source.
- Relevance: embedding similarity to the best source sentence, or word coverage.

*Verifier v3 additions (R6, value checks, red).* `app/ai/recompute.py`:
- **Recomputation.** A figure the passage doesn't print is accepted when it can be computed from the passage's own
  figures with exact decimal arithmetic: durations (36 months = 3 years), monthly ↔ annual when the claim says so,
  percent-of (18% of the taxable value), an item count × a per-item rate, shares and changes between two figures the
  claim names, whole-number ratios ("six months' rent"), column totals and date intervals. The derivation is shown
  under the sentence ("Recomputed: …").
- **Money direction.** An amount in a Debit/Withdrawals (Credit/Deposits) column, or one the passage calls debited
  (credited), must not be described as coming in (going out). Column roles come from the statement header lexicon.
- **Change arithmetic.** "Rose from A to B" with B below A, or "increased to B" when the passage goes from A down
  to B, is a contradiction.

*Wording heuristics (amber, "check wording").* These are shown to the user but don't count against the answer.
v3 fixes: converse verbs (rents from / leases to), passive voice read next to the name only, "declined" read as
refused or decreased from what follows, negated direction words ("not included" = excluded), possessive name spans,
and a rarity-weighted choice of the matching source sentence.
- Negation with scope: the parity of negation cues is compared, counting only cues whose next six words touch the
  other text.
- Direction words: credit/debit, rose/fell, above/below, before/after.
- Party roles: by/from mark the source, to marks the recipient, plus the grammatical subject.

*Optional NLI model.* LettuceDetect (`KRLabsOrg/tinylettuce-ettin-68m-en`, MIT) is a token classifier run over the
whole answer in one pass. It is **off by default** (`ENABLE_NLI_VERIFIER=false`), because it didn't help on the
held-out test set.

*Output per sentence:* `supported`, `needs_review`, `issues[{kind, detail, severity}]`, a similarity `score` and
`sources`.

**Knowledge graph** (`knowledge.py`).
- Entity types: PERSON, ORG, LOCATION, DATE, MONEY, EMAIL, URL, PRODUCT, LAW, CONCEPT, OTHER.
- Extraction uses regex for EMAIL, URL, MONEY, DATE and LAW, heuristic named-entity recognition for ORG, PERSON and
  LOCATION, and, when an LLM is configured, **GraphRAG-style JSON extraction** of entities and typed relations.
- Entities are merged by normalised name, mentions are stored per chunk, and relations are weighted.
- **Timeline:** every dated fact is listed with its context, including upcoming deadlines.

**Structured extraction** (`extraction.py`). The user defines fields such as `{"effective_date": "start date"}`.
Passages are retrieved per field, and an LLM fills a JSON object, with `null` where the value isn't found.

### 4.4 Responsible AI and security — `app/ai/guardrails.py`, `app/core/security.py`, `app/api/deps.py`

**PII detection** covers email, phone, credit card (Luhn-validated), SSN, IBAN, IP address, India PAN and Aadhaar,
reported per document. It is **detected, not redacted**: `redact()` exists but nothing in the pipeline calls it.

**Indirect prompt injection** (OWASP LLM01). Documents are scanned at upload against a pattern list (pattern-based,
not a model). Instruction-like spans are neutralised in the retrieved context, and the system prompt treats source
text as data.

**Tenancy.** Every user gets a private workspace (tenant), and every query path filters by tenant. Cross-tenant
access is tested. Users from v1 are still in a shared `default` tenant.

**Authentication.**
- Passwords use PBKDF2-SHA256 with 310,000 iterations and a constant-time compare.
- Tokens are JWT HS256 with a 24-hour expiry.
- An empty or known-default `JWT_SECRET` is replaced by a random key at startup.

**Rate limits.** The limiter is in memory, per process: auth 10/min per IP; upload 30, query 60 and eval 5 per
minute per user (HTTP 429).

**Upload limits.**
- size: 50 MB
- PDF pages: 500
- image size: 40 megapixels, checked before decoding
- DOCX inflated size: 200 MB, with a cap on internal parts (stops zip bombs)
- an extension allow-list
- SHA-256 duplicate detection per tenant

**Provenance.** Each answer keeps its citations, trace, verifier output and prompt hash.

---

## 5. Data model (BUILT) — `app/database/models.py`

**Tables:**
- `tenants`
- `users`: email, password hash, tenant
- `documents`: text, hash, original file path, page count, type and confidence, summary, quality, plus JSON for
  keywords, stats, vision report, PII and security flags
- `document_chunks`: text, embedding as JSON, embedding model, page, index
- `chat_sessions`
- `chat_messages`, with `meta_json` holding citations, verifier output and trace
- `saved_items`
- `entities`
- `entity_mentions`
- `relations`
- `query_logs` (the audit trail)

The PLANNED schema (Source, Page, Region, Claim, Evidence, ResolutionDecision, AuditEvent, and others) is in
`docs/architecture/DATA_MODEL.md`.

## 6. API (BUILT) — all routes are under `/api`

**auth**
- `POST register`
- `POST login`
- `GET me`
- `PUT update_email`

**documents**
- `POST upload`
- `GET list`
- `GET {id}`
- `GET {id}/page/{n}/image`: the highlighted page
- `POST {id}/extract`: structured extraction
- `DELETE delete/{id}`
- `PUT edit/{id}`
- `POST save/{id}`

**chat**
- `POST query`
- `POST stream`: SSE events `session`, `trace`, `token` and `final`
- sessions: list, rename, delete
- `GET messages/{session}`
- saved items: list, update, delete

**intel**
- `GET graph`
- `GET overview`
- `GET timeline`
- `GET audit`
- `POST eval`
- `GET capabilities`

**vision**
- `POST analyze`: the Vision Lab

**Health:** `GET /api/health` returns `{"version": "2.1.0"}`.

Full request and response shapes are in `docs/API_CONTRACT.md`.

## 7. Frontend (BUILT) — `frontend/src`

| Page | What it shows |
|---|---|
| Dashboard | KPIs, document types, topic clusters, recent questions |
| Upload | upload, then an analysis card |
| Documents and Document page | summary, type, keywords, entities, PII, per-page vision report, structured extraction |
| Chat | streamed answers; clickable `[n]` citations; "view on page"; evidence score; claim check (red/amber/green with reasons); reasoning trace; fast or deep mode; scope by document |
| Graph | canvas force-directed entity graph |
| Timeline | every dated fact, including upcoming deadlines |
| Vision Lab | annotated regions, quality gauges, deskew angle, OCR text with confidence, caption |
| System | provider and model status, retrieval evaluation, audit log |
| Settings | account and saved items |

Login and Register complete the app.

---

## 8. Engineering, deployment and operations (BUILT)

**Tests.** `python -m pytest tests -q` runs **32 tests**, offline, against an isolated temporary database:
- end-to-end API tests
- unit tests (PII, retrieval, CV, entities)
- hardening tests (caps, zip bomb, rate limits, OpenRouter wiring)
- verifier tests, including a benchmark regression guard

In CI, `REQUIRE_ML_MODELS=1` makes the semantic tests fail rather than skip when the ML stack is broken.

**CI** (`.github/workflows/ci.yml`) runs three jobs on every push and pull request:
1. **backend:** CPU torch and torchvision installed together, the MiniLM model cached and pre-loaded, then pytest.
2. **frontend:** `npm ci`, lint, build.
3. **docker:** build the slim image; run it with 512 MB, `PORT=10000` and an SQLite path in a folder that doesn't
   exist yet; check health and the UI; then register, upload and ask a question. The app used about 162 MiB.

**Render.**
- `render.yaml` sets `JWT_SECRET` (`generateValue`), `LLM_PROVIDER_ORDER` with OpenRouter first, and asks for
  `OPENROUTER_API_KEY` and `CORS_ORIGINS` in the dashboard.
- The free plan has **no persistent disk**, so the database and uploads reset on every deploy and restart.
- It sleeps after about 15 minutes idle; the first request then takes about 40 seconds.

**Repository hygiene.**
- Dead modules and old scripts were removed; two tools moved to `tools/`.
- `.dockerignore` matches at any depth.
- ESLint flat config (0 errors, 17 warnings).
- `npm audit`: 2 moderate advisories remain, which need a React Router 7 upgrade.

**Git history.**
- `main` was replaced by the v2 line through PR #1, with a merge that kept v2's files.
- 14 personal documents and 3 derived index files were then **purged from all branches** with `git filter-repo`
  and a force-push.
- GitHub's read-only `refs/pull/1/head` still exposes the old commits, so the repo should be made private or
  GitHub Support asked to remove those refs.

**Commit policy:** commits and PR descriptions carry no AI co-author or "generated with" lines.

---

## 9. Measured results (the only numbers you may quote)

**Claim verifier v3.1 on HB-Synth v2** (R6 fixes; fresh set of 610 claims pre-registered before the fixes; scored
once):

| Held-out HB-Synth v2, MiniLM | Errors caught (of 330) | Correct sentences wrongly flagged (of 280) |
|---|---|---|
| v2 red | 77% (72–81%) | 54% (48–59%) |
| v3 red | 78% (73–82%) | 41% (35–47%) |
| **v3.1 red (shipped)** | **74% (69–78%)** | **21% (16–26%)** |

- Hashing embedder (slim/Render): v3.1 catches 77% and wrongly flags 23%.
- False-flag target (≤ 10%) not met.
- Calibration: ECE 0.110, so it is not displayed.

**Claim verifier v3 on HB-Synth v1** (R6; generated set pre-registered before the change; test scored once):

| Held-out test (600 claims), MiniLM | Errors caught (of 356) | Correct sentences wrongly flagged (of 244) |
|---|---|---|
| v2 red | 71% (95% CI 66–76%) | 30% (25–36%) |
| **v3 red (shipped)** | **72% (67–76%)** | **11% (8–16%)** |
| v3 red + amber | 84% (80–88%) | 18% (14–23%) |

- Acceptance: catch ≥ 68% met; false flags ≤ 10% **not met**.
- Hashing embedder (slim/Render): v3 red catches 75% and wrongly flags **31%** (v2: 42%).
- Calibration of P(supported): test ECE 0.096 (CI 0.077–0.115), overconfident; **not displayed**.
- Caveat: generated by the same developer who wrote the verifier; not an independent test.

**Claim verifier benchmark v0** (`benchmarks/hallucination`; report: `benchmarks/reports/HALLUCINATION_BENCHMARK.md`):
- 146 hand-labelled claims over 16 fictional Indian lending documents.
- A **dev** split (74) was used for tuning; a **test** split (72) was scored once, after the rules were frozen.

| Held-out test, MiniLM | Errors caught (of 44) | Correct sentences wrongly flagged (of 28) |
|---|---|---|
| v1 (similarity only) | 20% (95% CI 11–35%) | 14% (6–31%) |
| **v2 red tier (shipped)** | **68% (53–80%)** | **11% (4–27%)** |
| v2 red + amber | 91% (79–96%) | 43% (27–61%) |

- **By type:** every wrong number, lakh/crore scale, date, period and party name was caught (24 of 24; v1 caught
  2). Flipped negation, swapped parties and rose/fell are only caught by the amber hints.
- **Slim/Render embedder** (hashing): v1 caught 18% and wrongly flagged 29%; the v2 red tier catches 68% and
  wrongly flags 18%.
- **Caveats:**
  - The cases and the verifier were written by the same developer.
  - The set is small, synthetic and single-domain.
  - The amber/red grouping and switching NLI off were decided after seeing the test results; no rule was changed
    after the test run.

**Other measurements:**
- **Performance:** warm verification takes about 1.7 s for a 6-sentence answer over 4 sources on a laptop CPU, with
  the NLI model on. Container memory was about 162 MiB (slim image).
- **No other benchmark exists.** There is no OCR accuracy (CER/WER), table accuracy (TEDS), retrieval baseline,
  calibration (ECE) or user study yet. The in-app `/intel/eval` computes Hit@5 and MRR on the user's own data,
  but no baseline has been stored.

---

## 10. Known limitations (NOT DONE — be explicit about these)

1. **Verifier (v3.1):**
   - Meaning errors that reuse the source's words (swapped parties, flipped negation) are amber-only. The verifier
     doesn't check which table column a figure came from.
   - On unseen layouts and wording it still wrongly flags about 1 in 5 correct sentences (HB-Synth v2: 21%, 23%
     with the hashing embedder).
   - Known gaps: units given only in a column header, three-figure totals, a date plus a number of days, labels
     written after the figure.
2. The **evidence score is uncalibrated**: it is not a probability. A claim-level calibration was measured twice (ECE 0.096 on HB-Synth v1, 0.110 on v2) and is not shown.
3. **Ingestion is synchronous** inside the upload request. There are no workers, retries or progress events.
4. **SQLite and in-memory state:** no Postgres or Alembic, the index lives in process memory, and rate limits
   aren't shared across replicas.
5. **Scanned PDFs have no stored word boxes**, so citation highlights only work on PDFs with a text layer.
6. **PyMuPDF is AGPL-3.0.** It must be replaced before any closed-source distribution. EasyOCR is stagnant.
7. **PII is detected, not redacted.** Prompt-injection defence is pattern-based.
8. **The live site has no persistence** (free plan). `JWT_SECRET` and CORS must be set in the Render dashboard.
9. **v1 users share the `default` tenant.** There's no RBAC, SSO or organisation workspaces.
10. **Entity resolution is name normalisation only.** There's no identifier validation (GSTIN, PAN, CIN) and no
    human-reviewed merges.
11. **No synthetic case generator or document benchmarks yet.** That's MindDoc-Synth, backlog Phase 2.

---

## 11. Research and strategy done (documents, not code)

- **`docs/audit/CURRENT_STATE_AUDIT.md`:** an independent audit of what works, what doesn't, security and
  licences. It found that the v1 checker passed 6 of 6 planted hallucinations.
- **`docs/research/`:**
  - industry landscape: Palantir, Quantexa, MindBridge, Perfios, Microsoft GraphRAG, NVIDIA NeMo Retriever,
    Azure/Google document AI
  - technology evaluation with licence checks
  - research papers: 72 references are tagged [K] (cited from memory) and **must be verified before citing**
  - research gaps: directions A–E
  - benchmark datasets
  - hackathon winners analysis
- **`docs/strategy/`:**
  - market selection: **lender forensic review of borrower fund flows in India** scored 4.05/5; the fallback is
    procure-to-pay integrity (3.70)
  - competitive analysis (requirements R1–R10)
  - product differentiation
- **Re-check in `docs/review/D_MARKET_RESEARCH.md` (2026-11-10, cited) — inconclusive, commercially weaker:**
  - **The problem is real and regulation-driven:** RBI's 2026 fraud directions; the 2024 wilful-defaulter direction
    (diversion, siphoning, "shall consider" a forensic audit); *Amit Iron* (2026), under which the forensic report
    is given to the borrower with third-party parts withheld.
  - **But competitors already exist:** IDfy's Transaction Intelligence Platform, Cygnet Finalyze, iAcuity,
    CypherSOL and Valid8 flag round-tripping or related parties.
  - **RBI asks for an "external or internal" audit**, so outside forensic firms aren't the only buyer.
  - **Published fees look capped** (about ₹80k per audit, unverified).
  - **Account Aggregator** data only reaches regulated institutions, so forensic and CA firms still depend on PDFs.
  - **Rescored:** about 3.70–3.85, roughly level with the fallback. **The market is not decided**; see gate M1 in
    §13.
- **Most promising research direction: E, robustness of findings to source removal.** Each finding gets a
  "leave-one-source-out" fragility score. Ground truth comes from re-running the pipeline, so no labels are needed.
  It's a workshop-paper target.
- **Open-source upgrade shortlist (licences checked 2026-11-10):**
  - **Permissive:**
    - PaddleOCR-VL (Apache-2.0)
    - Docling (MIT)
    - GLM-OCR (Apache-2.0)
    - ColQwen visual retrieval (colpali-engine MIT)
    - LightRAG, HippoRAG 2, Microsoft GraphRAG (all MIT)
    - Graphiti (Apache-2.0; reference design for time-aware facts)
    - Splink (MIT)
    - LettuceDetect (MIT)
    - HHEM-2.1-Open (Apache-2.0)
    - DeepEval (Apache-2.0)
    - Inspect AI (MIT)
    - Outlines (Apache-2.0)
    - C2PA signing (c2pie, c2pa-rs)
  - **Avoid or check first:**
    - MinerU: extra licence terms
    - Marker weights: OpenRAIL-M, paid licence above $5M revenue
    - PyMuPDF, YOLO and DocLayout-YOLO: AGPL
    - LayoutLMv3 weights: non-commercial
    - Neo4j Community, igraph, leidenalg: GPL
    - Arize Phoenix: Elastic License 2.0

---

## 12. Target architecture (PLANNED — ADRs 0001–0009, all "Proposed")

| ADR | Decision |
|---|---|
| 0001 | Modular monolith + separate worker processes (no microservices) |
| 0002 | PostgreSQL 18 as the system of record: pgvector, full-text search, row-level security, Alembic |
| 0003 | Job table + transactional outbox now; **Kafka only at a trigger** (3+ consumer groups needing replay, or more than about 200 events/s) |
| 0004 | **Claim-centric, bitemporal evidence model**: a claim is not a fact; every value keeps valid time and system time; reviews are append-only |
| 0005 | Graph stored in Postgres, analysed with NetworkX/graspologic; no graph database yet; Cytoscape.js explorer |
| 0006 | Parsing with Docling + PaddleOCR + Tesseract; licence-clean models; PyMuPDF removed |
| 0007 | Own typed plan executor with four LLM roles (Planner, Extractor, Verifier, Writer) over deterministic tools; no agent swarm |
| 0008 | Primary market: forensic review of borrower fund flows (India) |
| 0009 | Entity resolution with Splink plus human-confirmed, reversible merges |

Further detail is in `docs/architecture/`:
- `SYSTEM_ARCHITECTURE.md`: layer by layer
- `DATA_MODEL.md`
- `EVENT_CATALOG.md`
- `INVESTIGATION_ENGINE.md`: forensic detectors D1–D7, the discovery ledger, the hypothesis lab
- `EVALUATION_FRAMEWORK.md`
- `SECURITY_ARCHITECTURE.md`

---

## 13. How we approach new features (the plan and the method)

### 13.1 Order of work — `docs/IMPLEMENTATION_BACKLOG.md`
**Stabilise → measure → foundation → evidence → intelligence → agents → validation.**

| Phase | Content | Status |
|---|---|---|
| 0 Stabilise | base-branch choice, hygiene, honest UI wording, upload caps, rate limits | **done**, except owner actions: `JWT_SECRET`/CORS on Render; private repo or GitHub Support |
| 1 Evidence foundation | Postgres + Alembic, canonical schema with row-level security, blob store, job table and workers, async ingestion, legacy-tenant quarantine | next |
| 2 Measure first | MindDoc-Synth generator, DocBench-50, a larger hallucination set, benchmark harness, baseline scorecard | partly started (the hallucination set v0) |
| 3 Document intelligence v3 | Docling, PaddleOCR, word boxes for scans, table cells, **bank-statement parser with running-balance reconciliation**, GST and Tally import | planned |
| 4 Claims, entity resolution, graph explorer | claim extraction with evidence; GSTIN/PAN/IFSC/CIN/DIN validation; Splink; Cytoscape explorer | planned |
| 5 Verifier v2 + Postgres retrieval | **verifier v2 is built early**; recomputation, calibration (ECE) and retrieval on Postgres are still to do | in progress |
| 6 Forensic detectors | D1–D7, Benford and threshold tests, IsolationForest/LOF with SHAP explanations, discovery ledger | planned |
| 7 Evidence-constrained investigation | plan executor, verifier pipeline including leave-one-source-out fragility, report with evidence bundle | planned |
| 8 Validation and launch | 25 customer interviews, a retrospective pilot, research paper, public scorecard | planned |

**Explicitly not now:**
- Kafka on day one
- Neo4j, Temporal, Flink or Spark, Kubernetes
- LLM fine-tuning
- YOLO or LayoutLMv3 (licences)
- agent swarms
- live government-portal scraping
- any automated "fraud" verdict

> **Superseded ordering (2026-11-10):** `docs/review/J_ROADMAP.md` re-orders this as follows:
> - **R0:** decide and secure.
> - **R1:** measure (StatementBench) and start interviews.
> - **R2:** evidence foundation (Postgres, Alembic, RLS, jobs).
> - **Gate M1 (market decision).**
> - **R3–R4:** statement engine.
> - **R5:** entities.
> - **R6:** verifier round 2.
> - **R7:** detectors (after gate M2).
> - **R8:** investigation, fragility, redacted reports.
>
> The full review (deliverables A–J) is in `docs/review/`; read its README first.

### 13.2 Recommended next three items
1. **Verifier round 2:**
   - fix the bugs the test split revealed: converse verbs, local passive voice, "declined", possessive entity spans
   - add a recomputation engine for percentages and from→to arithmetic
   - add table-column semantics
   - then measure on a **fresh** labelled set and on RAGTruth
2. **Phase 1 foundation:** Postgres, Alembic and async ingestion. Everything later depends on durable claims and
   evidence.
3. **Phase 3 bank-statement parser with running-balance reconciliation.** It is self-verifying, because extraction
   errors show up without labels, and it is the core of the target market.

### 13.3 Workflow for any new feature
1. **Write the problem and the metric first.** What failure does it fix, and how will we measure it? Add labelled
   cases with a dev/test split before building.
2. **Record a baseline** of the current code on that benchmark.
3. **Design:** a short ADR if it adds a dependency, a data structure or a service. Check the licence and the
   project's activity before adopting any library or model.
4. **Implement behind a setting** if it is optional or model-backed. The slim install (no torch) must keep working.
5. **Test:** unit tests, an API test, and a regression guard on the benchmark.
6. **Measure on the held-out split once.** Report confidence intervals, per-type results and caveats. Never tune on
   the test split.
7. **Make the UI honest:** labels describe what the code actually does, with tooltips for uncertainty, and no
   placeholder or fake features.
8. **Update the docs** in the same change: CONCEPTS, MANUAL, API_CONTRACT, the backlog status and this file.
9. **Run CI**, including the Docker boot and smoke test, then push to `main` (Render deploys), then check
   `/api/health`.

---

## 14. Non-negotiable rules (from the project brief)

- Never claim something was inspected, tested, benchmarked or implemented unless it actually was.
- Never fabricate performance statistics; quote only §9 or newly measured, stored results.
- Never add a technology just to make the stack look impressive; every addition needs a measured reason.
- Never create fake UI functionality. Never sacrifice correctness for an impressive demo.
- Keep secrets out of source control. Audit before modifying. Preserve working functionality. Avoid unnecessary
  rewrites.
- No automated "fraud" or "forgery" verdicts: findings are leads for a professional's judgement.
- Treat licences as product requirements: no AGPL, GPL or non-commercial components in the shipped product.

## 15. Glossary

| Term | Meaning |
|---|---|
| **RAG** | retrieval-augmented generation: retrieve passages, then generate an answer that cites them |
| **BM25** | lexical ranking function |
| **RRF** | Reciprocal Rank Fusion |
| **MMR** | Maximal Marginal Relevance (diversity) |
| **HyDE** | Hypothetical Document Embeddings: embed an imagined answer to search with |
| **Cross-encoder** | model that scores a query and passage together; used for reranking |
| **c-TF-IDF** | class-based TF-IDF, used for topic labels |
| **NLI** | natural-language inference: does the text entail the claim? |
| **ECE** | expected calibration error |
| **Bitemporal** | storing both when a fact was true (valid time) and when the system learned it (system time) |
| **Outbox** | write events in the same DB transaction, publish them later |
| **TEDS** | table-structure similarity metric |
| **CER / WER** | character and word error rate (OCR accuracy) |
| **Lakh / crore** | 10^5 / 10^7 (Indian number scales) |
