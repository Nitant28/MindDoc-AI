# MindDoc AI

**Glass-box document intelligence.** Upload contracts, scans, invoices, papers or photos of documents. MindDoc
*sees* them (computer vision + OCR), *understands* them (ML analytics + a knowledge graph), and *answers* questions
with evidence you can check: numbered citations highlighted on the original page, a per-sentence claim check
(numbers, dates, IDs, parties against the cited source), an evidence score (uncalibrated) and a full reasoning trace.

It runs with Claude, OpenAI/Azure, OpenRouter, Gemini, NVIDIA NIM, DeepSeek or a local Ollama model. It also runs
**fully offline**, with no LLM at all.

---

## What's inside

| | Capability | Techniques |
|---|---|---|
| 👁 **Computer Vision** | scanned-page OCR, quality gating, layout | variance-of-Laplacian blur score, NL-means denoise, CLAHE, deskew (minAreaRect), adaptive threshold, morphological text/table/figure detection, Tesseract + EasyOCR (CRAFT + CRNN) with confidence, vision-LLM captions, **pixel-level citation highlights** |
| 📈 **Machine Learning** | search, analytics, evaluation | BM25, dense embeddings (MiniLM), Reciprocal Rank Fusion, cross-encoder reranking, MMR, zero-shot classification, KeyBERT-style keyphrases, K-Means + c-TF-IDF topics, extractive summaries, readability, self-supervised Hit@5/MRR with ablations |
| ✨ **Generative AI** | grounded answers and extraction | agentic RAG (rewrite → decompose → HyDE → retrieve → GraphRAG → rerank → generate → verify), streamed cited answers, claim verifier (number/date/ID/party consistency + wording heuristics, benchmarked) + LLM-as-judge, abstention, evidence score, schema-driven JSON extraction, GraphRAG-style entity + relation extraction, multi-provider gateway with circuit breaker |
| 🛡 **Responsible AI** | trust and safety | PII detection (Luhn-validated cards, SSN, IBAN, PAN/Aadhaar…), indirect prompt-injection detection + context sanitisation, per-user workspace isolation, audit trail with prompt hashes, rate-limited auth, PBKDF2-310k |

## Quick start

```bash
pip install -r requirements.txt -r requirements-ml.txt   # drop -ml for a slim install (offline embeddings, no reranker)
cp .env.example .env          # set JWT_SECRET; add any LLM key (optional)
python run_server.py          # API → http://127.0.0.1:8000/docs
```
```bash
cd frontend && npm install && npm run dev     # UI → http://127.0.0.1:5173
```
Or run everything in one container: `docker build -t minddoc . && docker run -p 8000:8000 --env-file .env minddoc`

Tests (offline, isolated DB): `python -m pytest tests -q`

## How an answer is made

```mermaid
flowchart LR
  Q[Question] --> P[Plan: rewrite · sub-queries · HyDE]
  P --> R[Hybrid retrieve: BM25 + dense → RRF]
  R --> G[GraphRAG: entity-linked chunks]
  G --> X[Cross-encoder rerank → MMR]
  X --> L[LLM: cited, streamed answer]
  L --> V[Verify each claim vs its sources]
  V --> C[Confidence · abstain · audit log]
```

## Current limitations (from the independent audit)

Read `docs/audit/CURRENT_STATE_AUDIT.md` before demoing. In short:
- The claim verifier (v2) catches wrong numbers, scales, dates, periods and party names. It only hints at flipped
  negation or swapped parties. On a small held-out test set it caught 68% of planted errors vs 20% for v1
  (`benchmarks/reports/HALLUCINATION_BENCHMARK.md`).
- Confidence is an uncalibrated weighted score.
- PII is detected but not redacted.
- Prompt-injection defence is pattern-based.
- Ingestion is synchronous.
- PyMuPDF is AGPL-3.0.

The fixes are planned in `docs/IMPLEMENTATION_BACKLOG.md`.

## Documentation

| Doc | For |
|---|---|
| [docs/audit/CURRENT_STATE_AUDIT.md](docs/audit/CURRENT_STATE_AUDIT.md) | independent audit: what works, what doesn't, security, licences |
| [docs/architecture/SYSTEM_ARCHITECTURE.md](docs/architecture/SYSTEM_ARCHITECTURE.md) | target architecture, layer by layer (proposal) |
| [docs/architecture/](docs/architecture/) | data model, event catalog, investigation engine, evaluation framework, security model |
| [docs/adr/](docs/adr/) | architecture decision records (proposed) |
| [docs/strategy/](docs/strategy/) | market selection, competitive analysis, product differentiation |
| [docs/IMPLEMENTATION_BACKLOG.md](docs/IMPLEMENTATION_BACKLOG.md) | prioritised build order with exit criteria |
| [docs/research/](docs/research/) | industry landscape, technology evaluation, papers, research gaps, benchmark datasets |
| [docs/PROJECT_CONTEXT.md](docs/PROJECT_CONTEXT.md) | **start here**: complete context (built vs planned, every concept and where it lives, measured results, gaps, how to build next) |
| [benchmarks/reports/HALLUCINATION_BENCHMARK.md](benchmarks/reports/HALLUCINATION_BENCHMARK.md) | claim verifier v1 vs v2: catch and false-flag rates, by error type, with caveats |
| [docs/MANUAL.md](docs/MANUAL.md) | install, configure providers, use every screen, troubleshooting |
| [docs/CONCEPTS.md](docs/CONCEPTS.md) | every CV / ML / GenAI concept explained, with file pointers and interview lines |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | system design, data model, design decisions, security, scaling path |
| [docs/API_CONTRACT.md](docs/API_CONTRACT.md) | REST + SSE API reference |
| [docs/ROADMAP.md](docs/ROADMAP.md) | product strategy, vertical positioning, roadmap, 3-minute demo script |
| [docs/research/HACKATHON_WINNERS_RESEARCH.md](docs/research/HACKATHON_WINNERS_RESEARCH.md) | Microsoft / Google / NVIDIA winners analysis and Palantir principles |

## Project layout

```
app/
  api/        auth · documents · chat (JSON + SSE) · intel (graph, timeline, audit, eval) · vision
  ai/         llm gateway · rag pipeline · knowledge graph · extraction · guardrails
  ml/         embeddings · hybrid retrieval · insights · evaluation
  vision/     CV pipeline · page highlighter
  services/   parsing · ingestion orchestration
  database/   SQLAlchemy models + auto-migration
frontend/     React + TypeScript + Tailwind
tests/        unit + end-to-end API tests
docs/         manuals, architecture, research, roadmap
```
