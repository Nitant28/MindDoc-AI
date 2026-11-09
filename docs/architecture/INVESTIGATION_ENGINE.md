# MindDoc — Investigation & Discovery Engine (proposal v0.1)

> The flagship capability. Runtime/framework choice is an ADR decided after `docs/research/TECHNOLOGY_EVALUATION.md`;
> this document fixes the *logical* design, which must hold regardless of framework.

## 1. Design stance: few LLM agents, many deterministic tools

Most "agents" in typical multi-agent diagrams are an LLM re-describing work a deterministic function does better.
MindDoc separates three kinds of components:

| Kind | Examples | Properties |
|---|---|---|
| **Deterministic analytics tools** | graph queries, path finding, 3-way match, Benford test, duplicate detection, aggregations, date-order checks | exact, unit-testable, explainable, cheap |
| **ML models** | entity matcher, anomaly scorer, document classifier, layout/table models | versioned, evaluated, calibrated, SHAP-explainable |
| **LLM roles** (only 4) | *Planner* (question → typed plan), *Extractor* (text/table → claims), *Verifier* (adversarial checker), *Writer* (findings → report prose) | schema-constrained I/O, prompt-versioned, evaluated on trajectories |

An LLM never produces a statistic, a score or a graph edge directly; it calls the tool that does and cites the result.

## 2. Investigation lifecycle (durable state machine)

```
created → planned → running ⇄ awaiting_input → verifying → awaiting_review → reported → closed
                         ↘ failed (resumable from last completed step)
```
- **Plan** = a typed DAG of steps `{tool, args, depends_on, purpose}` produced by the Planner from a tool catalogue;
  validated against permissions *before* execution and shown to the user (editable).
- Each step is persisted (`AgentStep`: input hash, output ref, status, ms, tokens, cost) → crash-safe resume,
  reproducible replay, cost accounting, and the "Agent Control Room" view.
- **Checkpoints**: plans touching > N sources or costing > budget, and every `write-proposal` action, pause for approval.

## 3. The verification layer (what makes findings defensible)

Every candidate `Finding` must pass, in order:
1. **Evidence completeness** — each factual sentence maps to ≥1 `Claim` with `Evidence` (region + quote); otherwise dropped.
2. **Citation entailment** — NLI/LLM-judge checks the quote entails the sentence (threshold per risk level).
3. **Recomputation** — any number in the finding is recomputed by the tool that produced it; mismatch → reject.
4. **Counter-evidence search** — the Verifier is prompted *adversarially* ("find evidence this is false or explained")
   with retrieval restricted to the investigation scope; hits are attached as `counter_claim_ids`.
5. **Robustness (leave-one-source-out)** — findings are functions of claims, so recompute with each supporting source
   removed; if the conclusion flips on one source, mark it **fragile** (research direction E).
6. **Status** — `supported` / `contradicted` / `undetermined`, never a bare probability unless that score is calibrated.

## 4. Hypothesis Lab

```
"Did Acme and Globex have a contractual relationship during FY2024?"
  → Hypothesis{subject: Acme, predicate: CONTRACTED_WITH, object: Globex, interval: 2024-04-01..2025-03-31}
  → Evidence template: CONTRACTED_WITH claim | invoice(Acme→Globex) | payment(Globex→Acme) | PO referencing contract
  → Search claim store + retrieval for each template slot (supporting and contradicting)
  → Verdict per slot + overall: Supported / Contradicted / Undetermined
  → For Undetermined: "missing evidence that would decide this" ranked by expected information gain  (direction D)
```
Scenario analysis ("what if this contract date were wrong?") = recompute dependent findings with a claim overridden in
an isolated branch; results are labelled hypothetical and never written to the main graph.

## 5. Discovery engine (signals nobody asked for)

Detectors are plugins: `detect(snapshot, params) -> list[Discovery]`, versioned, triggered by events
(`graph.updated`, `document.extracted`) or schedule, each emitting reproducible `Discovery` records with evidence.

**Pack 1 — lender forensic review (primary market; D-numbers match `MARKET_SELECTION.md §7.2`):**

| Detector | Method | Output for the reviewer |
|---|---|---|
| D1 End-use leakage | for each disbursement, trace outflows within N days (bounded BFS over the fund-flow graph, amount-weighted, FIFO/LIFO attribution variants) to non-purpose or connected counterparties | traced path with amounts per hop, attribution method stated |
| D2 Round-tripping | cycles returning to borrower/promoter group (Johnson's algorithm, length ≤ k, time-ordered, amount-similarity tolerance) | cycle with timestamps and per-edge evidence |
| D3 Undisclosed related parties | entity-resolution + shared director/address/account/phone vs `RelatedPartyDisclosure` claims | link chain with identifiers and source pages |
| D4 Turnover contradictions | stock statement vs GSTR-1 vs bank credits vs books per period; tolerance bands | per-period reconciliation table with deltas |
| D5 Invoice integrity | invoices with no GST counterpart; duplicates (vendor+amount±window, MinHash on lines, pHash on scans); splits | grouped duplicates with side-by-side highlights |
| D6 Temporal anomalies | payment before invoice; back-dated documents; period-end spikes (change-point on daily balances) | timeline with the violating pair |
| D7 Document-integrity cues | font/metadata inconsistencies, edited-region heuristics — **for human review only** | visual overlay, never a verdict |

**Pack 2 — procure-to-pay integrity (fallback), plus generic detectors reusable by both packs:**

| Detector | Method | Grounding in practice |
|---|---|---|
| Three-way match break | Invoice ↔ PO ↔ contract: party, amount, quantity, date tolerances | standard AP control |
| Duplicate / near-duplicate invoices | same vendor + amount ± window; MinHash on line items; perceptual hash on scans | classic duplicate-payment audit |
| Duplicate vendors | entity-resolution candidates sharing bank account / address / phone / tax id | vendor-master fraud scheme |
| Vendor–employee overlap | shared address / account between vendor and employee/director entities | conflict-of-interest scheme |
| Benford's-law deviation | first/second-digit distribution per vendor/period; MAD + χ² with sample-size guard | forensic accounting standard test |
| Threshold avoidance | amounts clustering just below approval limits; split invoices | known control-evasion pattern |
| Timeline violations | payment before invoice/approval; activity after contract end | temporal-order check |
| Payment cycles | cycles / round-tripping in the payment graph (Johnson's algorithm, bounded length) | layering pattern |
| Statistical outliers | Isolation Forest / LOF on engineered transaction features, TreeSHAP attributions | unsupervised triage |
| Text ↔ table contradictions | narrative amounts/dates vs table cells in the same document | cross-modal check (direction B) |

Rules: a discovery is a **lead for review**, never an accusation; every detector reports its false-alarm rate on
MindDoc-Synth; analyst dispositions (`confirmed`/`dismissed` + reason) become labelled data for threshold tuning and,
when enough exists, a supervised re-ranker — released only if it beats the current version on held-out data.

## 6. Retrieval router (used by Planner and chat)

Rule-first, learnable later. Features: detected entities, temporal expressions, aggregation words, comparison intent,
document references. Routes: `lexical+dense` (lookup), `graph-local` (entity neighbourhood), `graph-path` (connection
questions), `temporal` (as-of / ordering), `structured` (SQL over claims/tables for sums, counts), `compare`
(two-document diff), or a combination fused with RRF. Logged per query so ablation R3 can learn when each route helps.

## 7. Report generation

Report = ordered findings, each with: statement, status, supporting evidence (thumbnails with highlights),
counter-evidence, method (tool + version), fragility flag, unknowns, reviewer decision. Prose is written by the Writer
role **from the approved finding objects only**; a final verifier pass rejects any sentence without a finding reference.
Export: PDF/HTML with an appendix of lineage JSON.
