# MindDoc AI — API Contract (v2)

Base URL: `http://127.0.0.1:8000/api` (override with `VITE_API_URL`). All endpoints except register/login
require `Authorization: Bearer <token>`. All responses are JSON unless noted.

Backward compatible with v1: every v1 endpoint and field still exists.

---

## Auth

| Method | Path | Body | Response |
|---|---|---|---|
| POST | `/auth/register` | `{email, password}` | `{access_token, token_type}` |
| POST | `/auth/login` | `{email, password}` | `{access_token, token_type}` |
| PUT | `/auth/update_email` | `{new_email, password}` | `{message}` |
| GET | `/auth/me` | – | `{id, email, workspace}` |

Each new user gets a private workspace (tenant). Documents are isolated per workspace.

---

## Documents

### `POST /documents/upload` (multipart, field `file`)
Accepts `.pdf .docx .txt .md .png .jpg .jpeg .tiff .bmp .gif .webp`.
```json
{
  "message": "Document uploaded successfully",
  "document_id": 12,
  "filename": "contract.pdf",
  "characters_extracted": 18234,
  "preview": "first 200 chars…",
  "analysis": DocumentDetail
}
```

### `GET /documents/list`
```json
[{ "id": 12, "filename": "contract.pdf", "created_at": "2026-11-09T10:00:00",
   "doc_type": "legal_contract", "summary": "…", "pages": 9, "chunk_count": 31,
   "quality_score": 0.92, "pii_count": 3 }]
```

### `GET /documents/{id}` → `DocumentDetail`
```json
{
  "id": 12, "filename": "contract.pdf", "created_at": "…",
  "doc_type": "legal_contract", "doc_type_confidence": 0.71,
  "summary": "3–5 sentence summary",
  "keywords": [{ "term": "indemnification", "score": 0.42 }],
  "entities": [{ "name": "Acme Corp", "type": "ORG", "count": 7 }],
  "pii": { "count": 3, "types": { "EMAIL": 2, "PHONE": 1 } },
  "security_flags": [{ "type": "prompt_injection", "severity": "high", "snippet": "ignore previous instructions…" }],
  "vision": {
    "overall_quality": 0.92,
    "ocr_pages": 2,
    "pages": [{ "page": 1, "method": "text|ocr", "ocr_confidence": 0.88, "blur_score": 412.5,
                "quality": "good|fair|poor", "skew_angle": 0.4, "tables_detected": 1, "figures_detected": 0 }]
  },
  "stats": { "characters": 18234, "words": 3011, "chunks": 31, "pages": 9,
             "reading_time_min": 12, "readability": 41.2 },
  "preview": "first 1000 chars"
}
```
Any field may be `null`/empty for documents uploaded before v2.

### `POST /documents/{id}/extract`
Structured extraction (GenAI → JSON). Body:
```json
{ "fields": { "parties": "Names of contracting parties", "effective_date": "Start date", "total_value": "Contract value" } }
```
Response:
```json
{ "data": { "parties": ["Acme Corp", "Globex"], "effective_date": "2026-01-01", "total_value": "$1.2M" },
  "provider": "anthropic", "model": "claude-sonnet-5-5" }
```

### Unchanged
`DELETE /documents/delete/{id}`, `PUT /documents/edit/{id}?filename=…`, `POST /documents/save/{id}`.

---

## Chat

### `POST /chat/query`
Body:
```json
{ "query": "What is the termination clause?", "session_id": null,
  "document_id": 12, "document_ids": [12, 14], "mode": "fast|deep" }
```
- No `document_id(s)` → searches the whole workspace (falls back to general knowledge if workspace is empty).
- `mode: "deep"` → query decomposition + multi-query retrieval + LLM verification (slower, better).

Response (`RagAnswer`):
```json
{
  "answer": "Markdown answer with inline citations like [1] and [2].",
  "session_id": 5,
  "citations": [{ "index": 1, "document_id": 12, "filename": "contract.pdf", "page": 4,
                  "chunk_id": 88, "snippet": "Either party may terminate…", "score": 0.83 }],
  "confidence": 0.81,
  "grounded": true,
  "groundedness": { "supported": 5, "total": 6, "unsupported": ["sentence not backed by sources"] },
  "sub_queries": ["termination clause", "notice period for termination"],
  "trace": [{ "step": "retrieve", "detail": "hybrid BM25+dense → 24 candidates", "ms": 41 }],
  "provider": "anthropic", "model": "claude-sonnet-5-5", "latency_ms": 2310
}
```

### `POST /chat/stream` — Server-Sent Events
Same body as `/chat/query`. Response `text/event-stream`, each event is `data: <json>\n\n`:
- `{"type":"trace","step":"retrieve","detail":"…","ms":41}`
- `{"type":"token","text":"partial text"}`
- `{"type":"final", ...RagAnswer}` (always last on success)
- `{"type":"error","detail":"…"}`

Use `fetch` + `ReadableStream` (not `EventSource`, because it is a POST with a bearer token).

### `GET /chat/messages/{session_id}`
```json
[{ "role": "user", "content": "…" },
 { "role": "assistant", "content": "…", "meta": { "citations": [...], "confidence": 0.8, "grounded": true, "trace": [...] } }]
```
`meta` may be absent on old messages.

### Unchanged
`GET /chat/sessions`, `DELETE /chat/sessions/{id}`, `PUT /chat/sessions/{id}?title=…`,
`POST /chat/save_response`, `GET /chat/saved_items`, `DELETE|PUT /chat/saved_items/{id}`.

---

## Intelligence (ontology, analytics, evaluation)

### `GET /intel/graph?document_id=12&limit=150`
Knowledge graph (ontology) of entities across the workspace.
```json
{ "nodes": [{ "id": "e:17", "label": "Acme Corp", "type": "ORG", "weight": 7, "documents": [12, 14] }],
  "edges": [{ "source": "e:17", "target": "e:21", "relation": "co_occurs|signed_with|…", "weight": 3 }] }
```
Node `type` ∈ `PERSON ORG LOCATION DATE MONEY EMAIL URL PRODUCT LAW CONCEPT OTHER`.

### `GET /intel/overview`
```json
{ "documents": 8, "chunks": 210, "entities": 143, "relations": 302, "queries": 57,
  "avg_latency_ms": 1820, "avg_confidence": 0.77, "pii_total": 11,
  "doc_types": { "legal_contract": 3, "research_paper": 2 },
  "topics": [{ "id": 0, "label": "payments · invoice · tax", "keywords": ["payments","invoice","tax"], "document_ids": [3, 5] }],
  "recent_queries": [{ "query": "…", "confidence": 0.8, "latency_ms": 1500, "provider": "anthropic", "created_at": "…" }] }
```

### `POST /intel/eval` (body optional `{ "sample_size": 20 }`)
Self-supervised retrieval evaluation (synthetic queries from chunks).
```json
{ "n": 20, "hit_rate_at_5": 0.9, "mrr": 0.74, "dense_only_hit_rate": 0.8, "bm25_only_hit_rate": 0.7, "ms": 900 }
```

### `GET /intel/capabilities` (no auth required)
```json
{ "llm_providers": [{ "name": "anthropic", "available": true, "model": "claude-sonnet-5-5" }],
  "embeddings": "sentence-transformers/all-MiniLM-L6-v2 | hashing-384 (offline fallback)",
  "reranker": false, "opencv": true, "ocr_engines": ["tesseract", "easyocr"], "vision_llm": true }
```

---

## Vision Lab

### `POST /vision/analyze` (multipart, field `file`: an image)
Computer-vision inspection of a single image (what the AI "sees").
```json
{
  "width": 1654, "height": 2339,
  "quality": { "blur_score": 380.2, "brightness": 0.81, "contrast": 0.32, "quality": "good", "score": 0.9 },
  "skew_angle": -1.2,
  "blocks": [{ "x": 120, "y": 88, "w": 900, "h": 40, "type": "text|table|figure" }],
  "ocr": { "engine": "tesseract", "text": "…", "confidence": 0.86, "words": 312 },
  "caption": "Optional vision-LLM description of the image (null if no vision LLM)",
  "annotated_image": "data:image/png;base64,…  (input with detected blocks drawn)"
}
```

---

## v2.1 additions (provenance & decision support)

### Pixel-level citations — `GET /documents/{id}/page/{page}/image?chunk_id=88`
Returns `image/png`: the rendered PDF page with the cited passage highlighted (amber boxes).
Auth is a bearer header, so fetch with axios `responseType: 'blob'` and show via `URL.createObjectURL`.
404 when the original isn't available (non-PDF, or uploaded before v2.1) — hide the "View on page" button then.
Response header `X-Highlight-Boxes: <n>` = number of highlighted regions (0 = page shown without highlight).

### Claim-level verification (added to `RagAnswer.groundedness`)
```json
"groundedness": { "supported": 5, "total": 6, "unsupported": ["…"],
  "claims": [{ "text": "Either party may terminate with 60 days notice.", "supported": true, "score": 0.82, "sources": [1] }] }
```
Plus top-level `"abstained": true|false` (answer says the sources don't contain it, or evidence too weak) and
`"prompt_hash": "sha256…"` (provenance).

### Timeline — `GET /intel/timeline?document_id=&upcoming_days=`
Dates/deadlines found across documents, sorted ascending.
```json
[{ "date": "2026-03-12", "text": "12 March 2026", "document_id": 12, "filename": "msa.pdf", "page": 2,
   "snippet": "…renewal on 12 March 2026 unless…", "upcoming": true, "days_from_now": 123 }]
```

### Audit trail — `GET /intel/audit?limit=50`
```json
[{ "id": 9, "created_at": "…", "query": "…", "mode": "deep", "provider": "anthropic", "model": "claude-sonnet-5-5",
   "latency_ms": 2100, "confidence": 0.81, "grounded": true, "n_citations": 3,
   "prompt_hash": "ab12…", "chunk_ids": [88, 91] }]
```

---

## Errors
Standard FastAPI: `{ "detail": "message" }` with 4xx/5xx status. 401 → frontend clears token and redirects to `/login`.
