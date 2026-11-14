# MindDoc AI — User & Operator Manual

## 1. Install and run (Windows, macOS, Linux)

**Prerequisites:** Python 3.11+, Node.js 20+. Optional: Tesseract OCR, Ollama (local LLM), an LLM API key.

```bash
# backend
pip install -r requirements.txt -r requirements-ml.txt   # ML extras: MiniLM embeddings, reranker, EasyOCR
cp .env.example .env            # then set JWT_SECRET and at least one LLM key (optional)
python run_server.py            # http://127.0.0.1:8000  (API docs at /docs)

# frontend (second terminal)
cd frontend
npm install
npm run dev                     # http://127.0.0.1:5173
```

**Single-process mode:** `cd frontend && npm run build`, then `python run_server.py` serves the UI and the API on
port 8000.

**Docker:** `docker build -t minddoc . && docker run -p 8000:8000 -v minddoc-data:/data --env-file .env minddoc`
builds the slim image (Tesseract, offline hashing embeddings; fits 512 MB hosts). Add
`--build-arg INSTALL_ML=true` for MiniLM embeddings + the reranker, pre-downloaded so the container runs offline
(needs ~2 GB RAM). The database and uploaded originals live in `/data` — mount a volume there.

**Render:** `render.yaml` deploys the Docker image, generates `JWT_SECRET` automatically and reads
`OPENROUTER_API_KEY` from the dashboard. On the free plan `/data` resets on each deploy; see the comment in the file.

**Tests:** `python -m pytest tests -q` (runs fully offline in an isolated temp database).

## 2. Choosing an AI provider

MindDoc works in three tiers — pick per your privacy and budget needs:

| Tier | Configure | What you get |
|---|---|---|
| Offline / zero-egress | nothing | extractive answers with citations, all CV/ML features, graph (rule-based) |
| Local LLM | install Ollama, `ollama pull llama3.1`, `ollama serve` | generative answers, nothing leaves the machine |
| Cloud LLM | one of `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `GEMINI_API_KEY`, `NVIDIA_API_KEY`, `DEEPSEEK_API_KEY` | best quality, deep mode, LLM graph extraction, image captions, LLM-judge |

`LLM_PROVIDER_ORDER` sets priority; a failing provider is skipped for 60 seconds automatically.
Check what's live on the **System** page or `GET /api/intel/capabilities`.

## 3. Using the app

### Dashboard
KPIs for your workspace (documents, chunks, entities, relations, queries, average evidence score and latency, PII found),
document-type breakdown, automatically discovered **topic clusters**, recent questions and the document list.

### Upload
Drag in PDFs (digital or scanned), Word files, images (photos of documents, screenshots, receipts) or text.
Each upload returns an analysis card: detected type, summary, scan quality, how many pages needed OCR, PII found and
any **security flags** (e.g. a hidden prompt-injection). Re-uploading the same file is detected and de-duplicated.

### Document page
Summary, type + confidence, reading stats, weighted keywords, extracted entities, PII summary, per-page vision report
(text layer vs OCR, OCR confidence, blur, skew, tables/figures). **Structured extraction:** define fields
(name + description) and get a JSON record — e.g. `parties`, `effective_date`, `total_value` from a contract.

### Chat
- **Scope:** whole workspace, or one/several documents.
- **Fast mode:** single hybrid retrieval pass, lowest latency. **Deep mode:** query planning, sub-questions, HyDE,
  LLM fact-check — use for complex or multi-part questions.
- Every answer shows **citations** (click `[n]` to jump to the source snippet with file and page), an **evidence
  score** (uncalibrated — not a probability), a **claim check** and the full **reasoning trace**.
- **Claim check:** each sentence is compared with the passage it cites.
  - **Red, "contradicts source":** a number, amount scale (lakh/crore), date, ID, payment period or party name
    doesn't match the source, or the sentence isn't in the source. The reason is shown under the sentence.
  - **Amber, "check wording":** a heuristic thinks negation, direction (rose/fell, credit/debit) or who-did-what
    may differ. These hints are often wrong (43% of correct sentences got one in testing), so read the source.
  - **Green:** no inconsistency found, which is not proof. On the benchmark the red tier caught 68% of planted
    errors. Always open the cited source for consequential facts.
- Follow-up questions keep context ("what about its renewal terms?").
- Ask "summarise this document" to get coverage-based summaries instead of similarity search.

### Cases and your organisation
- **Settings → Organisation:** admins create invitation links (optionally for one email address) and pass them on
  themselves; MindDoc sends no email. The colleague opens the link and registers. Admins can change roles and
  deactivate members.
- **Cases:** create a case for each engagement; you become its lead. Add members by email with a role: viewer (read),
  analyst (upload, resolve parties, draft and propose findings), reviewer (also approve or reject findings, issue
  reports and disclosure copies) or lead (also members and settings). Only members see a case.
- The **case switcher** in the header chooses the case that Documents, Parties, Findings and Chat work in. The
  General case is open to the whole organisation.

### Findings, reports and disclosure copies
- A finding's page shows its **robustness**: which independent sources it rests on. "Rests on one source" means
  removing that one statement (or its copies) leaves a supporting claim without evidence.
- A report can be downloaded as its frozen JSON or as an **evidence bundle** (zip with row images, sources and a
  SHA-256 manifest).
- **Disclosure copy:** for a recipient such as the borrower. Tick the subjects of the report (account holders are
  pre-ticked); other people's names and identifiers are withheld and listed with reasons. Check the withheld list
  before sending: whether it is legally sufficient is your decision.

### Knowledge Graph
Entities (people, organisations, places, dates, money, laws…) and their relationships across all documents.
Filter by type, search, drag nodes, click for details and linked documents. Filter to one document with
`/graph?document=ID`.

### Vision Lab
Upload any image to see what the AI sees: annotated text/table/figure regions, quality gauges, deskew angle, OCR text
with confidence, and a vision-LLM description (if configured). Great for demos and for diagnosing bad scans.

### System
Live capability status (providers, embeddings, reranker, OpenCV, OCR engines, vision LLM) and a one-click
**retrieval evaluation** that reports Hit-Rate@5 and MRR for hybrid vs dense-only vs BM25-only on your own data.

## 4. Configuration reference (`.env`)

| Variable | Default | Meaning |
|---|---|---|
| `JWT_SECRET` | random per start | **set this** or users are logged out on every restart (known default values are rejected) |
| `DATABASE_URL` | `sqlite:///./minddoc.db` (Docker: `sqlite:////data/minddoc.db`) | any SQLAlchemy URL; Postgres is the planned production store (ADR-0002) |
| `CORS_ORIGINS` | localhost:5173/5174 | comma-separated allowed origins |
| `LLM_PROVIDER_ORDER` | `anthropic,openai,openrouter,gemini,deepseek,ollama` | provider priority (`nvidia` is appended if its key is set) |
| `*_API_KEY`, `*_MODEL` | – | per-provider credentials and model ids |
| `OPENAI_BASE_URL` | OpenAI | point at Azure OpenAI / vLLM / LM Studio / Groq |
| `EMBEDDING_MODEL` | MiniLM-L6-v2 | any sentence-transformers model (vectors auto-migrate) |
| `ENABLE_RERANKER` | `true` | cross-encoder reranking (falls back silently if the model can't load) |
| `STORAGE_DIR` | `./data/uploads` | where originals are kept for page-highlight citations |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | 900 / 150 | chunking granularity (chars) |
| `RETRIEVAL_TOP_K` | 8 | sources passed to the LLM |
| `OCR_ENGINE_ORDER` | `tesseract,easyocr` | OCR preference |
| `TESSERACT_CMD` | – | path to `tesseract.exe` on Windows |
| `ENABLE_VISION_CAPTIONS` | `true` | describe images with a vision LLM |
| `MAX_UPLOAD_MB` | 50 | upload size limit |
| `MAX_PDF_PAGES` / `MAX_IMAGE_PIXELS` / `MAX_DOCX_UNCOMPRESSED_MB` | 500 / 40,000,000 / 200 | parsing caps (reject with HTTP 400) |
| `RATE_UPLOAD_PER_MIN` / `RATE_QUERY_PER_MIN` / `RATE_EVAL_PER_MIN` | 30 / 60 / 5 | per-user limits (HTTP 429); per process, not shared between replicas |
| `ENABLE_NLI_VERIFIER` | `false` | add the LettuceDetect NLI model to the claim check (needs ML extras; downloads ~275 MB) |
| `VERIFIER_NLI_THRESHOLD` | 0.95 | NLI probability that triggers a "check wording" flag |

## 5. Troubleshooting

| Symptom | Fix |
|---|---|
| "Extractive answer – no LLM is configured" | add an API key or start Ollama; check System page |
| Scanned PDF returns little text | install Tesseract (`winget install UB-Mannheim.TesseractOCR`) or rely on EasyOCR; check page quality in the document's vision table |
| First question is slow | embedding/reranker models load once (~5–10 s); warm-up runs in the background at startup |
| Logged out after restart | set `JWT_SECRET` in `.env` |
| Old documents lack insights | opened documents are backfilled automatically; startup backfills all legacy docs in the background |
| `429 Too many attempts` / `Rate limit reached` | auth: 10/min per IP; upload 30, questions 60, evaluation 5 per minute per user — wait a minute |
| Upload rejected with "limit" in the message | the file exceeds a page, pixel or size cap; split it or raise the cap in `.env` |

## 6. Upgrading from v1

- Database columns/tables are added automatically on start (no data loss). Legacy chunks without valid vectors are
  re-embedded on first query (this repairs a v1 bug that silently dropped every embedding).
- Users created in v1 remain in the shared `default` workspace; new users get private workspaces.
- All v1 endpoints still work; see `docs/API_CONTRACT.md` for v2 additions.
