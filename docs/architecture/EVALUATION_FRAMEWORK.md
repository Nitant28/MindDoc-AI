# MindDoc — Evaluation Framework (proposal v0.1)

> Principle: **no capability is claimed until it has a metric, a baseline, a reproducible run and a stored result.**
> Dataset choices and licences: `docs/research/BENCHMARK_DATASETS.md`. Results land in `benchmarks/reports/` and the
> System page reads them — the UI never shows a number that a script didn't produce.

## 1. Harness

```
benchmarks/
  datasets/<name>/MANIFEST.json      # source URL, licence, version, sha256 of every file, split definition
  suites/<layer>/<suite>.py          # pure function: (system_config, dataset) -> per-item records
  runs/<run_id>/                     # config.json (git sha, model versions, prompt versions, seeds), records.jsonl
  reports/<run_id>.md + .json        # aggregated metrics with 95% bootstrap CIs
```
- Every run pins: git commit, dataset manifest hash, model ids + versions, prompt template versions, random seeds.
- LLM-dependent suites run **3 seeds / repeats** and report mean ± CI; deterministic suites run once.
- Comparisons between systems use **paired** tests on the same items (paired bootstrap or McNemar for accuracy).
- CI runs a **smoke subset** (≤ 2 min, offline, hashing embeddings) on every commit; full suites run on demand.

## 2. Metrics by layer

| Layer | Metric | Definition / note |
|---|---|---|
| OCR | CER, WER | edit distance / reference length, after Unicode NFKC + whitespace normalisation |
| Layout | mAP@[.5:.95], per-class AP | COCO protocol on DocLayNet-style labels |
| Tables | cell-level F1, TEDS | structure + content; GriTS if using PubTables-1M |
| Field extraction | per-field P/R/F1, exact & normalised match | normalise dates/amounts/currency before comparing |
| Grounding | **box IoU ≥ 0.5 hit-rate** | predicted evidence region vs gold region for each extracted value |
| Retrieval | Recall@k, MRR, nDCG@10, latency p50/p95 | gold passages per question; also report "no-answer" handling |
| RAG answers | faithfulness, answer correctness, context precision/recall | LLM-judge **validated against ≥100 human labels** (report judge agreement κ) |
| Citations | citation precision / recall | ALCE-style: does each cited passage entail its sentence; is each claim cited |
| Unsupported claims | % answer sentences not entailed by any retrieved evidence | the headline trust metric |
| Abstention | precision/recall of "not in documents" on answerable vs unanswerable questions | |
| Entity resolution | pairwise P/R/F1, B³ F1, merge-error rate | false merges weighted ×5 in the cost view (they corrupt the graph) |
| Relations / claims | triple P/R/F1 (strict & relaxed), temporal-qualifier accuracy | |
| Contradictions | P/R/F1 per kind; **false-alarm rate per 100 documents** | analysts care about review load |
| Anomaly discovery | Precision@k, PR-AUC, recall of injected anomalies | only on datasets with ground truth (synthetic injection) |
| Calibration | ECE, Brier, reliability diagram | for any score shown as a probability |
| Agents | task success, tool-selection accuracy, step-level error rate, human-intervention rate, cost & tokens per task | trajectory-level evaluation, not final answer only |
| Robustness | conclusion flip-rate under leave-one-source-out | see RESEARCH_GAPS direction E |
| Security | prompt-injection attack success rate, cross-tenant leakage tests (must be 0) | red-team suite |
| Systems | docs/min throughput, end-to-end ingest latency, consumer lag, DLQ rate, cost/doc | |

## 3. Ablation matrix (the research story)

| ID | Question | Arms |
|---|---|---|
| R1 | Does hybrid beat dense? | BM25 · dense · hybrid RRF · hybrid + rerank · + contextual prefix |
| R2 | When does graph retrieval help? | hybrid vs hybrid + GraphRAG-local vs router-selected — split by question type (lookup / multi-hop / aggregation / temporal) |
| R3 | Does the router save cost without losing quality? | fixed full pipeline vs adaptive router: quality Δ vs tokens/latency Δ |
| V1 | Does layout-aware extraction beat plain OCR text? | OCR text → LLM vs layout/table-aware → LLM, on field F1 + grounding IoU |
| G1 | Does evidence-calibrated confidence rank true relations higher? | raw extractor confidence vs calibrated multi-signal score: AUC, ECE |
| D1 | Does graph context improve anomaly discovery? | tabular IsolationForest vs + graph features vs + text features |
| A1 | Does a verification pass reduce unsupported conclusions? | agent report without vs with verifier + counter-evidence search |

A result that favours the baseline is reported and **changes the product default** (e.g. if GraphRAG loses on lookup
questions, the router stops using it there).

## 4. The custom investigation benchmark (MindDoc-Synth)

Synthetic but realistic, modelled on the primary market (lender forensic review): a seeded generator of a fictional
borrower group — companies, directors (DIN), addresses, bank accounts across several banks, 24 months of bank
statements in common Indian layouts, sanction letters and disbursements, invoices, GSTR-1/3B summaries, stock
statements, ledgers and related-party disclosures — rendered to PDF/XLSX and to *degraded scans* (blur, noise, skew,
JPEG). It injects **labelled** schemes (end-use leakage via supplier pass-through, round-tripping cycles, undisclosed
related parties via shared directors/addresses, turnover mismatches, duplicate/split invoices, back-dating) **and
benign look-alikes** (legitimate supplier payments, genuine group transfers, seasonal spikes) so false-positive rates are
measurable. Ground truth is emitted by the generator, so labels are exact and the set regenerates at any size. Released
with a datasheet; no real names or identifiers.

## 5. What the current v2 already measures (and its limits)

`/api/intel/eval` reports self-supervised Hit@5/MRR with BM25/dense/hybrid ablation. Limits: inverse-cloze queries
favour BM25; no gold answers; no grounding, extraction, ER or agent metrics. It becomes suite `retrieval/self_supervised`
in the harness and stays as a cheap regression signal.
