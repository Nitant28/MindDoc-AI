# MindDoc AI — Product Strategy & Roadmap

*Grounded in `docs/research/HACKATHON_WINNERS_RESEARCH.md` (Microsoft Imagine Cup, Google Solution Challenge / Gemini /
Kaggle, NVIDIA developer contests, Palantir AIP/Foundry/Ontology docs).*

## 1. What winners do, and where MindDoc already stands

| Pattern that wins | MindDoc today (v2.1) | Next move |
|---|---|---|
| A named user + measurable outcome | generic "any document" | pick a vertical pack (below), run a 3–5 user pilot, log minutes saved |
| Unstructured → structured | schema extraction, entities, timeline | typed vertical ontology (Contract → Party/Clause/Obligation/Deadline) |
| Trust, verification, explainability | citations, claim-level support, abstention, confidence, trace, **pixel-level page highlights** | dual-model cross-check, per-field confidence |
| Close the loop (insight → action) | – | **governed actions**: agent proposes, human approves (task, deadline, draft notice, export) |
| Human-in-the-loop | – | confidence-routed review queue |
| Measured results | self-supervised retrieval eval with ablations | public benchmarks (CUAD, FUNSD, SROIE, DocVQA), cost/doc, latency |
| Offline / edge / privacy | extractive mode, Ollama, local embeddings + reranker | benchmark local vs cloud; NVIDIA Jetson/RTX build |
| Multimodal | OCR + layout + VLM captions | signatures, stamps, checkboxes, handwriting, tamper detection |
| Sponsor-stack integration | provider-agnostic gateway (Claude, OpenAI/Azure, Gemini, NVIDIA NIM, DeepSeek, Ollama) | per-competition adapters (Azure AI Document Intelligence, Google Document AI, NVIDIA NeMo Retriever) |
| Platform, not just app | REST API + OpenAPI | MCP server so any agent can use MindDoc as a tool |

## 2. Positioning — one engine, three "ontology packs"

| Pack | User | Wedge | Best for |
|---|---|---|---|
| **C. KYC / compliance intelligence** (recommended for Palantir-style judges) | onboarding analysts at fintechs/NBFCs | cross-document consistency (name/address/amount/date), tamper flags, PII markings, case approve/reject with audit | enterprise judges, Imagine Cup startup track, defense/fintech recruiters |
| **B. Clinical-document copilot** | community clinics | scans → patient timeline, notes-vs-lab contradictions, PHI markings, fully offline | Google/Kaggle health & Gemma challenges, NVIDIA edge |
| **A. AI paralegal for SMEs** | SME owners, CA firms | obligation register, renewal timeline, playbook risk, redlines | broadest B2B pilot; differentiate from Legal SahAI (Google 2025 winner) with provenance + actions + offline |

Use synthetic/public data only for demos (MIDV-family IDs, Synthea records, CUAD contracts).

## 3. Roadmap

### Shipped in v2 / v2.1
- Multimodal ingestion: PDF text layer + page-level CV OCR fallback, DOCX, images, native tables → Markdown.
- CV pipeline: quality scoring, NL-means denoise, CLAHE, deskew, adaptive threshold, morphological layout
  (text/table/figure), OCR with confidence, VLM captions, Vision Lab.
- Retrieval: hybrid BM25 + dense, RRF, cross-encoder rerank, MMR, GraphRAG-lite, self-healing index.
- Agentic RAG: rewrite, decomposition, HyDE, summary-intent coverage sampling, cited streaming answers.
- Trust: claim-level groundedness, LLM judge (deep mode), calibrated confidence, abstention, trace,
  prompt hash + chunk-id provenance, audit trail, **pixel-level PDF citations**.
- Ontology: entities + typed relations, entity resolution by normalisation, knowledge-graph explorer, date timeline.
- ML analytics: zero-shot classification, KeyBERT-style keyphrases, extractive summaries, K-Means + c-TF-IDF topics,
  readability, self-supervised retrieval evaluation with ablations.
- Responsible AI: PII detection (Luhn-validated cards, PAN/Aadhaar…), prompt-injection detection + sanitisation,
  per-user workspaces, rate-limited auth, stronger password hashing.
- Platform: provider-agnostic LLM gateway with circuit breaker, single-container deploy, 17 automated tests.

### Next 2–3 weeks (P0 for a finals demo)
1. **Vertical ontology pack** (pick C, B or A): typed object schema + extraction with per-field confidence.
2. **Review queue**: fields below a confidence threshold go to a human; accept/edit/reject is stored as training data.
3. **Governed actions**: `ProposedAction` objects (create deadline, export CSV, draft notice, open ticket), approve → execute → audit.
4. **Benchmarks page**: run CUAD / FUNSD / SROIE subsets; extraction F1, recall@k, faithfulness, latency, cost/doc.
5. **Markings + role-aware retrieval**: PII/PHI tags on chunks, redaction by role at query time.
6. **Bounding boxes for OCR pages**: store OCR word boxes so scanned pages get highlights too (PDF text pages already do).

### Next quarter (P1 differentiators)
- Cross-document contradiction detection (invoice vs PO vs contract; ID vs statement).
- Tamper/forgery signals: error-level analysis, copy-move, font inconsistency, metadata anomalies.
- Learned layout + table models (DocLayNet-YOLO / Table Transformer / LayoutLMv3), signature & stamp detection.
- Extraction-strategy lab: OCR-only vs VLM vs OCR+VLM per document type, chosen by measured quality/cost.
- Agentic deep-research memos (planner → retriever → critic → writer) with citations.
- MCP server + webhooks; background ingestion queue with progress events; Postgres + pgvector.

### Later (P2)
- Active learning: reviewer corrections fine-tune a small extractor (Donut/LayoutLM) — show accuracy over time.
- Mobile capture with live quality gating ("too blurry — retake"), dewarping, Indic OCR, voice Q&A.
- Red-team suite with attack-success-rate metric; model card; SOC2-style controls (SSO, RBAC, retention).
- Edge build: TensorRT-optimised OCR + embeddings on NVIDIA Jetson; quantised local LLM benchmarks.

## 4. Three-minute finals demo script

1. **0:00 Persona + pain** (15 s): "Priya reviews 40 KYC files a day; each takes 25 minutes."
2. **0:15 Upload a messy scan** → Vision Lab shows quality, deskew, detected tables → document card: type, PII, flags.
3. **0:45 Hidden attack**: a PDF containing "ignore previous instructions" is flagged at upload and neutralised.
4. **1:00 Hard cross-document question (Deep mode)** → trace streams (plan → hybrid retrieve → graph → rerank →
   verify) → answer with per-claim support badges → click `[2]` → the exact sentence highlighted on the page.
5. **1:45 Knowledge graph + timeline**: entities linked across files; "what's due in the next 90 days?"
6. **2:10 Measured, not claimed**: System page → retrieval eval (hybrid vs dense vs BM25) → audit trail with
   prompt hashes.
7. **2:30 Privacy**: unplug Wi-Fi / switch to Ollama → still answers with citations.
8. **2:45 Close**: metrics slide (accuracy, faithfulness, latency, cost/doc, pilot minutes saved) + architecture.

## 5. Resume / interview framing

> Built MindDoc AI, a glass-box document-intelligence platform: multimodal ingestion with an OpenCV/OCR pipeline,
> hybrid retrieval (BM25 + dense + RRF + cross-encoder + MMR) with self-supervised evaluation, an entity/relation
> ontology powering GraphRAG, and an agentic RAG pipeline with claim-level verification, calibrated confidence,
> pixel-level citations and a full audit trail — provider-agnostic across Claude, OpenAI, Gemini, NVIDIA NIM and
> local models, with an offline mode.
