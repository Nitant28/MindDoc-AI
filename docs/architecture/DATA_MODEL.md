# MindDoc — Canonical Evidence Model (proposal v0.1)

> Status: **proposed, not implemented.** This is the foundation every other layer depends on (Stage C deliverable).
> The current v2 schema (`app/database/models.py`) is mapped onto it in §9.

## 1. Design principles

1. **A claim is not a fact.** A document *asserts* something; MindDoc *extracts* it; algorithms may *infer* things;
   independent sources may *corroborate* it; a human may *verify* or *reject* it. These are different epistemic states
   and are stored as such — never collapsed into one "relationship" row.
2. **Everything is traceable to pixels.** Every extracted value points to a page region (normalised bounding box)
   in an immutable, content-addressed original.
3. **Bitemporal by construction.** *Valid time* = when something was true in the world (from the document).
   *System time* = when MindDoc recorded/believed it. "What did we know on 1 March?" is an as-of query on system time;
   "who owned X in 2024?" is a query on valid time.
4. **Append-only decisions.** Resolutions, reviews, merges and dispositions are events, never in-place edits, so every
   conclusion can be replayed and every mistake undone.
5. **Confidence is a vector, not a number.** Extraction, resolution, source reliability, corroboration and
   contradiction are stored separately; any combined score is a documented, versioned function (and calibrated
   before it is shown as a probability).
6. **Deterministic, idempotent identities.** Re-processing the same file with the same model version yields the same
   IDs, so reprocessing is safe and diffs between model versions are meaningful.

## 2. Epistemic status ladder

| Status | Meaning | Who sets it |
|---|---|---|
| `stated` | appears in a source (raw region text) | parser |
| `extracted` | structured by a model/rule from one region | extractor (+ version) |
| `inferred` | derived by computation/ML across sources (e.g. duplicate vendor) | algorithm (+ version, params) |
| `corroborated` | supported by ≥2 **independent** sources, no unresolved contradiction | corroboration engine |
| `contested` | at least one unresolved contradiction | contradiction engine |
| `verified` / `rejected` | human decision with reason | reviewer (RBAC-gated action) |

Independence is explicit: two sources are **not** independent if they are versions of the same document
(`supersedes` chain), near-duplicates (MinHash Jaccard ≥ τ), or derived from one another (e.g. a report quoting an
invoice). Corroboration counts independent source clusters, not documents.

## 3. Layer 1 — sources and pixels

```
Source(id ULID, tenant_id, sha256 UNIQUE per tenant, mime, filename, bytes, source_system, received_at,
       supersedes_source_id?, lifecycle_state, markings[])
Page(id = hash(source.sha256, number), source_id, number, width_pt, height_pt, rotation,
     has_text_layer, render_uri, quality{blur, contrast, brightness, skew}, ocr_engine?, ocr_confidence?)
Region(id = hash(page.id, kind, bbox_q), page_id, parent_region_id?, kind, bbox[x0,y0,x1,y1] ∈ [0,1],
       reading_order, text, method {pdf_text|ocr:<engine>|vlm:<model>}, method_version, confidence)
       kind ∈ heading|paragraph|list_item|table|table_cell|figure|chart|caption|header|footer|
              signature|stamp|handwriting|form_field
TableCell(region_id, table_region_id, row, col, row_span, col_span, header_path[], value_raw,
          value_norm {number, currency, date, unit}?)
```
- Bounding boxes are normalised so highlights survive any render DPI. `bbox_q` = bbox quantised to 1/1000.
- `lifecycle_state`: `received → validated → parsed → extracted → indexed → linked → analysed` or `failed(stage, error)`.

## 4. Layer 2 — retrieval units

```
Chunk(id, source_id, region_ids[], text, context_prefix, page_span, token_count, chunker_version)
Embedding(chunk_id, model, dim, vector)          -- many models may coexist; queries pin one
LexicalIndex(chunk_id, tsvector)                 -- or BM25 sidecar
```
`context_prefix` implements contextual retrieval (document title + section path + 1-sentence situating summary)
and is embedded together with the chunk text.

## 5. Layer 3 — mentions, entities, identity resolution

```
Mention(id, region_id, char_start, char_end, surface, type, extractor, extractor_version, confidence)
Entity(id ULID, tenant_id, type, canonical_name, status {active|merged_into:<id>|split}, created_at)
EntityIdentifier(entity_id, scheme {GSTIN|PAN|CIN|IBAN|email|phone|URL|…}, value_norm, evidence_region_id)
ResolutionDecision(id, mention_id, entity_id, score, features{name_sim, id_match, address_sim, graph_overlap,
                   temporal_compat}, method {rule|model:<ver>|human}, decided_by, decided_at, superseded_by?)
EntityMerge / EntitySplit events (append-only, reversible)
```
Resolution policy (versioned): `score ≥ τ_auto` → auto-link; `τ_review ≤ score < τ_auto` → review queue;
below → separate. Hard constraints: conflicting strong identifiers (two different valid GSTINs) never auto-merge.

## 6. Layer 4 — claims, evidence, relationships, events

```
Claim(id, tenant_id, subject_entity_id, predicate, object_entity_id? | object_value{type, value, unit, currency},
      qualifiers{valid_from?, valid_to?, as_of?, location?}, modality {asserted|negated|hypothetical|planned|reported},
      status (§2), extracted_by, extractor_version, recorded_at, retracted_at?)
Evidence(id, claim_id, region_id, role {supports|contradicts|context}, quote_start, quote_end, source_sha256)
Relationship(id, tenant_id, subject_id, predicate, object_id, valid_from?, valid_to?,
             claim_ids[], status, scores{extraction, resolution, reliability, corroboration, contradiction},
             combined_score, score_fn_version, recorded_at, superseded_at?)   -- materialised from claims
Event(id, tenant_id, type, time{point|interval, precision day|month|year, uncertainty}, participants[{entity_id, role}],
      amount?, claim_ids[])
```
- **Predicates come from the ontology** (`KNOWLEDGE_GRAPH_SCHEMA` section below) with per-predicate domain/range
  constraints and cardinality (e.g. `DIRECTOR_OF` Person→Organization, many-to-many, time-bounded).
- Co-occurrence is **not** a relationship. It is stored as `CoMention(entity_a, entity_b, count, source_ids)` and shown
  as a weak, separately styled signal (the current v2 `co_occurs` edges move here).

### Ontology packs (selected market: `docs/strategy/MARKET_SELECTION.md`)

**Pack 1 — Lender forensic review (primary):** loan end-use and related-party fund trail.

| Object types | Person (DIN, PAN), Organization (CIN, PAN, GSTIN), Address, BankAccount (number + IFSC), BankTransaction, LoanFacility, Disbursement, Invoice, GSTReturn (GSTR-1/3B/2B period summary), LedgerEntry, StockStatement, RelatedPartyDisclosure, Document |
|---|---|
| Predicates | DIRECTOR_OF, SHAREHOLDER_OF, PROMOTER_OF, HAS_ACCOUNT, TRANSFERRED_TO (BankTransaction), DISBURSED_FROM, SANCTIONED_TO, ISSUED_INVOICE, BILLED_TO, REPORTED_TURNOVER, DECLARED_STOCK, DISCLOSED_RELATED_PARTY, LOCATED_AT, SHARES_ADDRESS_WITH, SUPERSEDES, MENTIONED_IN |
| Literal properties | amount (INR, paise precision), value date, narration, counterparty text, running balance, period, invoice no., GSTIN, HSN, end-use condition, limit |

Integrity rules that are *data-model* features, not detectors: bank-statement pages must reconcile
(`opening + credits − debits = closing` per page) or the page's claims are marked `extraction_suspect`;
identifiers are validated (GSTIN/PAN checksums and format, IFSC format) before they can drive entity merges.

**Pack 2 — Procure-to-pay integrity (fallback):** Vendor, Employee, PurchaseOrder, GoodsReceipt, Invoice, Payment,
Contract; predicates ISSUED_PO, RECEIVED_GOODS, INVOICED, PAID, CONTRACTED_WITH. Same engine, different detectors.

## 7. Layer 5 — analysis, investigation, governance

```
Contradiction(id, claim_a, claim_b, kind {value_mismatch|date_conflict|identity_conflict|temporal_order|cross_modal},
              detector, detector_version, score, explanation_template, status {open|explained|confirmed|dismissed})
Discovery(id, tenant_id, trigger {event|schedule|query}, hypothesis_template, algorithm, algorithm_version, params,
          score, calibrated_probability?, evidence_ids[], counter_evidence_ids[], disposition {pending|confirmed|dismissed},
          disposed_by?, reproducibility{dataset_snapshot, seed})
Investigation(id, tenant_id, title, question, scope{source_ids|entity_ids|time_range}, state, created_by)
AgentStep(id, investigation_id, agent, tool, input_hash, output_ref, status, started_at, ms, tokens, cost)
Finding(id, investigation_id, statement, supporting_claim_ids[], counter_claim_ids[], unknowns[], method,
        status {draft|proposed|approved|rejected}, approved_by?)
Review(id, target_type, target_id, decision, reason, reviewer_id, at)                      -- append-only
Action(id, type, target, params, requested_by {user|agent}, policy_check, approval_id?, executed_at?)
AuditEvent(id, tenant_id, actor, verb, object, payload_hash, prev_hash, at)                  -- hash-chained
```

## 8. Lineage query (the auditor's path)

```
Report.Finding → Finding.supporting_claim_ids → Claim → Evidence → Region.bbox → Page → Source.sha256
             ↘ AgentStep(tool, input_hash, model, prompt_version) ↘ Review / Approval
```
Acceptance test: from any sentence in a generated report, the UI reaches the highlighted source region in ≤ 2 clicks,
and the API returns the full chain as JSON.

## 9. Mapping from the current v2 schema

| v2 table | Becomes | Notes |
|---|---|---|
| `documents` | `Source` (+ `Page`) | `content_hash` → `sha256`; page reports in `vision_json` → `Page.quality` |
| `document_chunks` | `Chunk` + `Embedding` | v2 chunks have page but no region ids; re-parse originals to attach regions |
| `entities`, `entity_mentions` | `Entity`, `Mention`, `ResolutionDecision` | v2 resolution is exact-normalised-name only |
| `relations` (`co_occurs`) | `CoMention` | LLM-typed relations → `Claim(status=extracted)` with evidence |
| `query_logs`, `chat_messages.meta_json` | `AuditEvent` + `AgentStep` | prompt hash + chunk ids already captured |
| — | `Claim`, `Evidence`, `Relationship`, `Event`, `Contradiction`, `Discovery`, `Investigation`, `Review` | new |

Migration is additive; v2 endpoints keep working against compatibility views until the frontend moves over.
