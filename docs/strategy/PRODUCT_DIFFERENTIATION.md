# MindDoc — Product & Research Differentiation (Stage D)

> Sources: `COMPETITIVE_ANALYSIS.md` (requirements R1–R10), `MARKET_SELECTION.md`, `../research/INDUSTRY_LANDSCAPE.md`,
> `../research/RESEARCH_GAPS.md`. Everything below marked **claim** is a target until a benchmark run supports it.

## 1. Why it is valuable (to whom)

A forensic partner reviewing a borrower's fund flows today reconciles bank statements, ledgers, invoices, GST returns
and director data by hand in Excel/IDEA, then writes a report that the borrower is now ordinarily entitled to see with
the "material relied upon". MindDoc's value is **time to a defensible draft**: findings that are traced, recomputed,
challenged and reviewer-approved, with an evidence bundle that withstands scrutiny. Pilot KPIs (MARKET_SELECTION §7.4):
≥50% less time to partner-reviewed findings, ≥90% recall vs the firm's final report, 100% traceability, 0 numeric
mismatches.

## 2. What already exists (be honest about it)

| Capability | Who already does it well |
|---|---|
| Ontology of objects, links and governed actions; AI proposes, humans commit | Palantir Foundry/AIP |
| Entity resolution + network analytics for financial crime | Quantexa |
| Full-population anomaly scoring of ledgers | MindBridge, Caseware IDEA (adding agents) |
| Bank-statement analysis for lenders | Perfios (credit, not forensic) |
| Graph-based RAG with community summaries | Microsoft GraphRAG |
| Multimodal extraction → embed → rerank pipelines | NVIDIA NeMo Retriever; Azure/Google document AI |
| Agent runtimes with tools, guardrails, tracing | OpenAI Agents SDK, Google ADK |
| Citations grounded in source spans | Anthropic Citations, Azure DI polygons |

None of these is MindDoc's competitor in the target segment *as a product*, but each sets the engineering bar.

## 3. Where MindDoc is differentiated (the combination, not any single part)

| # | Differentiator | Versus | Proof required |
|---|---|---|---|
| 1 | **Claim-centric, bitemporal evidence graph** — claims vs facts, valid vs system time, append-only reviews | entity graphs with a single confidence number | lineage completeness 100%; time-travel/diff queries demonstrably correct on synthetic incremental cases |
| 2 | **Self-verifying extraction** — bank-statement running-balance reconciliation, identifier checksums, recomputation of every number | "99% accuracy" extraction claims | ≥99% of statement pages reconcile on the test set; 0 recomputation mismatches |
| 3 | **Cross-document fund-trail reasoning** across statement ↔ ledger ↔ invoice ↔ GST ↔ director data (R1) | GL-only analytics, IDP that extracts but doesn't investigate | seeded-scheme recall ≥90% with ≤1 false flag per 10 benign look-alikes |
| 4 | **Explainable Indian-identifier entity resolution** with reversible human merges (R2) | name-similarity matching | high-risk merge precision ≥0.98 |
| 5 | **Evidence-constrained investigation** — few LLM roles over deterministic tools; verifier with counter-evidence and leave-one-source-out fragility | chat assistants, agent demos | unsupported-claim rate and fragile-finding detection measured (ablation A1) |
| 6 | **Pixels-to-report provenance + evidence bundle export** (R3) | citations to whole documents | every report sentence → finding → claim → region in ≤2 clicks |
| 7 | **Deployable where data lives, licence-clean** (R6) | cloud-only SaaS; stacks with AGPL/NC models | runs offline on a laptop-class machine; dependency licence audit in CI |
| 8 | **Published, reproducible evaluation** (R9) | unverifiable vendor claims | public scorecard + generator + datasheet |

## 4. What could be genuinely new (research) — and what is not

From `RESEARCH_GAPS.md` (all five directions have close prior work; nothing is "novel" until checked):

| Direction | Verdict | Plan |
|---|---|---|
| **E. Robustness of findings to source removal** (closest: CUE-R, 2026, which lists agentic workflows as future work) | small–medium gap, **highest feasibility** — ground truth comes from re-running the pipeline, no labels needed | **pursue first**: fragility metric for agent-produced findings on MindDoc-Synth + MultiHop-RAG; workshop target |
| A. Evidence-calibrated graph confidence (closest: Knowledge-Based Trust; Evidence Laundering, EMNLP 2026) | small–medium gap | second: uses E's instrumentation; source-independence clustering is the angle |
| B. Cross-modal contradiction detection (closest: Kontrast 2026, FinDVer, MMIR) | medium gap; benchmark + baseline could reach a D&B track | build the detector for the product (D4) anyway; publish only with a released benchmark |
| C. Temporal reconstruction | medium gap but classical tools | engineering, not a paper |
| D. Active evidence acquisition (closest: BED-LLM, ICLR 2026) | medium–large gap, needs a simulator and depends on A | later, labelled experimental |

Caveat: the research files tag 72 references as cited from memory ([K]); verify every one before citing it anywhere.

## 5. What must NOT be claimed

- That MindDoc is better than Palantir, Quantexa, MindBridge or any platform overall.
- Any accuracy, speed or savings number not produced by a stored benchmark or pilot run.
- That a finding, anomaly score or document-integrity cue indicates **fraud** or **forgery** — they are leads for a
  professional's judgement (ICAI FAIS).
- That a score is a probability unless it has been calibrated on held-out data (report ECE).
- Novelty of any research direction before the literature check is complete.
- Production readiness, compliance (DPDP, SOC 2) or security certification before independent review.

## 6. The honest pitch (to be filled with real numbers)

> MindDoc turns a borrower's case file — scanned statements, ledgers, invoices, GST returns and director records — into
> a claim-level evidence graph where every value is anchored to a page region and every number is recomputed. Forensic
> detectors and calibrated anomaly models surface fund-trail leads; an evidence-constrained investigator drafts findings
> that are checked for citation support, counter-evidence and dependence on any single source; and a reviewer approves
> them into a report whose every sentence resolves to pixels. On our seeded benchmark it recovers **[X]%** of injected
> schemes at **[Y]** false flags per case, and in a retrospective pilot it cut time-to-draft by **[Z]%**.
