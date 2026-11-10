# F — Review of the claim-centric bitemporal evidence schema

**Reviewed:** `docs/architecture/DATA_MODEL.md` (v0.1, proposed) and ADR-0004, against the current code
(`app/database/models.py`) and the bank-statement design (E).

**Verdict:** the principles are right — claims are not facts, everything traces to pixels, append-only decisions,
and confidence is a vector. But v0.1 is not implementable as written. It lacks the financial observation layer, case
scope, a money type, concrete bitemporal mechanics, and a way to freeze what a finding relied on. The changes below
close those gaps without changing the ADR's decision.

## 1. Gaps in v0.1

| # | Gap | Why it matters | Fix (§ below) |
|---|---|---|---|
| F1 | No typed tables for statements, accounts, transactions or reconciliation checks. A `BankTransaction` exists only as an ontology object type | A statement has hundreds to thousands of rows. Arithmetic, sorting and matching need typed numeric columns, not generic claims | §2.3 |
| F2 | No money representation beyond "INR, paise precision" | `float` breaks reconciliation (`0.1 + 0.2 ≠ 0.3`); the current verifier uses float (audit A14) | §2.2 |
| F3 | No case or engagement scope | Forensic work is per borrower engagement, with its own team, period and sources. Tenant-wide graphs mix unrelated borrowers | §2.1 |
| F4 | Bitemporality is named, not specified: claims have `recorded_at` and `retracted_at`, but there's no versioning rule, no as-of query pattern and no constraint | Without one rule, "what did we know on 1 March?" can't be answered reliably | §3 |
| F5 | Findings point to *current* claims | When a claim is corrected, an old finding silently changes meaning. It must stay explainable as it was | §4 |
| F6 | Merges are "events", but there's no defined way to compute the current identity map or to reverse a merge | Reversibility is a requirement (ADR-0009) | §5 |
| F7 | `tenant_id` sits only on top-level tables | Row-level security needs the tenant on every row, or slow join-based policies | §2.1 |
| F8 | Source independence is described but not stored | Corroboration and leave-one-source-out fragility (I) need source clusters | §6 |
| F9 | No place for fragility results, reconciliation outcomes or review queues | Deliverables E and I need them | §2.3, §6 |
| F10 | No data-governance fields (PII class, retention, legal hold) | Lending data falls under the DPDP Act; see D | §7 |

## 2. Structural changes

### 2.1 Scope and tenancy
```
tenant(id, name)
case(id, tenant_id, title, borrower_entity_id?, period_from, period_to, status, created_by, created_at)
case_member(case_id, user_id, role {lead|analyst|reviewer|viewer})
case_source(case_id, source_id, added_by, added_at, removed_at?)   -- a source can belong to several cases
```
- Every table carries `tenant_id NOT NULL`, set from the parent at insert time and enforced by RLS.
- Case-level authorisation is enforced in the application layer: role checks per case.
- Graph analytics, discovery and findings are **case-scoped**. The tenant-wide view stays for search only.

### 2.2 Money and numbers
- Amounts: `amount_paise BIGINT` + `currency CHAR(3) DEFAULT 'INR'`. Never `float`, anywhere in the financial path,
  Python included: use `int` paise or `decimal.Decimal` with explicit quantisation.
- Rates and ratios: `NUMERIC(12,6)`.
- Every parsed amount keeps its raw text (`amount_raw`) beside the normalised value, so the original is never lost.

### 2.3 Financial observation layer (new)
Observations are what a parser **extracted** from a region. Claims are assertions about the world built from them.
```
bank_account(id, tenant_id, entity_id?, bank_name, ifsc?, account_no_masked, account_no_hash, account_type?,
             currency, first_seen_source_id)
statement(id, tenant_id, source_id, bank_account_id?, period_from, period_to,
          opening_balance_paise?, closing_balance_paise?, opening_side, closing_side {CR|DR},
          layout_signature, extractor, extractor_version, extracted_at, status {parsed|reconciled|needs_review|failed})
statement_txn(id = hash(source_sha256, page, row_bbox_q, extractor_version), tenant_id, statement_id, seq_no,
              page_no, row_region_id, txn_date, value_date?, narration_raw, cheque_or_ref_raw?,
              debit_paise?, credit_paise?, balance_paise?, balance_side?,
              direction_source {column|suffix|inferred_from_balance}, mode? {UPI|NEFT|RTGS|IMPS|NACH|CHQ|CASH|CARD|INT|CHG|OTHER},
              utr?, counterparty_text?, field_confidence jsonb, status {ok|suspect|corrected},
              supersedes_id?, sys_period tstzrange)
statement_cell(txn_id, column_role {date|value_date|narration|ref|debit|credit|amount|balance}, region_id, bbox, text_raw)
reconciliation_check(id, tenant_id, statement_id, scope {row|page|statement|cross_statement}, txn_id?, page_no?,
                     expected_paise, observed_paise, diff_paise, status {pass|fail|not_checkable},
                     reason_code, explanation, checker_version, checked_at)
```
- **Transactions are observations, not claims.** A claim such as `TRANSFERRED_TO(borrower_account → party,
  ₹X, date)` is created from one or more `statement_txn` rows, with `Evidence` pointing at their regions.
- `reconciliation_check` rows are append-only results. A failed check never edits the transaction (deliverable E).
  A human correction inserts a new `statement_txn` version, with `supersedes_id` and a review event, and re-runs the
  checks.
- `account_no_hash` (keyed hash) supports matching; only the masked form is displayed (§7).

## 3. Bitemporal mechanics (one rule for every mutable assertion)

Applies to: `claim`, `relationship`, `entity_attribute`, `statement_txn` corrections, `resolution_decision`.

1. **Two kinds of identity.** A row has a stable *logical key* (`claim_key`) and a *version id* (`id`). Evidence,
   reviews and findings always reference **version ids**.
2. **Valid time** (`valid_period tstzrange` or `daterange`, plus `valid_precision {day|month|year|unknown}`) is what
   the document asserts about the world. It's nullable; open bounds mean "unknown".
3. **System time** (`sys_period tstzrange`, `[recorded_at, superseded_at)`) is when MindDoc believed this version.
   Rows are never updated except to close `sys_period`. A correction inserts a new version, and the two happen in one
   transaction.
4. **Integrity:** at most one current version per logical key at any system time. Use PostgreSQL 18's temporal
   `WITHOUT OVERLAPS` key on `(claim_key, sys_period)` if the infra research (G) confirms it fits. Otherwise use an
   exclusion constraint (`btree_gist`): `EXCLUDE USING gist (claim_key WITH =, sys_period WITH &&)`.
5. **Queries:**
   - *current*: `upper_inf(sys_period)`, exposed as views (`claim_current`).
   - *as known at T*: `sys_period @> T`.
   - *true at V*: `valid_period @> V`.
   - *both*: combine the two.
6. **Re-processing is deterministic:** the same source plus the same extractor version gives the same observation IDs
   (no new versions). A new extractor version creates new versions, closes the old ones and records a diff.

## 4. Findings stay explainable over time

```
finding(id, tenant_id, case_id, finding_key, statement, method, status {draft|proposed|approved|rejected|superseded},
        evidence_snapshot_at timestamptz, supersedes_id?, created_by {user|agent}, created_at)
finding_support(finding_id, claim_version_id, role {supports|contradicts|context}, weight?)
finding_robustness(finding_id, run_id, method {loso_cluster}, n_clusters, essential_cluster_ids[], k_fragility?,
                   persisted_fraction, details jsonb, pipeline_version, computed_at)       -- deliverable I
report(id, case_id, finding_ids[], frozen_at, content_hash, signed_by?)                   -- immutable once issued
```
- A finding stores **claim version IDs** and `evidence_snapshot_at`. Re-running it after new evidence creates a new
  finding version (`supersedes_id`). The old version still resolves to exactly the claims and regions it relied on.
- An issued report is frozen: `content_hash`, plus a pinned list of finding versions. That's the "material relied
  upon" a borrower may be entitled to see (see D).

## 5. Identity: reversible merges and splits

```
entity(id, tenant_id, type, created_at)                  -- never deleted, never renamed in place
entity_identifier(entity_id, scheme {GSTIN|PAN|CIN|DIN|IFSC_ACCOUNT|UPI_VPA|email|phone}, value_norm,
                  valid_checksum bool, evidence_region_id, sys_period)
identity_event(id, tenant_id, kind {merge|unmerge|split}, survivor_id?, merged_ids[], reason, features jsonb,
               method {rule|splink:<ver>|human}, decided_by, decided_at, reverses_event_id?)
entity_canonical(entity_id, canonical_id, sys_period)    -- derived from identity_event, rebuildable
```
- **Undo** is a new `unmerge` event that references the merge. `entity_canonical` is recomputed for the affected
  component, and old system-time queries still show the merged state as it was then.
- **Hard rule:** conflicting valid strong identifiers (two different valid PANs) block auto-merge. A human override
  must give a reason.
- Mentions resolve through versioned `resolution_decision` rows (v0.1 §5, unchanged).

## 6. Independence and review

```
source_cluster(id, tenant_id, case_id, kind {same_document_versions|near_duplicate|derived_from|same_issuer_system},
               member_source_ids[], method, method_version, sys_period)
review_event(id, tenant_id, target_type, target_version_id, decision {verify|reject|correct|dismiss|escalate},
             reason, reviewer_id, at, supersedes_event_id?)            -- append-only
review_queue(id, tenant_id, case_id, item_type, item_id, priority, reason_code, state, assigned_to?) -- operational
```
- Corroboration counts **independent source clusters**, not files.
- `review_queue` is the only mutable operational table. Its history lives in `review_event`.

## 7. Governance fields (DPDP-aware; legal analysis in D)
- `source.sensitivity {public|internal|confidential|personal}`, `source.retention_until`, `source.legal_hold bool`.
- PII-bearing columns (`narration_raw`, `counterparty_text`, account numbers) are tagged in a column registry, so
  export, redaction and erasure jobs can find them.
- Account numbers are stored masked, plus a keyed hash. The raw value lives only in the region text of the original
  document.

## 8. Worked scenarios (these become acceptance tests)

1. **OCR digit error.** Row 57 is read as ₹1,48,000. The running balance fails by ₹1,30,000 (`reconciliation_check`
   fail on row 57).
   - The finding "₹1.48 lakh paid to X" is drafted, then held for review.
   - The reviewer corrects the row to ₹18,000: a new `statement_txn` version plus a `review_event`, and the checks
     pass.
   - A new finding version is created. The old one still shows ₹1,48,000, the failed check and why it was
     superseded.
   - **Test:** as-of queries before the correction return the old values.
2. **Wrong merge undone.**
   - "Sunrise Traders" and "Sunrise Trading Co." are auto-merged by Splink, and a related-party finding uses the
     merged entity.
   - A reviewer unmerges them. The finding is re-evaluated and superseded.
   - **Test:** the graph at the earlier system time still shows the merge; the current graph doesn't.
3. **New statement arrives.** An extra month of statements adds contradicting evidence.
   - `finding_support` for the new finding version includes a `contradicts` row.
   - The issued report keeps pointing to the old version, and the case shows "new evidence since report".

## 9. Mapping from current tables (additions to DATA_MODEL §9)

| Current (v2.1) | New |
|---|---|
| `documents` | `source` + `page` + `case_source` |
| `document_chunks` (JSON vectors) | `chunk` + `embedding` (pgvector) |
| `entities` / `entity_mentions` / `relations` | `entity`, `mention`, `resolution_decision`. `co_occurs` rows → `co_mention` (audit A19); typed relations → `claim` with evidence |
| — | `statement`, `statement_txn`, `statement_cell`, `bank_account`, `reconciliation_check` |
| `query_logs`, `chat_messages.meta_json` | `audit_event` + `agent_step` (prompt hash and chunk IDs carry over) |

## 10. Costs and risks

- **More tables and joins:** mitigate with `*_current` views for the application and tests that pin the as-of
  semantics.
- **Write amplification:** corrections are rare compared with inserts, so the cost is acceptable.
- **ORM ergonomics:** SQLAlchemy maps views read-only; inserts and closing versions go through one repository
  function per aggregate, so the "never update" rule lives in one place.
- **Over-modelling before the first parser works:** build in this order — `source/page/region` → statement tables →
  claim/evidence for transfers → identity → findings. Each step is shipped behind tests (see J).

## 11. Acceptance criteria for the schema

- Property test: for random sequences of inserts, corrections and merge/unmerge, every as-of query at time T returns
  the same answer before and after later events.
- Lineage: from any finding version, the API returns finding → claim versions → evidence → region bbox → page →
  source sha256 in one call, and the UI reaches the highlighted region in ≤ 2 clicks.
- RLS: a user from tenant A gets zero rows from any tenant-B table, even with crafted IDs (tested per table).
- No `float` columns or Python floats in the financial path (enforced by a lint rule and a grep in CI).
