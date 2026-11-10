# A — Repository audit at commit `ee814b0` (2026-11-10)

**Scope.**
- **Code:** `main` and `consolidate/v2-base` both point to `ee814b0` ("Claim verifier v2 …"). Five doc-only fixes and
  `docs/review/` are uncommitted on top.
- **Prior audit:** `docs/audit/CURRENT_STATE_AUDIT.md` is the pre-Phase-0 audit of v2.0. This one supersedes it for
  the current code and records what changed since.
- **Method:** every finding names how it was checked: **code** (read the source), **test** (ran it), **live** (probed
  https://minddoc-ai-2.onrender.com), **CI** (GitHub Actions run on `ee814b0`) or **not verified**.

## 1. Summary

| Area | State | Biggest risk |
|---|---|---|
| Correctness of answers | Better than v2.0: claim verifier v2 catches value errors; the evidence score is uncalibrated | meaning errors (negation, swapped parties) only get amber hints |
| Data durability | **Weak**: SQLite in the container; the live free plan wipes data on every deploy and restart | no persistence, no backups, no migrations |
| Scalability | Single process: in-memory index, rate limits and caches; ingestion runs inside the request | a second worker or replica breaks consistency |
| Security | Basics in place (PBKDF2, JWT, tenant filter, caps, rate limits) | old commits with personal documents still public via PR #1 refs; live `JWT_SECRET` not verified |
| Licences | **PyMuPDF (AGPL-3.0) in the default build** | blocks closed-source distribution and on-premise installs |
| Domain fit (Indian fund-flow forensics) | **Not started**: no transaction model, no money type, no statement parser, no identifier validation | the flagship capability doesn't exist yet |
| Engineering hygiene | Good: 32 tests, 3-job CI including a Docker boot test, lint clean of errors | no Postgres in tests; no load or perf tests |

## 2. Findings

Severity: **S1** blocks the target product or is a security exposure · **S2** must fix before a paying pilot ·
**S3** quality debt.

### 2.1 Security and privacy

| # | Finding | Sev | Evidence |
|---|---|---|---|
| A1 | The 14 personal documents purged from branch history are still served through GitHub's read-only `refs/pull/1/head`. An anonymous API call listed `data/uploads` at old commit `6f4a21b` (HTTP 200). The repo is public | S1 | live (GitHub API) |
| A2 | The live `JWT_SECRET` value is unknown. A token signed with the v1 default `supersecretkey` is rejected (401), so the default isn't in use. Either a strong secret is set or v2 generates an ephemeral one (sessions reset on restart) | S2 | live; dashboard **not verified** |
| A3 | Rate limits and the auth limiter are in-memory per process (`app/core/security.py`). They reset on restart and aren't shared across replicas | S2 | code |
| A4 | PII is detected, not redacted (`guardrails.redact` has no callers). Documents, chunks and answers store PII in plain text; the database isn't encrypted beyond the host | S1 for the lending market | code |
| A5 | Users from v1 share the `default` tenant (`init_default_tenant`). There's no RBAC, no case-level access control, and no SSO | S2 | code |
| A6 | `query_logs` and `chat_messages.meta_json` give provenance (prompt hash, chunk IDs), but there's no tamper-evident audit chain and no reviewer-action log | S2 | code |
| A7 | Tokens last 24 h with no revocation or refresh, and there's no account lockout beyond the rate limit | S3 | code |
| A8 | CORS: a foreign-origin preflight is rejected (HTTP 400). Same-origin UI | OK | live |

### 2.2 Data, durability, scale

| # | Finding | Sev | Evidence |
|---|---|---|---|
| A9 | SQLite is the store. Schema changes come from `_auto_migrate()` adding columns at startup; there's no Alembic, so renames and type changes are impossible | S1 | code |
| A10 | The live service runs on Render's free plan with no disk: the database and uploads reset on each deploy and restart | S1 for a pilot | `render.yaml`, live |
| A11 | Ingestion is synchronous inside `POST /upload`: parse → OCR → embed → analyse → graph. There's no retry, progress or dead-letter handling, and a 500-page scanned PDF blocks a request for minutes | S1 | code |
| A12 | The retrieval index is a per-process NumPy cache rebuilt lazily from JSON-text vectors (`app/ml/retrieval.py`). It's correct for one process only | S2 | code |
| A13 | No backups, no monitoring or error tracking, no structured logs, no health beyond `/api/health` | S2 | code |

### 2.3 Correctness and evidence

| # | Finding | Sev | Evidence |
|---|---|---|---|
| A14 | **No money type.** Amounts appear only inside text and the verifier, which parses them as Python `float`. A reconciliation engine needs exact integer paise | S1 for E | code |
| A15 | No transaction, statement or account model. Bank statements are stored as text chunks like any other document | S1 | code |
| A16 | Citations are page plus text snippet. Region bounding boxes are stored only implicitly (PyMuPDF search at render time), so **scanned pages can't be highlighted** | S1 | code (`app/vision/highlight.py`) |
| A17 | Claim verifier v2: held-out catch 68% and false flags 11% on 146 synthetic, developer-written claims. Meaning errors are amber-only | S2 | test (`benchmarks/reports/HALLUCINATION_BENCHMARK.md`) |
| A18 | The evidence score is a fixed weighted heuristic and isn't calibrated | S2 | code |
| A19 | Co-occurrence edges are stored in `relations` with `relation="co_occurs"` and drawn as graph edges next to typed relations. The UI shows the label but treats them alike, contrary to the data-model principle "co-occurrence is not a relationship" | S2 | code (`knowledge.py:184`, `Graph.tsx`) |
| A20 | Entity resolution is exact match on normalised names only. There's no validation of identifiers (GSTIN, PAN, CIN, IFSC) | S1 for the target market | code |
| A21 | The relevance gate and NLI choice were tuned on a dev split; the NLI path is off by default and untested in CI (the model isn't cached in CI) | S3 | code, CI |

### 2.4 Licences and dependencies

| # | Finding | Sev | Evidence |
|---|---|---|---|
| A22 | `pymupdf` (AGPL-3.0) is in `requirements.txt`. It's used for PDF text, tables, rendering and highlights | S1 for distribution | code; licence verified earlier |
| A23 | EasyOCR (optional) is stagnant. Tesseract is the default OCR in Docker | S3 | prior research |
| A24 | Frontend: `vite` and `@babel/helper-validator-identifier` sit in `dependencies` rather than `devDependencies`; 2 moderate `npm audit` advisories need React Router 7 | S3 | code |

### 2.5 Tests, CI and docs

| # | Finding | Sev | Evidence |
|---|---|---|---|
| A25 | 32 pytest tests pass (API end to end, tenancy, caps, rate limits, verifier, benchmark regression guard). CI runs backend, frontend and a Docker boot plus smoke test at 512 MB (about 162 MiB used) | OK | test, CI |
| A26 | No tests against Postgres, no migration tests, no load or performance tests, no frontend unit tests | S2 | code |
| A27 | 72 references in `docs/research/` are tagged [K] (from memory, unverified) | S2 for any publication | docs |
| A28 | `docs/ROADMAP.md` is marked superseded. The doc inconsistencies found in this review (README "calibrated confidence", manual defaults, architecture diagram, PII "redact available") were corrected | fixed, uncommitted | docs |

## 3. What changed since the pre-Phase-0 audit

**Fixed**
- Forgeable JWT default.
- Unbounded uploads: page, pixel, DOCX and size caps.
- No rate limits on expensive endpoints.
- Broken lint and CI.
- Dead code.
- Overclaiming UI labels.
- Personal files in branch history (but see A1).
- v1 checker passing 6/6 planted errors: v2 now catches value errors, measured.

**Still open:** A1, A4, A9–A16, A20, A22. These are exactly what Phases 1, 3 and 4 of the backlog address, and the
reason deliverables E, F and G exist.

## 4. Not verified in this audit

- Render dashboard settings: environment variables, plan, region.
- GitHub repository settings: branch protection, secret scanning.
- Behaviour on real (non-synthetic) Indian bank statements: none were used, by design.
- Throughput on large scanned PDFs on the 512 MB instance.
