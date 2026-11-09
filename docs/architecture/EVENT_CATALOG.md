# MindDoc — Event Catalog & Streaming Design (proposal v0.1)

> Status: **proposed.** Event contracts are defined now; the transport is introduced in two steps (see §1).

## 1. Why events, and when Kafka is actually justified

Today ingestion runs **inside the upload request** (`app/api/documents.py` → `services/ingestion.py`): a 200-page
scanned PDF blocks an HTTP worker for minutes, a crash loses work, and nothing downstream can react to new data.
Those are real problems, and an event log fixes them. But Kafka is not needed to fix them; a durable job table is.

| Requirement | Durable job table (Postgres `SKIP LOCKED` + transactional outbox) | Kafka |
|---|---|---|
| Upload returns immediately; retries; dead-letter | ✅ | ✅ |
| Several independent consumers of the same fact (indexer, graph builder, discovery, audit) | awkward (fan-out tables) | ✅ consumer groups |
| **Replay history** with a new model version (re-extract all invoices with extractor v3; rebuild graph "as of") | manual | ✅ offset reset / retained log |
| Ordered per-document/per-tenant processing at scale | ok | ✅ partition key |
| Ops burden for a solo developer | low | medium (KRaft single node in Docker is fine) |

**Decision (ADR-0003):** define every event contract now; ship **Step A** (outbox + Postgres-backed workers) with the
canonical data model; introduce **Step B** (Kafka, KRaft, single broker in Docker Compose) when the second independent
consumer group (continuous discovery) lands — the point where fan-out + replay become genuine requirements.
The outbox table becomes the Kafka producer's source (Debezium-style relay or a small poller), so no producer code changes.

## 2. Envelope (all events)

```json
{
  "event_id": "01JC…(ULID)", "type": "document.parsed", "version": 1,
  "tenant_id": "t_…", "subject_id": "src_…", "occurred_at": "2026-11-10T09:12:03Z",
  "producer": "parser@1.4.0", "trace_id": "otel trace id", "causation_id": "event_id that caused this",
  "idempotency_key": "sha256(type|subject_id|producer_version|input_hash)",
  "payload": { }
}
```
- Serialisation: JSON Schema in `schemas/events/*.json` now; Avro/Protobuf + schema registry only with Kafka.
- Versioning: additive changes keep `version`; breaking changes bump it and consumers handle both for one release.

## 3. Topics / event types

| Event | Key (partition) | Producer | Consumers | Payload (essentials) |
|---|---|---|---|---|
| `source.received` | tenant_id | API | validator | source_id, sha256, mime, bytes, uri |
| `source.validated` / `source.rejected` | tenant_id | validator | parser / audit | checks (type sniff, size, pages, encryption, macro/JS) |
| `document.parsed` | source_id | parser | extractor, indexer | page_ids, region counts, text-layer vs OCR pages |
| `page.ocr.completed` | source_id | OCR worker | parser | page_id, engine@ver, mean_conf |
| `document.extracted` | source_id | extractor | resolver, contradiction, indexer | claim_ids, mention_ids, table_ids |
| `document.indexed` | source_id | indexer | — | chunk_ids, embedding model@ver |
| `entity.resolved` | tenant_id | resolver | graph, discovery | mention→entity decisions, merges (with scores) |
| `graph.updated` | tenant_id | graph builder | discovery, UI notifier | changed relationship ids, diff summary |
| `contradiction.detected` | tenant_id | contradiction engine | discovery, UI notifier | claim pair, kind, score |
| `discovery.raised` | tenant_id | discovery engine | UI notifier, audit | discovery_id, algorithm@ver, score |
| `review.recorded` | tenant_id | API (human) | graph, ML feedback store, audit | target, decision, reviewer |
| `investigation.step.completed` | investigation_id | orchestrator | UI (SSE), audit | step, tool, status, ms, tokens |
| `action.requested` / `action.approved` / `action.executed` | tenant_id | agents / humans | policy engine, audit | action type, params, policy result |
| `*.failed` | same as source event | any | retry scheduler, DLQ | stage, error class, attempt |

## 4. Delivery semantics (honest version)

- Kafka's exactly-once covers Kafka→Kafka pipelines, **not** our Postgres, vector index and object store. Therefore
  every consumer is **idempotent**: writes are upserts keyed by deterministic IDs (see DATA_MODEL §1.6) and each consumer
  records `processed(event_id)` in the same DB transaction as its writes.
- Retries: exponential backoff (1s, 5s, 30s, 2m, 10m) → `*.dlq` with the full envelope; a UI page lists DLQ items with
  "retry" and "discard" actions (audited).
- Backpressure: bounded worker concurrency per stage (OCR is CPU-heavy, LLM extraction is rate-limited and costly);
  per-tenant fair scheduling so one 10,000-file upload cannot starve other tenants.
- Ordering: only guaranteed per partition key; consumers must tolerate `entity.resolved` arriving before
  `document.indexed` for the same source.

## 5. Observability

Every event carries `trace_id`; workers emit OpenTelemetry spans. Metrics: per-stage throughput, p50/p95 latency,
queue depth / consumer lag, retry and DLQ rates, cost per document (LLM tokens + compute seconds).
The **Ingestion Center** UI reads `source.lifecycle_state` plus the per-stage events to show each document's live status.

## 6. Replay scenarios this design must support (acceptance tests)

1. Re-run extraction for all `Invoice` sources with extractor v2 → new claims with `extractor_version=2`; old claims are
   retracted (system time), not deleted; graph diff is emitted.
2. Rebuild the graph "as of" a past system time from the event log and compare with the live graph.
3. Kill a worker mid-document → on restart the document completes with no duplicate rows.
