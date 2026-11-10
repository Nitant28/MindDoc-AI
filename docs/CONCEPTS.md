# MindDoc AI — Concepts Manual

A study guide to every Computer Vision, Machine Learning and Generative AI technique in this project:
**what it is → why we use it → where it lives in the code → how to talk about it in an interview.**

> Read this alongside the code. Each section names the file and function so you can jump straight in.

---

## Part 1 — Computer Vision (`app/vision/cv.py`)

### 1.1 Image quality assessment
- **What:** Score an image before trusting it. *Sharpness* = variance of the Laplacian (an edge detector). A blurry
  image has weak edges → low variance. *Exposure* = mean brightness; *contrast* = standard deviation of pixel intensity.
- **Why:** Garbage in, garbage out. A poor scan produces bad OCR, which produces wrong answers. We surface quality per
  page so a human knows which pages to re-scan — a *data-quality signal*, which enterprise buyers love.
- **Code:** `assess_quality()` → `{blur_score, brightness, contrast, score, quality}`.
- **Interview line:** "We compute variance-of-Laplacian per page and propagate a quality score into the UI, so
  low-confidence evidence is visible instead of silently degrading answers."

### 1.2 Preprocessing pipeline
| Step | Technique | Why |
|---|---|---|
| Grayscale | `cv2.cvtColor` | OCR works on luminance; 3× less data |
| Upscale | bicubic resize to ~1200px | OCR engines expect ~300 DPI glyph sizes |
| Denoise | Non-Local Means (`fastNlMeansDenoising`) | removes scanner speckle while keeping stroke edges |
| Local contrast | CLAHE (Contrast-Limited Adaptive Histogram Equalisation) | fixes uneven lighting / phone-photo shadows |
| Deskew | Otsu threshold → `minAreaRect` over ink pixels → rotate | tilted lines destroy OCR line segmentation |
| Binarise | Adaptive Gaussian threshold | handles gradients better than one global threshold |

- **Code:** `preprocess()`, `estimate_skew()`, `rotate()`.

### 1.3 Layout analysis (document structure without a deep model)
- **Text blocks:** dilate the inverted binary image with a rectangular kernel so characters merge into words,
  words into lines, lines into paragraphs; then `findContours` → bounding boxes, sorted into reading order.
- **Tables:** morphological *opening* with long horizontal and vertical kernels isolates ruling lines; their
  intersections (joints) confirm a grid. ≥4 joints ⇒ table.
- **Figures:** large regions with high ink density or rich mid-tones (photos/charts) rather than sparse strokes.
- **Code:** `detect_layout()`, visualised by `annotate()` (Vision Lab shows the boxes).
- **Upgrade path:** swap in a learned detector (LayoutLMv3, DiT, YOLO-doclaynet, Microsoft Table Transformer) —
  the interface (`list[{x,y,w,h,type}]`) stays the same.

### 1.4 OCR (Optical Character Recognition)
- **Tesseract:** classic LSTM-based OCR; we use `image_to_data` to get **per-word confidence**.
- **EasyOCR:** deep-learning OCR = CRAFT text *detector* + CRNN *recogniser* (CNN features → BiLSTM → CTC decoding).
- **Strategy:** try engines in `OCR_ENGINE_ORDER`; if confidence < 0.5 on the binarised image, retry on the
  deskewed grayscale and keep the better result (binarisation sometimes hurts clean scans).
- **Code:** `ocr()`, `ocr_page_image()`. In PDFs, only pages without a usable text layer are OCR'd
  (`document_service.parse_pdf`) — hybrid digital/scanned PDFs are handled page by page.

### 1.5 Vision-Language Models (multimodal GenAI)
- **What:** an LLM that accepts images (Claude, GPT-4o-class, Gemini, Llama-vision via Ollama).
- **Why:** OCR reads characters; a VLM *understands* charts, diagrams, photos and forms. We caption images so
  that a chart becomes searchable text ("bar chart of quarterly revenue, Q3 highest at $4.1M").
- **Code:** `caption_image()` → `llm.generate(images=[...])`.

### 1.6 Pixel-level provenance (`app/vision/highlight.py`)
- **What:** clicking a citation renders the original PDF page and draws boxes around the exact cited lines.
- **How:** the chunk is split into line fragments → PyMuPDF `page.search_for()` returns their rectangles in PDF
  coordinates → scaled by the render zoom → alpha-composited amber boxes with Pillow.
- **Why:** "show me where it says that" is the single most persuasive trust feature for analysts and judges.
- **Limit:** works on PDF pages with a text layer; scanned pages need stored OCR word boxes (roadmap).

---

## Part 2 — Machine Learning & Information Retrieval (`app/ml/`)

### 2.1 Chunking (`insights.chunk_pages`)
- Split on paragraph → sentence boundaries, pack to ~900 chars with 150-char overlap, **never across pages**
  so every citation has an exact page number.
- **Why overlap:** facts that straddle a boundary still appear whole in at least one chunk.

### 2.2 Dense embeddings (`embeddings.py`)
- **What:** a neural network (MiniLM, 384-d, sentence-transformers) maps text to a vector; semantically similar
  texts have high cosine similarity even with no shared words ("terminate" ≈ "end the contract").
- **Offline fallback:** a *feature-hashing* embedder (word uni/bi-grams + char tri-grams hashed into 384 signed
  buckets). Zero downloads, deterministic, surprisingly decent — the app never hard-fails.
- **Self-healing index:** each vector stores the model that produced it; stale/missing vectors are re-embedded
  automatically at index build (`retrieval._build`). (This fixed a real v1 bug where *all* vectors were being
  discarded because `numpy.float32` is not a Python `float`.)

### 2.3 BM25 (`retrieval.BM25`)
- **What:** the classic lexical ranking function behind search engines. Score = Σ IDF(term) × saturated TF,
  normalised by document length (k1=1.5, b=0.75).
- **Why both BM25 and dense?** Dense misses exact identifiers (invoice numbers, clause "12.3", names); BM25 misses
  paraphrases. **Hybrid beats either** — measure it yourself on the System page (`/intel/eval`).

### 2.4 Reciprocal Rank Fusion (RRF)
- **What:** combine ranked lists by Σ 1/(60 + rank). Rank-based, so you never have to calibrate BM25 scores
  against cosine similarities.
- **Code:** `WorkspaceIndex.search` (BM25 ⊕ dense) and `rag._fuse` (across sub-queries + HyDE).

### 2.5 Cross-encoder reranking
- **What:** a bi-encoder (embeddings) encodes query and passage *separately* — fast but shallow. A cross-encoder
  reads them *together* through full attention and outputs a relevance logit — slow but far more precise.
- **Pattern:** retrieve 40 candidates cheaply → rerank with `cross-encoder/ms-marco-MiniLM-L-6-v2` → keep the best.
- **Code:** `embeddings.rerank_scores`.

### 2.6 Maximal Marginal Relevance (MMR)
- **What:** greedy selection maximising `λ·relevance − (1−λ)·max_similarity_to_already_selected`.
- **Why:** stops the context window filling with five near-identical chunks; more *coverage* per token.
- **Code:** `WorkspaceIndex._mmr`.

### 2.7 Keyphrase extraction (KeyBERT-style)
- TF-IDF n-gram candidates (1–3 words) → re-score by cosine similarity to the whole-document embedding → MMR for
  diversity. **Code:** `insights.extract_keywords`.

### 2.8 Zero-shot document classification
- **What:** classify without training data. Embed a natural-language *description* of each class ("legal
  agreement with clauses, termination, liability…"), embed the document, pick the most similar prototype;
  a temperature-scaled softmax gives a confidence. **Code:** `insights.classify_document`.
- **Upgrade:** once users correct labels, train logistic regression on embeddings (few-shot → supervised).

### 2.9 Extractive summarisation
- Centroid / TextRank-style: embed sentences, score by similarity to the document centroid (+ small position prior),
  return the top sentences in original order. Used when no LLM is available. **Code:** `insights.extractive_summary`.

### 2.10 Topic discovery (unsupervised)
- Average chunk embeddings per document → **K-Means** (k ≈ √(n/1.5)) → label each cluster with **c-TF-IDF**
  (BERTopic's trick: treat each cluster as one document and find its distinctive terms).
- **Code:** `insights.discover_topics`, shown on the Dashboard.

### 2.11 Readability
- Flesch Reading Ease = 206.835 − 1.015·(words/sentence) − 84.6·(syllables/word). **Code:** `insights.text_stats`.

### 2.12 Retrieval evaluation (`evaluation.py`)
- **Self-supervised:** sample chunks, synthesise a query each chunk should answer (LLM question or *inverse cloze*
  pseudo-query of its rarest terms), check whether retrieval returns that chunk.
- **Metrics:** Hit-Rate@5 (is the right chunk in the top 5?) and **MRR** (mean of 1/rank). Reported for hybrid vs
  dense-only vs BM25-only — an ablation study in one click.
- **Interview line:** "We don't claim retrieval is good; we measure it, with ablations, on the customer's own data."
- **Caveat (know this before a judge asks):** inverse-cloze pseudo-queries are bags of a chunk's *rarest words*, which
  is exactly what BM25 is built for — so offline, BM25-only can score highest (on the v1 demo corpus: BM25 Hit@5 1.0,
  hybrid 0.90, dense 0.75). With an LLM configured, the eval writes natural-language *questions* instead, which is
  where dense + reranking earn their keep. Always say which query source produced a number.

---

## Part 3 — Generative AI (`app/ai/`)

### 3.1 Model-agnostic LLM gateway (`llm.py`)
- One interface over Anthropic Claude, OpenAI (+ any OpenAI-compatible endpoint: Azure, vLLM, Groq), Google Gemini,
  **NVIDIA NIM**, DeepSeek and local **Ollama**. Plain HTTP (httpx), so SDK version drift can't break us.
- **Circuit breaker:** a failing provider is skipped for 60 s; the next one serves the request.
- **Streaming** (SSE) for every provider, **JSON mode** + repair-retry for structured output, **vision** inputs.
- **Why:** vendor independence, cost/latency routing (`fast=True` uses the small model), and an *offline* story.

### 3.2 Retrieval-Augmented Generation (RAG) — the glass-box pipeline (`rag.py`)
```
plan → retrieve (hybrid, multi-query, HyDE) → graph expand → rerank → MMR → generate (cited) → verify → score
```
- **Query rewriting:** follow-ups ("what about its fees?") are resolved into standalone questions.
- **Query decomposition:** complex questions → up to 3 sub-queries, each retrieved separately, fused with RRF.
- **HyDE (Hypothetical Document Embeddings):** the LLM writes a *fake answer passage*; we embed that and search with
  it. Answers look more like documents than questions do, so recall improves.
- **Summary intent:** "summarise this" switches from similarity search to *coverage sampling* (evenly spaced chunks),
  because the most "similar" chunks to the word *summary* are not a summary.
- **Citations:** sources are numbered; the system prompt requires `[n]` after every factual sentence.
- **Deep vs Fast mode:** deep = planner + HyDE + LLM judge (slower, better); fast = single hybrid pass.

### 3.3 Claim verification (hallucination detection) — verifier v2
- Split the answer into sentences; check each against the passages it cites. **Code:** `app/ai/verifier.py`,
  called from `rag._verify`. In deep mode an **LLM-as-judge** gives a second faithfulness score.
- **Value checks (red, decide "not supported")** — concrete values must match the source:
  - **numbers:** ₹/Rs/INR/$ amounts, Indian digit grouping, lakh/crore/million scales, number words, percentages.
    "About" allows 5%. Sums and differences of two source figures, and intervals between source dates, count as
    derived.
  - **dates:** full date, day-month, month-year, FY ranges, years; D/M/Y with M/D/Y as an alternative reading.
  - **identifiers:** account numbers, DINs, invoice/PO/policy numbers must match exactly.
  - **periods:** the frequency word next to a number (per month vs per annum) must match the source's.
  - **party names:** every named organisation or person must appear in the source.
  - **relevance:** the sentence must be similar to some source sentence, or most of its content words must
    appear in the source.
- **Wording heuristics (amber, "check wording", don't count against the answer):**
  - **negation:** the parity of negation cues is compared with the best-matching source sentence, counting only
    cues whose scope touches the other text's words.
  - **direction words:** credit/debit, rose/fell, above/below, before/after.
  - **party roles:** by/from → source, to → recipient, plus the grammatical subject.
- **Optional NLI model** (LettuceDetect tiny, MIT; `ENABLE_NLI_VERIFIER=true`): one token-classification pass
  over the whole answer. Off by default because it didn't help on the held-out test set.
- **Measured (held-out test split, `benchmarks/reports/HALLUCINATION_BENCHMARK.md`):**
  - **v1 similarity check:** caught 20% of planted errors and wrongly flagged 14% of correct sentences.
  - **v2 red tier:** caught 68% and wrongly flagged 11%. Every wrong number, scale, date, period and party name
    was caught.
  - **Including amber:** caught 91%, but flagged 43% of correct sentences.
- **Still weak:** flipped negation, swapped payer/payee and rose/fell are only amber hints. Percentages computed
  from two figures are wrongly flagged. Passing means "no inconsistency found", not "verified true". The set is
  small, synthetic and written by the verifier's author.
- Each claim is returned with `supported`, `needs_review`, `issues` (kind, detail, severity), `score` (similarity
  to the best source sentence) and its `sources`.
- **Abstention:** if the model says the sources don't cover the question, or confidence is < 0.25, the answer is
  marked `abstained` — refusing to bluff is a feature.

### 3.4 Evidence score (uncalibrated)
- `0.4·retrieval_strength + 0.4·support_ratio + 0.2·citation_coverage`, capped at 0.35 when the model says "not
  found". `support_ratio` comes from the claim verifier (§3.3).
- It is a weighted heuristic, **not a probability**: it has never been fitted to labelled outcomes. Calibration
  (isotonic/Platt with an ECE report) is backlog Phase 5.
- Logged per query (`QueryLog.confidence`), shown as "Evidence score" and averaged on the Dashboard.
  **Code:** `rag._confidence`.

### 3.5 Knowledge graph / Ontology + GraphRAG-lite (`knowledge.py`)
- **Ontology** (Palantir's core idea): turn documents into typed *objects* (PERSON, ORG, MONEY, DATE, LAW…) and
  *links* between them, shared across the whole workspace.
- **Extraction:** precise regex for EMAIL/URL/MONEY/DATE/LAW; heuristic NER for ORG/PERSON/LOCATION; and, when an
  LLM is configured, GraphRAG-style JSON extraction of entities **and typed relations** (`signed_with`, `pays`…).
- **Entity resolution:** normalised names merge duplicates; most specific type wins.
- **GraphRAG-lite retrieval:** if a question names an entity, chunks that mention it (and its strongest neighbours)
  are added to the candidate pool — multi-hop questions get the right evidence.

### 3.6 Structured extraction (`extraction.py`)
- User defines a schema (`{"effective_date": "start date"}`) → retrieve passages per field → LLM fills a JSON
  object with `null` for missing values. Turns unstructured PDFs into rows for a spreadsheet/database.

### 3.7 Guardrails & Responsible AI (`guardrails.py`)
- **PII detection:** emails, phones, credit cards (validated with the **Luhn checksum**), SSN, IBAN, IPs, India
  PAN/Aadhaar → counts per document. `guardrails.redact()` exists, but nothing in the pipeline calls it yet: PII
  is **detected and reported, not redacted**, and stored text and answers still contain it.
- **Indirect prompt injection (OWASP LLM01):** a malicious PDF can contain "ignore previous instructions…".
  We flag it at upload, neutralise instruction-like spans in retrieved context, and the system prompt declares
  source text as untrusted data.
- **Tenant isolation:** every user has a private workspace; every query is filtered by tenant (tested).

### 3.8 Observability
- Every answer carries a **trace** (step, detail, ms), provider, model and latency; every query is logged.
  This is "glass-box AI": the user can audit *how* an answer was produced, not just *what* it says.

---

## Part 4 — Cheat-sheet: one line per concept

| Concept | One-liner |
|---|---|
| Variance of Laplacian | edge energy → blur detector |
| CLAHE | local histogram equalisation that doesn't blow up noise |
| Otsu | picks the threshold that best separates two intensity classes |
| Morphological opening | erode then dilate: keeps only shapes that fit the kernel (e.g. long lines) |
| CRAFT + CRNN + CTC | detect text regions, read sequences, align without per-character labels |
| Bi-encoder vs cross-encoder | separate vs joint encoding: speed vs precision |
| BM25 | TF-IDF with saturation and length normalisation |
| RRF | fuse rankings by 1/(k+rank) |
| MMR | relevance minus redundancy |
| HyDE | search with a hypothetical answer |
| GraphRAG | retrieve via entities and their relations, not just text similarity |
| LLM-as-judge | a second model grades faithfulness |
| Circuit breaker | stop calling a failing dependency for a while |
| Inverse cloze task | make a query from a passage to test retrieval without labels |
| c-TF-IDF | TF-IDF where each *cluster* is one document → topic labels |
| Luhn checksum | mod-10 check that rejects random 16-digit numbers as card numbers |
