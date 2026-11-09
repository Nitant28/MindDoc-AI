# MindDoc AI — Current-State Engineering Audit

Date: 2026-11-10. Scope: local `main` @ `1c888a1` ("New changes1"; v2 backend + v2 frontend), compared against v1
(`3245528`) and the public remote (`origin/main` @ `6f4a21b`). Method: read all of `app/`, the main frontend files and
`tests/`; ran the test suite, the frontend build (in place and from a clean `git archive`), throwaway probes (isolated
SQLite copies, `LLM_PROVIDER_ORDER=none`, scripts in the session scratchpad only), a localhost UI smoke test in a browser,
and read-only requests to the deployed site. No repository file was changed except this one.

Legend: **Works** = verified by test/probe/browser. **Partial** = runs, but limited or heuristic in ways that matter.
**Placeholder/UI-only** = presented as more than it is. **Broken** = gives wrong results or fails. **Untested** = code
exists, never exercised (no LLM key, no live provider, no test).

---

## Executive summary

- **The deployed site is not this code.** `https://minddoc-ai-2.onrender.com` reports `version 1.0.0` and serves the v1-lineage
  `origin/main` routes (no `/api/intel/*`, `/api/vision/*`, `/api/chat/stream`). Local `main` and `origin/main` have
  **diverged** from `3245528` (1 local commit vs 25 remote commits); a normal push will be rejected.
- **The live v1 deployment is likely forgeable.** v1 config defaults `jwt_secret` to a public literal
  (`origin/main:app/core/config.py:9`) and the remote `render.yaml` never sets `JWT_SECRET`. CORS on the live site reflects any
  `Origin` with `allow-credentials: true` (verified by preflight). Whether `JWT_SECRET` is set in the Render dashboard
  could not be checked.
- **The public GitHub repo contains user documents** (`origin/main:data/uploads/resume.pdf`, tax notices, assignments,
  14 files) plus `app/indexes/*` (3 files) built from them. The repo answers HTTP 200 without auth.
- **A fresh clone of local `main` does not build.** `.gitignore:15` (`lib/`) ignores `frontend/src/lib/` (8 files). A clean
  checkout gives 104 TypeScript errors (80 "cannot find module ../lib/..."). The in-place build passes only because the
  files are on disk.
- **The "verified / grounded / calibrated" trust layer fails on the core cases.** The claim verifier (`app/ai/rag.py:150-181`)
  marked as "supported" every hallucination I tried: wrong amount ($96k vs $48k), swapped payer/payee, negation, wrong
  period, and an uncited invented claim. Offline, an off-topic question got confidence 0.71, `grounded=true`,
  `abstained=false`. Confidence is a fixed weighted sum (`rag.py:200-208`) with no calibration.
- **Tenant isolation is correct for new users.** All 15 cross-tenant probes returned 404 or empty. Legacy data is
  different: the repo's `minddoc.db` has **26 v1 users all in the `default` tenant, sharing 16 documents with
  `owner_id=NULL`**, so they can't be separated after upgrade.
- **Ingestion runs synchronously inside the HTTP request.** A 30-page text PDF took 43 s (profiled: `find_tables` 13 s,
  embeddings 20 s, graph 7 s). A scanned page with EasyOCR on CPU took ~40 s. There are no page or pixel caps and no rate
  limits on upload, query or eval, so large uploads are a DoS risk.
- **Retrieval works and is tenant-scoped, but the in-memory design caps out early.** At 20k chunks: index rebuild 29 s
  after any upload or delete, run under one global lock; 665 ms per search in pure-Python BM25; vectors stored as JSON
  text at about 5 KB per chunk.
- **Heuristics are labelled as learned or verified features.** NER is regex plus a first-name list (missed "Satya Nadella"
  and "Sundar Pichai"). Mention counts use substring matching ("usa" counted 5× vs 2). Prompt-injection defence is a
  10-pattern blocklist (3 of 6 variants missed). PII is detected but **never redacted**: `redact()` is used only in tests.
- **The multi-provider LLM gateway has never been run against a real provider.** It covers Anthropic, OpenAI-compatible,
  Gemini, NVIDIA, DeepSeek and Ollama over raw HTTP. Response and SSE parsers pass canned payloads. The circuit breaker
  trips on any error, including a vision call to a model that can't take images.
- **Deploy configs are broken or risky.** Local `render.yaml` is a native Python service: no frontend build, no Tesseract,
  torch on the free 512 MB plan, no disk, no `JWT_SECRET`. The Dockerfile has no `.dockerignore`, so the build context is
  about 4.5 GB and `COPY frontend/` overwrites Linux `node_modules` with Windows binaries (high confidence; Docker daemon
  was off, so not executed).
- **License blocker:** the core PDF parser and page highlighter use PyMuPDF, which is **AGPL-3.0** (installed 1.23.7).
  Commercial SaaS use needs an Artifex licence or a swap to a permissive library.
- **Stack claims:** PostgreSQL, pgvector, Redis and LangChain are **absent** from the code. Docker, Ollama and multiple LLM
  providers are present.
- **Results:** `pytest` 17 passed in 189.8 s. `npm run build` passes in place (vite 11.7 s) but fails from a clean checkout.
  `npm run lint` is broken (ESLint 10, no config). `npm audit`: 12 advisories in the production dependency tree, 7 high.

---

## Severity-ranked issue table

| # | Sev | Where (file:line) | Issue | Impact | Fix |
|---|---|---|---|---|---|
| C1 | Critical | `origin/main:app/core/config.py:9`, `origin/main:render.yaml`, `origin/main:app/main.py:43-44` | Live v1 signs JWTs with a public default secret unless Render sets `JWT_SECRET` (not set in blueprint). CORS `*` + credentials (verified: reflects `https://evil.example`). | If unset, anyone can mint a token for any user id and read their documents. | Set a random `JWT_SECRET` in Render now (invalidates tokens). Restrict CORS. Replace the deployment with v2 after the P0 fixes. |
| C2 | Critical | `origin/main:data/uploads/*` (14 files incl. `resume.pdf`), `origin/main:app/indexes/*.json` | Personal documents and derived indexes are committed to a public repo. | Ongoing PII exposure; history keeps it even after deletion. | Make the repo private, purge with `git filter-repo`, force-push, notify the people concerned. |
| C3 | Critical | `.gitignore:15` | `lib/` ignores `frontend/src/lib/` (storage, theme, format, cx, dates, entities, clipboard, useTitle). | Clean clone, CI and Docker builds from git fail (verified: 104 TS errors). | Add `!frontend/src/lib/` (or scope `lib/` to `/lib/`) and commit the 8 files. |
| C4 | Critical (product integrity) | `app/ai/rag.py:150-181`, `:200-208`, `:344-346` | Groundedness = cosine ≥ 0.5 **or** token overlap ≥ 0.6 against the cited chunk. It can't see numbers, polarity or roles. Uncited claims are checked against all sources. | UI shows "Grounded 2/2" and a high confidence on wrong answers. Offline it treats copied passages as verified (off-topic: 0.71 / grounded). | Use an NLI / entailment cross-encoder per (claim, cited chunk), plus number/date/entity consistency checks, plus an LLM judge. Fit confidence on labelled data (ECE). Until then, label it "heuristic". |
| H1 | High | `app/database/models.py:234-240`; legacy `minddoc.db` | 26 v1 users share tenant `default`, and the 16 v1 documents have `owner_id=NULL`. After upgrade, graph, timeline, audit and chat retrieval are shared across all of them. | Cross-user data exposure for every pre-v2 account. | Migration: move each legacy user to a private tenant. Quarantine unowned docs (admin-only) or ask users to re-upload. |
| H2 | High | `app/api/documents.py:41`, `app/services/ingestion.py:51-96`, `frontend/src/api.ts:139` | Parse, OCR, embed, LLM summary, LLM graph and analytics all run inside the request. The client gives up at 300 s; the server keeps working. | Uploads of 30 pages or more, or any scan, are slow or time out. Each upload holds a threadpool worker. | Job queue plus a status/progress endpoint. Store the original first, then process asynchronously. |
| H3 | High | `app/services/document_service.py:110,155-167`, `app/vision/highlight.py:42`, `app/api/documents.py:35` | No page-count cap. No pixel cap for uploaded images (PIL only warns below ~179 MP). Pages are rendered at 2× an attacker-controlled MediaBox. DOCX zip bombs are possible. Multipart is spooled to disk before the size check. No rate limit on upload, query or eval. | One request can exhaust memory, CPU or disk, or run up LLM spend. | Caps on pages, pixels and decompressed size. Run parsing in a sandboxed worker with timeouts. Per-user quotas and rate limits. Request size limit at the proxy. |
| H4 | High | `Dockerfile:5-6`; missing `.dockerignore` | `COPY frontend/ ./` after `npm ci` copies host `node_modules` (only `rollup-win32-*`, `@esbuild/win32-x64` present). The context includes `models/` (2.9 GB), `OllamaSetup.exe` (1.26 GB) and `.env`. | Image build likely fails on the vite step; slow builds; risk of secrets in the context. | Add `.dockerignore` (node_modules, dist, models, venvs, `*.exe`, `.env`, `*.db`, `data/`). |
| H5 | High | `render.yaml:1-15`, `app/core/config.py:69-73` | Native env: no SPA build (`/` returns 404 JSON), no Tesseract, torch + EasyOCR + 2 models on 512 MB, no disk (SQLite and uploads wiped on restart). No `JWT_SECRET`, so a random key is used and every restart logs everyone out. The declared Postgres is unused and there is no driver. | The blueprint can't produce a working v2 deployment. | Docker env, persistent disk or managed Postgres, `JWT_SECRET` from a secret, an instance with ≥ 2 GB RAM, or remove EasyOCR. |
| H6 | High (commercial) | `requirements.txt:13`; `document_service.py:27`; `highlight.py:11` | PyMuPDF is AGPL-3.0. | Network use obliges releasing source or buying a commercial licence. | Buy a licence, or move to `pypdfium2` (Apache/BSD) + `pdfplumber` (MIT), or docling (MIT). |
| H7 | High | `app/ai/guardrails.py:79-110`, `app/ai/rag.py:234-235` | Injection defence is a regex blocklist plus a system prompt. Reordered, synonym and Hindi variants were not detected. Query-side detection only adds a trace line. | Indirect prompt injection from uploaded documents is not reliably mitigated. | Treat as defence-in-depth only: strict output schema, no tool access, mark untrusted spans, test against a red-team set. Don't market it as protection. |
| H8 | High (scale) | `app/ml/retrieval.py:207-288`, `:88-99` | The whole tenant index is rebuilt (JSON decode + BM25) on every chunk-set change, under one **global** lock. Search is O(N) in Python. | 20k chunks: 29 s rebuild, 665 ms per query. Other tenants' rebuilds block. | pgvector (HNSW) + Postgres FTS/BM25, or Qdrant/OpenSearch. Drop the in-process cache. |
| M1 | Medium | `frontend/src/api.ts:334-340`, `:248-276`; `app/api/chat.py:96-97` | On any stream failure, including after the server finished and persisted, the client re-POSTs `/chat/query` with the original `session_id` (null). The `session` SSE event is ignored. | Double LLM cost, duplicate session and audit rows, answer blanked and regenerated. | Track the session id from the SSE `session` event. Retry only if no `final` was persisted (idempotency key). |
| M2 | Medium | `app/ai/rag.py:48,92-103,258-260` | Any query matching `summar...` skips retrieval for evenly spaced chunks. Unscoped summaries use only the **first 3 documents by id**. Coverage hits get a fixed score of 0.7. | "Summarize the termination clause" retrieved 1 arbitrary chunk (verified). Newer docs are ignored; confidence is inflated. | Classify intent with an LLM or a stricter rule. Use map-reduce summaries over all scoped docs. |
| M3 | Medium | `app/ai/llm.py:262-273,313-317,348-351` | The breaker opens on any exception (4xx, JSON errors, vision request to a text-only Ollama/NVIDIA model) for 60 s, process-wide. | One bad request disables a provider for every tenant. | Break only on 5xx, timeouts and 429. Track vision capability per model. |
| M4 | Medium | `app/ml/embeddings.py:65-87`, `app/ml/retrieval.py:263-277` | If MiniLM isn't cached, the active model becomes `hashing-384`. `_build` then re-embeds and **persists** every chunk with hashing, and does it again when the download finishes. The model import is on the request path (first local upload: 65 s). | Quality drops and write churn on cold containers. | Bake models into the image (the Dockerfile does), fail closed instead of overwriting vectors, warm up before readiness. |
| M5 | Medium | `app/ml/retrieval.py:211-215` | The index fingerprint is (count, max id, model). Renames and edits are invisible to it. | Citations keep showing the old filename (verified). | Include `max(updated_at)`, or invalidate on rename; or don't cache filenames. |
| M6 | Medium | `app/database/models.py:201-215` | Auto-migration only adds columns. Indexes and constraints are not created on upgraded DBs (verified: legacy `documents` and `document_chunks` have only PK indexes). No Alembic. | Full table scans on the tenant/document filters every request uses. | Alembic with explicit revisions; create the missing indexes. |
| M7 | Medium | `app/ai/knowledge.py:33-35,248-270` | Ambiguous dates are read day-first (US `03/04/2025` becomes 3 Apr). 2-digit years always become 20xx (`12/31/99` becomes 2099). `3/4/10` (a version string) is extracted as a date. `March 2025`, `2025/03/12`, `12.03.2025` and `Q3 2025` are unsupported. | Wrong deadlines and renewals on the Timeline. | `dateparser` or `dateutil` with a per-document locale, plus context filters; keep the source span. |
| M8 | Medium | `app/ai/knowledge.py:42-56,148-169,202-203` | NER is regex plus gazetteers. Mentions are counted by substring, not word boundary. Co-occurrence is stored as "relations". Entity upserts are N+1; the orphan sweep runs O(entities) queries per delete. | Graph noise, inflated counts, slow ingest and delete. | spaCy/GLiNER NER, word-boundary matching, batched upserts. |
| M9 | Medium | `app/api/intel.py:102-111`; `app/main.py:55` | `/api/intel/capabilities` is unauthenticated. It reveals which provider keys are configured and triggers an Ollama probe and the reranker load. `/docs` and `/openapi.json` are public. | Reconnaissance; outbound calls triggered by anonymous requests. | Require auth; disable docs in production. |
| M10 | Medium | `app/api/documents.py:56-62`, `app/api/intel.py:31-49` | List and overview load every document's full `content`, and overview runs KMeans (`n_init=10`) on every dashboard load. | O(corpus) per page view. | Select only columns; cache topics at ingest. |
| M11 | Medium | `app/ai/rag.py:295,318,357-365`; `frontend/src/pages/System.tsx:263` | The audit log stores a **hash** of the prompt plus chunk ids, and those chunks are deleted with the document. It is not append-only. Uploads, deletes and logins are not logged. The UI says "every answer is reproducible". | Not audit-grade; the claim is false. | Store prompt and context snapshots (or content-addressed chunk versions), append-only table, log admin and data events. |
| M12 | Medium | `requirements.txt:6`, `app/core/security.py:36-47`, `app/api/auth.py:47-48` | `python-jose` 3.3.0 is allowed (CVE-2024-33663/-33664; weakly maintained). No `jti`, revocation, password change or reset, or account deletion. Register responses enable email enumeration; login has a timing oracle. | Weak account lifecycle; can't honour erasure requests. | PyJWT, refresh and revocation, password flows, `DELETE /me` that cascades. |
| M13 | Medium | `app/api/auth.py:33-36`, `app/core/security.py:50-70` | The auth rate limit is keyed on `request.client.host`. Behind Render/Cloudflare, uvicorn only trusts `127.0.0.1` for forwarded headers, so (likely) all users share one key. The limiter is per-process and its dict never evicts. | Global login lockout after 10 attempts per minute; no per-account brute-force protection. | Configure trusted forwarded headers; Redis or proxy rate limits keyed per account and IP. |
| M14 | Medium | `requirements.txt` (all `>=`), `frontend/package.json:10,13,19` | Unpinned Python deps. Lint script broken. `vite` and an odd `@babel/helper-validator-identifier` in runtime deps. 12 npm advisories in the prod tree (mostly build-time). | Builds not reproducible; no lint gate. | Lockfile (`uv`/`pip-tools`), ESLint flat config, `npm audit fix`. |
| M15 | Medium | `app/ai/extraction.py:28-46`, `app/api/documents.py:105-107` | The LLM path is untested and unverified against passages. The offline fallback returns the nearest sentence for **every** field and never null. The 502 response echoes the provider error. | Confidently wrong extracted fields. | Per-field evidence span plus verification; null below a threshold. |
| M16 | Medium | `app/ai/guardrails.py:12-21,69-76`; `app/services/ingestion.py:63-65`; `app/vision/cv.py:281-299` | PII is detected but never redacted. Raw text and images (IDs, forms) go to third-party LLMs for summary, graph and captions. Queries are stored indefinitely. No names, addresses or DOBs are detected. | Data-protection claims overstated; no egress control. | Presidio-based detection, redact-before-egress option, retention policy. |
| L1 | Low | `app/api/chat.py:39-43`; `app/ai/rag.py:226-232` | The session is created before the scope check, leaving empty sessions on failed queries (verified). | Clutter. | Create the session after validation. |
| L2 | Low | `app/ml/insights.py:41,56-58,62-66` | `overlap=0` is silently replaced with 150. `CHUNK_OVERLAP >= CHUNK_SIZE` loops forever. Chunks reach about 1.16× size (1045 vs 900). | Config footgun. | Validate settings; use `is None` checks. |
| L3 | Low | `app/services/document_service.py:97-105` | Native tables are appended as Markdown **in addition to** the text layer that already contains them. | Duplicate text in chunks and BM25. | Replace the table regions in the text instead of appending. |
| L4 | Low | `app/vision/highlight.py:40-41` | Highlights only work on PDFs with a text layer. OCR pages, DOCX and images get none. Each request re-renders, with no cache. | Partial provenance. | Store OCR word boxes; cache rendered pages. |
| L5 | Low | `app/vision/cv.py:262-278`; `frontend/src/pages/Vision.tsx:24,27` | Layout blocks are only counted; OCR runs on the whole page. The UI says "per block" and "Hough lines". | Over-claiming copy. | Fix the copy, or OCR per block in reading order. |
| L6 | Low | `app/services/{deepseek_client,ollama_client,local_llm,llama_manager,rag_service}.py`, `scripts/*` | Dead legacy code, only referenced by scripts. | Confusion. | Delete (see §6). |
| L7 | Low | `frontend/src/pages/DocumentPage.tsx:56-73`, `frontend/src/api.ts:75` | Frontend fallbacks for "v1 backends". | Dead branches. | Remove once v2 is the only backend. |
| L8 | Low | `app/api/chat.py:140-147,188-196`, `app/api/documents.py:116-121` | Unbounded `save_response`; edits take content and titles as query parameters. | Data in URLs and logs; DB bloat. | Pydantic bodies with length limits. |
| L9 | Low | `app/core/config.py:27-28` | Default Anthropic model ids `claude-sonnet-5-5` / `claude-haiku-5-5` were not verified against the provider list. | First call may 404, which also trips the breaker (M3). | Verify ids; make them required config. |
| L10 | Low | `app/ai/llm.py:352-354` | If a stream fails midway, the partial text is returned as a complete answer, then verified and persisted. | Truncated answers look final. | Mark as `truncated`. |
| L11 | Low | malformed upload (verified) | A non-PDF named `.pdf` returns 500 instead of 400. Binary named `.txt` is accepted (no content sniffing). | Noise in error handling. | Magic-byte check; map parser errors to 400. |
| L12 | Low | `# Code Citations.md` | Copilot code-referencing flagged GPL-2.0 matches for SVG icon snippets. | Licence ambiguity for icons. | Confirm `Icon.tsx` paths come from MIT/ISC sets (Heroicons/Lucide) and attribute. |

---

## 1. Architecture map

### 1.1 Modules

| Layer | File | Responsibility (as implemented) |
|---|---|---|
| Entry | `app/main.py` | App, CORS (`:58`), global 500 handler (`:62-65`), routers, `/api/health`, `/api/test`, SPA catch-all (`:86-95`), lifespan creates tables and the default tenant, and starts a warm-up thread (model load + backfill of v1 docs, `:22-37`). |
| Config | `app/core/config.py` | pydantic-settings from env and `.env` (relative to the CWD). An empty or insecure JWT secret is replaced by a random one per process (`:69-73`). |
| Security | `app/core/security.py` | PBKDF2-SHA256, 310k iterations, plus legacy v1 verify; HS256 JWT (python-jose); in-process sliding-window limiter, 10/min (`:70`). |
| API | `app/api/{auth,documents,chat,intel,vision}.py`, `deps.py` | REST + SSE. `get_current_user` decodes the JWT and loads the user (`deps.py:11-18`). |
| Ingestion | `app/services/ingestion.py`, `document_service.py` | SHA-256 dedup per tenant; parse PDF/DOCX/image/text; page-aware chunking; embed; classify, keywords, summary, PII and injection scans; persist; graph build; invalidate index; store original as `STORAGE_DIR/<tenant>/<doc_id><ext>`. |
| Vision | `app/vision/cv.py`, `highlight.py` | OpenCV quality, denoise, CLAHE, deskew, adaptive threshold; morphological layout; Tesseract/EasyOCR; VLM caption; PDF page render with `search_for` highlights. |
| ML | `app/ml/embeddings.py`, `retrieval.py`, `insights.py`, `evaluation.py` | MiniLM or hashing embeddings; optional cross-encoder; BM25 + dense + RRF + MMR over an in-memory per-tenant index; TF-IDF/KeyBERT-style keywords; prototype zero-shot classifier; extractive summary; KMeans topics; self-supervised hit@5/MRR. |
| GenAI | `app/ai/llm.py`, `rag.py`, `knowledge.py`, `extraction.py`, `guardrails.py` | HTTP gateway for 6 providers with a breaker; RAG pipeline with trace, verify and confidence; regex/LLM graph; schema extraction; PII and injection regexes. |
| Data | `app/database/models.py` | SQLAlchemy models; SQLite WAL; additive auto-migration. |
| Frontend | `frontend/src/*` | React 18 + TS + Vite + Tailwind; axios client (`api.ts`); SSE via `fetch` streams; custom Markdown renderer and force-directed graph (no third-party libraries); 11 routes (`App.tsx`). |
| Legacy (dead) | `app/services/{deepseek_client,ollama_client,local_llm,llama_manager,rag_service}.py` | Not imported by `app/` (only by `scripts/`). |

### 1.2 Request flows

**Upload → ingestion** (all synchronous in one request):

1. `POST /api/documents/upload` (`documents.py:29`): extension allow-list (`:32`), read ≤ `MAX_UPLOAD_MB` (`:35`).
2. `ingest_bytes` (`ingestion.py:31`): SHA-256 dedup within the tenant (`:33-36`), then `parse_document` by extension (`document_service.py:180`).
3. PDF pages: if the text layer has ≥ 40 chars, add `find_tables` Markdown (`:93-108`); otherwise render at 2× and OCR (`:110-114`).
4. `ingest_parsed` (`ingestion.py:51`): `chunk_pages` (900/150, page-aware), `emb.embed`, `classify_document`, `llm_summary` or extractive summary, keywords, `pii_summary`, `detect_injection`, `text_stats`.
5. Insert `Document` and `DocumentChunk` rows (vectors as JSON text) and commit.
6. `knowledge.build_graph_for_document` (regex entities, plus LLM entities and relations if a key is set; substring mentions; co-occurrence relations; commit). Then `retrieval.invalidate`, and the original is written to disk (`:39-47`).

**Question → answer** (`chat.py:68` JSON, `:86` SSE; both call `rag.run`):

1. Session lookup by `user_id`, or create one (`chat.py:33-43`). Load the last 8 messages.
2. Filter scoped `document_ids` to the tenant (`rag.py:226-232`). An injection regex on the query only adds a trace line (`:234`).
3. `get_index(db, tenant)` (`retrieval.py:218`): a fingerprint query, then cached or rebuilt.
4. Plan: deep mode with an LLM does rewrite, sub-queries and HyDE (`rag.py:57-70`). Otherwise a pronoun follow-up heuristic (`:249-252`).
5. Retrieve: summary-intent coverage sampling (`:258-260`), or hybrid search per query fused by RRF (`:262-269`). GraphRAG-lite adds ≤ 4 entity-linked chunks (`:271-277`), then optional rerank (`:279-285`), then MMR (`:286`).
6. Build context (14k-char budget, regex sanitising, `:115-129`).
7. Generate: LLM streamed with `[n]` citations; extractive if no LLM; general-knowledge answer if no sources (`:293-332`).
8. `_verify` (`:150-197`), `_confidence` (`:200-208`), grounded/abstained flags (`:344-346`), `QueryLog` insert (`:357-365`), `final` event. `chat._persist` stores both messages with `meta_json`.

### 1.3 DB schema (`app/database/models.py`)

| Table | Key columns | Notes |
|---|---|---|
| `tenants` | id, name (unique) | One per registered user (`auth.py:50`); `default` for v1. |
| `users` | id, email (unique), hashed_password, tenant_id, created_at | No roles, no status. |
| `documents` | tenant_id (idx), owner_id, content (full text), content_hash (idx), source_path, pages, doc_type, summary, quality_score, `*_json` (keywords, stats, vision, pii, security) | The full text sits on the row and is loaded by list and overview. |
| `document_chunks` | document_id (idx), chunk_text, **embedding (JSON text)**, embedding_model, page, chunk_index | About 5.1 KB per chunk measured. No ondelete. |
| `chat_sessions` / `chat_messages` | user_id / session_id (idx), role, content, meta_json | Scoped by user, not tenant. |
| `saved_items` | user_id, item_type, title, content | |
| `entities` | tenant_id, name, norm_name, type, mention_count; UNIQUE(tenant, norm_name, type) | The constraint exists only for newly created tables. |
| `entity_mentions` | entity_id, document_id, chunk_id (CASCADE), count | |
| `relations` | tenant_id, document_id, source_id, target_id, relation, weight | Mostly `co_occurs`. |
| `query_logs` | tenant_id, user_id, session_id, query, provider, model, latency, confidence, grounded, prompt_hash, chunk_ids_json | No FKs; no retention. |

### 1.4 Routes and authorisation

| Route | AuthN | AuthZ check | Verified cross-tenant |
|---|---|---|---|
| `POST /api/auth/register`, `/login` | none | rate limit by IP (`auth.py:33-36`) | n/a |
| `GET /api/auth/me`, `PUT /update_email` | JWT | self; password re-check on email change (`auth.py:72`) | n/a |
| `POST /api/documents/upload` | JWT | tenant from the user | n/a |
| `GET /api/documents/list` | JWT | `tenant_id` filter (`documents.py:56-59`) | empty for Bob ✓ |
| `GET /api/documents/{id}` | JWT | `_own_doc` tenant (`documents.py:22-26`) | 404 ✓ |
| `GET /api/documents/{id}/page/{p}/image` | JWT | `_own_doc` + `chunk.document_id == doc.id` (`:76-84`) | 404 ✓ |
| `POST /api/documents/{id}/extract` | JWT | `_own_doc` | 404 ✓ |
| `DELETE /delete/{id}`, `PUT /edit/{id}`, `POST /save/{id}` | JWT | `_own_doc` | 404 ✓ (×3) |
| `POST /api/chat/query`, `/stream` | JWT | session by `user_id` (`chat.py:35`); docs by tenant (`rag.py:226-232`); index per tenant | 404 / `error` event ✓; unscoped query cites nothing of Alice's ✓ |
| `GET /api/chat/sessions`, `/messages/{sid}`, `DELETE`/`PUT /sessions/{sid}` | JWT | `user_id` | 404 ✓ |
| `/api/chat/save_response`, `/saved_items[/{id}]` | JWT | `user_id` | code read |
| `GET /api/intel/graph`, `/timeline`, `/overview`, `/audit`; `POST /eval` | JWT | `Entity.tenant_id` / `QueryLog.tenant_id` / index per tenant | empty for Bob ✓ |
| `GET /api/intel/capabilities` | **none** | — | public (M9) |
| `POST /api/vision/analyze` | JWT | stateless | n/a |
| `/api/health`, `/api/test`, `/docs`, `/openapi.json`, `/{path}` (SPA) | none | SPA resolves and checks `_DIST in parents` (`main.py:92-93`) | `%2e%2e`, `..%2f`, `/assets/../..` all return index.html ✓ |

Isolation is consistent: documents are scoped by tenant and chat by user. That only stays correct while there is one user
per tenant. The legacy `default` tenant (H1) breaks this assumption today, and org workspaces will break it later.

---

## 2. Feature reality matrix

| Capability | Status | How verified / evidence | Heuristic vs learned, and the limit it imposes |
|---|---|---|---|
| PDF text extraction (per page) | **Works** | Tests; probe (30 pages → 240 chunks) | PyMuPDF (AGPL). `find_tables` costs 0.44 s per page. |
| OCR / vision pipeline for scans | **Partial** | EasyOCR probe: 2,834 chars, conf 0.57, 39–47 s per page on CPU; Tesseract not installed locally (it is in the Dockerfile) | Classical OpenCV preprocessing plus off-the-shelf OCR. No handwriting, no per-block OCR, no word boxes stored. EasyOCR-only deployments are far too slow. |
| Layout / table detection (images) | **Partial (heuristic)** | `test_cv_quality_layout_and_skew` (synthetic ruled table) | Morphology only (`cv.py:145-188`): ruled tables need ≥ 4 joints, figures are "tonal density". Borderless tables and multi-column reading order are not handled. Results are counted, not used. |
| Native PDF tables → Markdown | **Works / partial** | Code path; PyMuPDF `find_tables` | Appended as duplicate text (L3). |
| DOCX parsing | **Works (code)**; untested | No test | Single "page", so every citation says page 1. |
| Image upload → OCR + caption | **Partial** | OCR path probe; caption untested (needs a vision LLM) | Captions send the raw image to a third party (M16). |
| Hybrid retrieval BM25 + dense + RRF | **Works** | `test_hybrid_index_search_and_filter`; probes | Sound design. Pure-Python BM25 and an in-memory index: 665 ms per query at 20k chunks; 29 s rebuild (H8). |
| Cross-encoder rerank | **Untested / partial** | Disabled in tests (`conftest.py:12`) and probes | Loads in the background and is never awaited, so early requests are not reranked. `ms-marco` training data is MS MARCO (check terms for commercial use). |
| MMR diversity | **Works (code)**; no direct test | `retrieval.py:186-200` | Fine. |
| GraphRAG-lite | **Partial (heuristic)** | Code; trace step visible in probes | Substring match of entity names in the question, then +≤ 4 chunks. Loads up to 3,000 entities per query (121 ms). Neighbours come from co-occurrence, not semantic relations. |
| Knowledge-graph extraction | **Partial (heuristic)**; LLM mode untested | Unit and API tests; probes: missed "Satya Nadella", "Sundar Pichai", "Redmond", "Delaware"; 'usa' counted 5× vs 2 | Regex, gazetteers and capitalisation. "Relations" are co-occurrence counts unless an LLM is configured. |
| Claim verification / groundedness | **Broken (non-discriminative)** | `probe_ml.py`: 6/6 false claims "supported" | Embedding similarity and lexical overlap can't check facts. The deep-mode LLM judge is untested. |
| Confidence | **Placeholder-grade heuristic** | `rag.py:200-208` | 0.4·retrieval + 0.4·support + 0.2·cited, never calibrated. Inherits C4. The "calibrated" label (README, CONCEPTS §3.4) is inaccurate. |
| Abstention | **Partial** | Off-topic offline: `abstained=false`, conf 0.71 | A flag only; the answer is still shown. Triggers on regex "not found" phrases or conf < 0.25. |
| Pixel-level PDF highlights | **Works for text-layer PDFs** | `test_pdf_provenance…` asserts > 0 boxes | None for scans, DOCX or images; re-rendered on every request. |
| Timeline / deadlines | **Partial** | API test + browser (2 dates shown correctly) | 4 date formats; ambiguous parsing (M7). |
| Audit trail | **Partial** | API test + System page | Hash-only and not append-only (M11). |
| Structured extraction | **Partial**; LLM path untested | API test (offline: keys present only) | The offline fallback never returns null (M15). |
| Document classification | **Partial (heuristic)** | Unit test + browser ("Legal contract · 80%") | Zero-shot prototype cosine. The "confidence" is softmax at temperature 1/20, not a probability. |
| Summaries | **Works (extractive)**; LLM path untested | Browser | Centroid extractive summary. |
| PII detection | **Partial (heuristic)** | Unit test; probe: no names, DOB, passport or UK NI detected; invoice numbers flagged as cards; build ids flagged as IPs | Regex + Luhn. Detection only: `redact()` is unused (M16). |
| Prompt-injection defence | **Partial / weak** | Unit test; probe: 3/6 variants missed | Regex blocklist plus a system-prompt rule (H7). |
| Topic clustering | **Partial**; untested | Needs ≥ 3 docs | KMeans on mean chunk vectors, recomputed on every dashboard load. Meaningless under hashing embeddings. |
| Retrieval evaluation | **Partial (biased)** | `test_eval_endpoint` (range check only) | Pseudo-queries are the chunk's own highest-IDF tokens (`evaluation.py:20-24`): lexical leakage favours BM25 and inflates hit-rate. A smoke metric, not a benchmark. |
| Multi-provider LLM gateway | **Untested live** | Parsers verified with canned Anthropic/OpenAI/Gemini/Ollama payloads; no HTTP contract tests | Raw HTTP; breaker flaws (M3); unverified default model ids (L9). |
| Streaming SSE | **Works** | API test; browser (tokens, final, trace) | Fallback double-run (M1). |
| Offline / extractive mode | **Works** | All tests | Quality is "top passages", and the trust signals are meaningless in this mode (C4). |
| Auth (register / login / JWT) | **Works** | Tests; browser | Lifecycle gaps (M12, M13). |
| Frontend: Login, Register | **Works** | Browser: registration redirected to dashboard | Token in `localStorage` (`lib/storage.ts:25-29`). |
| Frontend: Dashboard | **Works** | Browser (overview cards, empty states) | Calls overview, which is heavy (M10). |
| Frontend: Upload / Library | **Works** | Browser render + list; upload exercised via API | Sequential uploads; 300 s timeout. |
| Frontend: Document page | **Works** | Browser: summary, keywords, entities, vision table, PII, flags, extraction form | Contains v1 fallback branches (L7). |
| Frontend: Chat | **Works** | Browser: streamed extractive answer, citations, claims, trace | "Grounded 2/2" badge inherits C4. |
| Frontend: Graph | **Works** | Browser: 6 entities, 6 relations rendered | Custom force layout; heuristic graph data. |
| Frontend: Timeline | **Works** | Browser | M7 parsing errors flow through. |
| Frontend: Vision Lab | **Partial** | Page renders; analysis tested via API only | Copy over-claims (L5). |
| Frontend: System | **Works** | Browser: capabilities, audit table | "Reproducible" claim (M11); eval not run in the UI. |
| Frontend: Settings | **Works (render)** | Browser | Email change only. No password change, account deletion or server-side logout. |

---

## 3. Correctness bugs and edge cases

- **Verification and confidence**: C4, M2. Coverage sampling gives every hit a score of 0.7, so summary answers get about
  0.28 confidence from retrieval strength alone (`rag.py:102`).
- **Streaming fallback double-run**: M1. Also, a client abort doesn't stop the server generator until the next yield, so the
  provider stream stays open (`chat.py:91-111`). Partial streams are persisted as complete (L10).
- **SQLite + threads**: `check_same_thread=False`, WAL, 30 s busy timeout (`models.py:17,28`). 4 concurrent same-tenant
  uploads with overlapping entities completed without errors (13.6 s), so the unique-constraint race on `entities`
  (`knowledge.py:160-164`) was not reproduced; it can still raise under real concurrency, and the failure is swallowed
  (`ingestion.py:86-91`: the document is kept with **no graph**). The duplicate-upload dedup check (`ingestion.py:33`) races
  the same way. The global index lock (`retrieval.py:223`) serialises rebuilds across tenants.
- **Index cache invalidation**: the fingerprint misses renames (M5). It is per-process: correct across workers because the
  fingerprint query runs on every request, but each worker holds a full copy of every tenant's index. Embedding-model
  churn rewrites stored vectors (M4). Mixed vector dimensions silently disable dense search for a tenant
  (`retrieval.py:283-287`, `matrix=None`).
- **Migrations**: additive only; no indexes on upgraded DBs (M6). Backfill runs at startup in a thread and lazily on
  `GET /documents/{id}`, which is a write inside a GET (`documents.py:68`). On the DB copy, backfilling 16 v1 docs took
  136 s (under load).
- **Error paths**: parser exceptions return 500 (L11); extraction returns 502 with provider text (M15). `int(payload["sub"])`
  raises a 500 on a non-numeric sub (`deps.py:15`). A malformed `pbkdf2_sha256$` hash raises a 500 (`security.py:27`).
  `HTTPBearer` returns **403** for a missing token, while the frontend handles only 401 (`api.ts:59`).
- **Retrieval details**: when nothing matches lexically or semantically, search falls back to the first chunks in document
  order (`retrieval.py:159-161`), which then look like evidence. Rerank only re-scores the first 40 candidates, then sorts
  together with un-reranked GraphRAG additions on a different scale (`rag.py:279-284`). Follow-up detection is a
  pronoun regex (`rag.py:49,249-252`).
- **Date parsing**: M7. The timeline is relative to server `date.today()` and ignores timezone.
- **Chunking**: L2, L3. DOCX and TXT are one "page". OCR pages keep `(OCR)` markers only in v1 data.
- **Stored originals**: `source_path` is stored as given (relative `./data/uploads/...` by default, `config.py:17`), so
  page images 404 if the server starts from another directory. Paths are id-based, so a crafted filename can't traverse
  (verified: `../../evil.txt` stored as `uploads/2/3.txt`).
- **Sessions**: orphan sessions on failed queries (L1). History can begin with an assistant turn if messages were filtered,
  which strict providers reject (`llm.py:139-145`).
- **Extraction**: field keys are rewritten (`invoice number` becomes `invoice_number`, `extraction.py:18`), so the response
  keys differ from what the client sent.

---

## 4. Security review

| Area | Finding | Refs |
|---|---|---|
| Tenant isolation | Correct on every endpoint and query path probed (15 checks). The model is "tenant = user"; the legacy shared tenant breaks it (H1). | §1.4; `rag.py:226-232`; `knowledge.py:218-241,311-328` |
| AuthN / JWT | HS256 via python-jose 3.3.0; 24 h expiry; no `iss`/`aud`/`jti`; no revocation, password change or reset, or account deletion. A random secret per process when unset (safe failure, but logouts on restart; breaks with multiple workers). | `security.py:36-47`; `config.py:69-73`; M12 |
| Live v1 deployment | Public default secret plus wildcard credentialed CORS (verified reflection). | C1 |
| Rate limiting | Auth only; per-process; keyed on proxy IP (likely). None on upload, query, eval or extract, which are LLM-cost endpoints. | M13; H3 |
| Upload validation | Extension allow-list only; no magic bytes; no page, pixel or decompressed-size limits; full multipart spooled before the size check (Starlette 0.41.3). Malicious PDFs reach the MuPDF C parser in-process (CVE surface; 1.23.7 is old). | H3; L11 |
| Decompression bombs | PNG/TIFF up to about 179 MP pass PIL (warning only). DOCX zip is unbounded. Vision Lab does cap at 40 MP / 15 MB (`vision.py:13-25`), but the document upload path does not. | `document_service.py:155-167` |
| Path traversal | SPA route is safe (resolve plus parents check, verified with 3 encodings). Stored originals use id-based names. | `main.py:86-95`; `ingestion.py:40-44` |
| SSRF / outbound | No user-controlled URLs. Outbound calls go only to configured LLM endpoints (`OPENAI_BASE_URL` and `OLLAMA_API_URL` come from env). An unauthenticated request can trigger the Ollama probe (M9). | `llm.py:69-123` |
| Secrets in repo | Tracked `.env.example`: all key fields empty. Tracked `frontend/.env.production`: one non-secret relative API base value. A history scan of all 28 commits found no provider-key patterns; the assignments it matched are placeholders. **The untracked local `.env` contains a DeepSeek key and a JWT secret** (gitignored, never committed). With no `.dockerignore` it would be sent in the Docker build context. | H4 |
| CORS (v2) | Explicit origin list from env with credentials; defaults to localhost. Same-origin SPA in production. OK. | `main.py:58-59` |
| XSS (frontend) | Custom Markdown renderer builds React elements with no `dangerouslySetInnerHTML`. Links are limited to http/https/mailto (`Markdown.tsx:209-216`). Images are never rendered, so markdown-image exfiltration is impossible. No unsafe sinks found (`grep`). The residual risk is a user clicking an attacker-supplied link in an answer. The JWT in `localStorage` would be exposed by any future XSS. | `Markdown.tsx` |
| Prompt injection | Regex detection plus context sanitisation plus a system rule (H7). No tools or agents exist, which limits the blast radius to answer manipulation. | `guardrails.py:79-110` |
| PII handling | Claims ("Responsible AI", "PII surfaced") vs reality: counting only; no redaction in any flow; raw content and images go to providers; queries are logged indefinitely; no names or addresses detected. | M16 |
| Info disclosure | `/api/intel/capabilities`, `/docs` and `/openapi.json` are public. Register reveals whether an email exists. | M9; M12 |
| Dependencies (Python) | Unpinned. PyMuPDF **AGPL** (H6). python-jose CVEs. EasyOCR pulls torch (about 1 GB). sentence-transformers and the MiniLM / ms-marco models are Apache-2.0 (the ms-marco model is trained on MS MARCO data; review its terms). OpenCV, Tesseract and EasyOCR are Apache-2.0; pdfplumber and python-docx are MIT. | `requirements.txt` |
| Dependencies (npm) | `npm audit`: 12 advisories in the prod tree (7 high: axios NO_PROXY SSRF (Node-side), form-data, picomatch, postcss, vite, nanoid, source-map-js), mostly build-time. react-router open-redirect advisories are moderate. All have fixes available. | `package.json` |

---

## 5. Performance and scalability (measured on the dev laptop, CPU only, MiniLM)

| Measurement | Result | Note |
|---|---|---|
| Test suite | 17 tests, 189.8 s | Dominated by model loading and EasyOCR. |
| Embedding throughput | 12–19 chunks/s (900 chars) | `embeddings.py:107-120`. |
| Ingest 30-page text PDF (isolated, profiled) | 43 s total: embed 19.8 s, `find_tables` 13.1 s, graph 7.1 s, extractive summary 3.2 s | 131 s when contended. Synchronous in the request (H2). |
| OCR one 1224×1584 page (EasyOCR) | 39–47 s warm; 130 s first call under load | A low-confidence result triggers a second OCR pass (`cv.py:270-273`). |
| Cold-start first upload (warm-up disabled) | 65 s | Torch / sentence-transformers import on the request path. |
| 20k chunks: insert / DB size | 32.8 s / 103 MB (about 5.1 KB per chunk, JSON vectors) | `models.py:109`. |
| 20k chunks: index rebuild | 29 s | Runs on the first query after any upload or delete, under a global lock. |
| 20k chunks: hybrid search / full offline answer | 665 ms / 1.7 s | Python BM25 loop (`retrieval.py:92-98`) plus O(N) dicts per query (`rag.py:274`, `retrieval.py:187`). |
| Cached `get_index` | 6 ms | The fingerprint query runs on every request. |
| Entity linking with 3,000 entities | 121 ms per query | Loads ORM rows and does a Python substring scan (`knowledge.py:315-317`). |
| Deployed v1 cold start | 42 s | Render free tier sleeps. |

**Ceilings:**

- Single process; each worker holds every tenant's index; SQLite single writer.
- The list and overview endpoints scale with total corpus size (M10).
- Practical limit is about 5–10k chunks per tenant before interactive latency degrades, and about 1 large upload at a
  time per instance.
- Memory: torch, MiniLM, the cross-encoder and EasyOCR together need about 1.5–2.5 GB RSS. This is an estimate from
  typical footprints; RSS was not measured.

---

## 6. Redundant / dead code and stale docs

| Item | Status | Action |
|---|---|---|
| `app/services/deepseek_client.py`, `ollama_client.py`, `local_llm.py`, `llama_manager.py` | Not imported by `app/`; superseded by `app/ai/llm.py`. `ollama_client` still uses `requests`, which is not in requirements. | Delete. |
| `app/services/rag_service.py` | v1 shim used only by `scripts/test_rag.py` and `verify_project.py`. | Delete with them. |
| `document_service.extract_text_from_file`, `save_document` (`:195-207`) | v1 compat, unused by the app. | Delete. |
| `scripts/` (19 files: llama-server downloaders, GGUF fetchers, `requests`-based e2e scripts against v1 routes, `try_providers`, `sample.pdf`) | v1-era. Only `fix_invalid_embeddings.py` and `inspect_db.py` are possibly useful. | Delete the rest; move useful ones to `tools/`. |
| `verify_project.py`, `setup_deployment.py`, `LAUNCH_BOT.bat`, `Procfile`, `railway.json` | v1 deploy and launch helpers. | Delete, or rewrite for v2. |
| `QUICKSTART.md` ("double-click LAUNCH_BOT.bat"), `PDF_OCR_SETUP.md`, `DEPLOYMENT_SUMMARY.txt` ("100% unchanged"), `# Code Citations.md`, `.github/copilot-instructions.md` | Stale and misleading. | Delete (keep the Code Citations content only as a licence-review note, L12). |
| `/api/test` endpoint (`main.py:75-77`) | Duplicate of health. | Delete. |
| Frontend v1 fallbacks (`DocumentPage.tsx:56-73`, `api.ts:75`), unused `documentsApi.save`/`rename` | Dead. | Remove. |
| `OllamaSetup.exe` (1.26 GB), `models/` (2.9 GB), `venv/`, `.venv/`, `.conda/` in the working dir | Ignored by git, but bloat the Docker context. | Remove, or add to `.dockerignore`. |
| Docs (`README`, `ARCHITECTURE`, `CONCEPTS`, `ROADMAP`) | Mostly accurate about mechanisms. They overstate "calibrated", "verified", "reproducible" and "covered by tests" (isolation tests cover 3 endpoints). | Correct the claims (see §2). |

---

## 7. Tests

**Covered (17 tests, all pass):**

- Auth validation.
- Upload lifecycle on a `.txt` file: classification, PII, dedup, list, delete.
- Cross-tenant checks on 3 endpoints (get, list, scoped query).
- Extractive Q&A, persistence, SSE event order, offline extraction keys, graph, overview, capabilities.
- Injection flagging, eval range, Vision Lab.
- PDF provenance: highlights > 0, 404 for an out-of-range page, timeline date, audit hash.
- Unit tests: PII and redaction, injection, chunking, BM25, hybrid index, hashing embeddings, rule NER, classification
  and keywords, CV layout and skew, annotation.

**Missing, most important first:**

1. **Groundedness-verifier adversarial tests** (wrong numbers, entities, negation, uncited claims). These must fail today.
2. **A cross-tenant matrix for every route**, including stream, extract, page image, edit, save, delete, sessions, saved
   items, graph and timeline `document_id`, and audit. Plus legacy-tenant migration tests.
3. **LLM gateway contract tests** with recorded fixtures per provider (JSON and SSE), breaker behaviour, failover, partial
   streams and vision routing.
4. **Upload hardening**: oversized files, page and pixel bombs, zip-bomb DOCX, malformed PDF (expect 400), wrong magic
   bytes.
5. Stream fallback idempotency, so a client retry doesn't double-run.
6. Index cache invalidation (rename, delete, model change, mixed dimensions).
7. Migration from a v1 DB snapshot (columns, indexes, backfill, page inference).
8. Date parser tables (US/EU, 2-digit years, month-year, ISO with slashes) and timeline filtering.
9. Concurrency: parallel same-tenant uploads (entity unique constraint), dedup race, SQLite lock behaviour.
10. Retrieval quality on a **labelled** set (not self-generated) with a regression threshold; reranker-on tests
    (`TEST_RERANKER`).
11. Frontend: no tests at all. Add unit tests for the Markdown renderer (XSS and link safety), the SSE parser, and the
    `normalizeAnswer` helper in `api.ts`; Playwright smoke tests for the 11 routes.
12. CI that builds from a clean checkout (would have caught C3) and runs `docker build`.

---

## 8. Stack claims vs code

| Claim | In local `main`? | Evidence |
|---|---|---|
| PostgreSQL | **No** (theoretically possible) | Any SQLAlchemy URL is accepted (`models.py:21`), but there is no driver in `requirements.txt` and it was never run. `render.yaml` declares an unused DB. On `origin/main` it appears only in `docker-compose.yml`, and that code used SQLite. |
| pgvector | **No** | Roadmap and docs only (`docs/ARCHITECTURE.md:117`, `ROADMAP.md:62`). Vectors are JSON text. |
| Redis | **No** | Not in local code. `origin/main:docker-compose.yml` defines a Redis service that the app never imports. |
| Docker | **Yes** | `Dockerfile` (2-stage). Build not executed (daemon off); see H4. |
| LangChain | **No** | Removed in `origin/main` commit `1dfe0de` ("removed langchain, faiss, chromadb"). Mentioned only in stale docs. |
| Ollama | **Yes** | HTTP provider `llm.py:101-106` (`/api/chat`), plus the dead `ollama_client.py`. |
| Multiple LLM providers | **Yes (untested live)** | Anthropic, OpenAI-compatible, Gemini, NVIDIA NIM, DeepSeek, Ollama (`llm.py:69-107`). |

---

## 9. Deployed app (`https://minddoc-ai-2.onrender.com`, read-only, unauthenticated)

- `GET /api/health` returned `{"status":"healthy","service":"MindDoc AI Backend","version":"1.0.0","database":"connected"}`
  after a 41.8 s cold start. `GET /api/test` returned 200.
- `openapi.json` reports `MindDoc AI 1.0.0` with v1 routes: auth, documents (incl. `upload_progress`, `statistics`), chat
  (incl. `/api/chat/upload`), `/api/notebook/notebook/*`, `/finetune/upload`, and duplicate un-prefixed `/auth/*`,
  `/documents/list`, `/chat/query`.
- **None of the v2 routes exist** (`/api/intel/*`, `/api/vision/*`, `/api/chat/stream`, `/api/documents/{id}`).
  `/api/intel/capabilities` returns the SPA HTML with 200, so unknown API paths are swallowed by the catch-all.
- `/docs` is public. The CORS preflight from `Origin: https://evil.example` returns
  `access-control-allow-origin: https://evil.example` and `allow-credentials: true`.
- The served SPA is the v1 bundle (`/assets/index-824f0160.js`, `vite.svg` favicon).
- **Conclusion:** production runs `origin/main` (April 2026, v1 lineage with OpenRouter). The audited v2 code has never
  been deployed.
- **Not checked:** I didn't log in, register or forge tokens, so whether `JWT_SECRET` is set (C1) is unknown.

---

## 10. Recommended refactoring (prioritised)

**P0: stop the bleeding (days)**

1. Set or rotate `JWT_SECRET` on Render and lock CORS on the live site.
2. Purge `data/uploads` and `app/indexes` from the public repo history; consider making the repo private (C1, C2).
3. Fix `.gitignore` for `frontend/src/lib`.
4. Tag `origin/main` as `v1-archive`, then decide explicitly to replace it with v2 (a force-push or a merge commit) (C3).
5. Add `.dockerignore`, pin dependencies, and fix the deploy target: Docker, persistent storage, secrets, ≥ 2 GB RAM, and
   no EasyOCR unless a GPU is available (H4, H5).
6. Relabel the trust UI as "heuristic support score" until the verifier is replaced. Remove "calibrated" and
   "reproducible" from the docs and UI (C4, M11).
7. Legacy-tenant migration (H1).

**P1: architecture (weeks)**

| Area | Keep | Refactor | Replace with | Why |
|---|---|---|---|---|
| API layer | FastAPI routers, `_own_doc` / tenant-filter pattern, SSE protocol (`session`/`trace`/`token`/`final`) | Pydantic request bodies everywhere; auth on capabilities; consistent 4xx mapping | — | Isolation logic is correct and simple. |
| Ingestion | Page-aware parse and chunk, dedup, trace of analysis steps | Split into idempotent stages | Job queue (Arq/RQ/Celery on Redis, or a Postgres-based queue) plus a sandboxed parser worker with page, pixel and time limits; progress over SSE | H2, H3. |
| Storage | SQLAlchemy models (mostly) | Alembic migrations; drop full text from hot rows | Postgres + **pgvector (HNSW)** + Postgres FTS (or a BM25 extension); object storage for originals | H8, M6, M10; removes the per-process index cache. |
| Retrieval | Hybrid + RRF + MMR design, reranker | Per-query timings; await reranker readiness | — (moved into the DB) | Measured and sound in principle. |
| Verification / confidence | Claim records schema, trace UI | — | NLI cross-encoder (e.g. DeBERTa-v3-MNLI) per claim and cited span, plus numeric/date/entity consistency, plus an optional LLM judge; calibrate on a labelled set (isotonic), report ECE | C4. This is the product's differentiator and currently doesn't work. |
| NER / graph / dates | Ontology tables, graph API, Timeline UI | Word-boundary mentions, batched upserts | spaCy or GLiNER NER; LLM relation extraction with evidence spans; `dateparser` with locale | M7, M8. |
| PII / safety | Luhn and IBAN validators, UI surfacing | Make redact-before-egress a policy option | Microsoft Presidio (MIT); red-team suite for injection | M16, H7. |
| PDF stack | `highlight` concept | Store word boxes (including OCR) for provenance | `pypdfium2` + `pdfplumber`, or docling (MIT) for layout and tables; Tesseract as default OCR, PaddleOCR/docTR optional | H6 (AGPL), L4, L5. |
| LLM gateway | Plain-HTTP adapters, StreamState, JSON repair | Breaker per error class; vision capability per model; contract tests | — (or LiteLLM if provider breadth grows) | M3, L9, L10. |
| Auth | PBKDF2 hashing | Account lifecycle | PyJWT; refresh and revocation; password reset; `DELETE /me`; org workspaces + RBAC; rate limits at the proxy or in Redis | M12, M13. |
| Frontend | Component library (`components/ui`), pages, safe Markdown, SSE client | Track the SSE session id; idempotent retry; remove v1 fallbacks; ESLint flat config | — | M1, L7, M14. |
| Eval | Endpoint and UI | — | Labelled gold set (questions → chunk ids and answers), faithfulness metric, CI regression gate | The current eval is biased toward BM25. |

**P2: delete:** everything in §6 (legacy services, `scripts/`, stale root docs, launcher and deploy files for v1, `/api/test`,
`OllamaSetup.exe`, frontend v1 branches).

---

### Could not verify

- Whether `JWT_SECRET` is set on Render (C1); any authenticated behaviour of the live site.
- Docker image build (daemon not running; H4 is from reading the Dockerfile and the `node_modules` contents).
- Any real LLM provider call (by instruction); the deep-mode planner, HyDE, LLM judge, LLM graph extraction, VLM
  captions and LLM-based extraction were never exercised.
- Tesseract path (not installed locally); cross-encoder reranker (disabled); Postgres compatibility.
- Memory footprint (RSS not measured); behaviour under real multi-user load.
