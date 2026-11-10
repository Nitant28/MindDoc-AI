# H — Benchmark and dataset strategy

**Purpose.** Every capability on the roadmap (J) gets a benchmark *before* it is built, so the claim "it works" is
always a number with an interval, measured on data the builder did not tune on. Today exactly one benchmark exists
(the claim verifier, §9 of PROJECT_CONTEXT), and it is small, synthetic and developer-written. This plan fixes that
in the order the product needs it.

## 1. Rules that apply to every benchmark

1. **Dev/test split, test scored once per release.** Tuning uses dev only. A test-split result is recorded with the
   commit hash; if code changes after seeing test errors, the next test number comes from a *new* or *extended* test
   split.
2. **Independent authorship for test data.** At least half of every test split is written or labelled by someone
   other than the developer of the component (a CA student, a pilot partner analyst, a contractor), with a written
   guideline. Report inter-annotator agreement (Cohen's κ or Krippendorff's α) on a double-labelled sample.
3. **Intervals, not points.** Wilson 95% intervals for rates; bootstrap intervals for F1/TEDS-style metrics.
   Minimum sizes are chosen so the interval half-width is ≤ ±5 points for headline metrics (≈ 400 items for a rate
   near 50%; fewer near 0/100%).
4. **Per-type breakdowns.** Every headline number is broken down by error type / document class so a good average
   cannot hide a failing class.
5. **Reproducible.** Generators are seeded; datasets are versioned (`v0`, `v1` …) with a datasheet (source, licence,
   authors, known biases); runners write JSON + a Markdown report to `benchmarks/reports/`.
6. **Regression guards in CI.** A small, fast subset of each benchmark runs on every push with a floor
   (as `tests/test_verifier.py` does now). Full runs happen per release.
7. **No real personal data in the repository.** Real documents (if any are ever used) live outside git, under a
   data-processing agreement, with access logged; only aggregate metrics are committed.

## 2. Benchmark portfolio (priority order)

| ID | Benchmark | Measures | Needed before | Status |
|---|---|---|---|---|
| **SB** | **StatementBench** — bank-statement extraction and reconciliation | rows, fields, direction, balances, reconciliation, error localisation, false alarms, CPU throughput | Phase 3 parser (flagship) | PLANNED (this doc) |
| HB | Hallucination / claim-verification set v1 | catch rate, false-flag rate, per error type | verifier round 2 | v0 exists (146 claims) |
| FB | Fund-flow case benchmark (MindDoc-Synth cases) | seeded-scheme recall, false flags per benign look-alike, evidence completeness | Phase 6 detectors | PLANNED |
| EB | Entity-resolution benchmark | high-risk merge precision/recall, pairwise and cluster F1 | Phase 4 Splink | PLANNED |
| DB | DocBench-50 (OCR, layout, tables on mixed documents) | CER/WER, layout F1, TEDS / cell F1, s/page | ADR-0006 swaps | PLANNED |
| RB | Retrieval QA set | Hit@k, MRR, nDCG on human-written queries | Postgres retrieval (Phase 5) | PLANNED (pseudo-query eval exists) |
| CB | Calibration set | ECE / reliability of the evidence score | showing any score as a probability | PLANNED |
| LB | Fragility benchmark | agreement of LOSO fragility with ground-truth necessity | research direction E | proposal in I |

## 3. StatementBench (SB) — flagship design

### 3.1 Data sources (three tiers)
1. **SB-Synth (primary, fully labelled).** A seeded generator produces:
   - *account histories*: opening balance, a transaction stream with realistic Indian modes (UPI, NEFT, RTGS, IMPS,
     NACH, cheque, cash, charges, interest, reversals), counterparties drawn from a synthetic entity set (shared
     with MindDoc-Synth cases so fund-flow ground truth is consistent), running balances computed exactly in paise;
   - *renderings* of the same history in several **layout families** (separate Withdrawal/Deposit columns; single
     amount column with Dr/Cr suffix; balance with Cr/Dr suffix for overdraft/CC accounts; value-date column present
     or absent; multi-line narrations; repeated page headers; "balance brought forward" rows; summary boxes);
     layouts are parameterised, not copies of any real bank's design or branding;
   - *degradations* for scan simulation: rasterise → skew, blur, noise, JPEG compression, low DPI, stamps/handwriting
     overlays, cropped margins;
   - **ground truth**: per row and per cell — values, direction, bounding boxes, page, and the layout family.
2. **SB-Public.** Publicly licensed sets found by `research/BANK_STATEMENT_RESEARCH.md`:
   - [AgamiAI/Indian-Bank-Statements](https://huggingface.co/datasets/AgamiAI/Indian-Bank-Statements): synthetic,
     Apache-2.0 **[verified licence]**, current accounts only. Use as an external, non-MindDoc-generated test of
     layout generalisation.
   - The Bankstatemently benchmark: MIT, 5 statements released; the Indian one is "coming soon" **[u]**.
   - SynFinTabs: MIT, financial tables only; useful for the table component, not for whole statements **[u]**.

   **No public, real, annotated Indian bank-statement set exists**, so SB-Real (tier 3) is indispensable for credible
   claims.
3. **SB-Real (later, consented).** 20–50 real statements from pilot partners, redacted, under a data-processing
   agreement, labelled by the partner's analysts with our guideline; kept outside git. This is the tier that turns a
   synthetic result into a credible one. Until it exists, every SB number must be labelled "synthetic".

### 3.2 Splits
- Dev: layout families A–D, all degradations. Test: **held-out layout families** E–F (never seen in development) +
  held-out degradation seeds — this measures generalisation to new bank formats, which is the real risk.

### 3.3 Metrics

| Metric | Definition |
|---|---|
| Row recall / precision | a predicted row matches a gold row if date, amount (exact paise) and direction match and the row bbox IoU ≥ 0.5 |
| Field accuracy | exact-match rate per field: txn date, value date, debit, credit, balance, balance side, reference/UTR; normalised-edit-distance for narration |
| Direction accuracy | share of rows with the correct debit/credit direction |
| Statement reconciliation rate | share of statements where opening + Σcredits − Σdebits = closing and every row's running balance checks, using **extracted** values |
| Error localisation | on statements with injected single-row extraction errors (digit swaps, dropped rows, merged rows), share where the first failing check points at the erroneous row (±0) |
| False-alarm rate | share of perfectly extracted statements on which any reconciliation check fails (must be ~0: checks are exact arithmetic) |
| Review load | flagged rows per 100 rows |
| Throughput | seconds per page on a 2-vCPU CPU host; peak RSS; both for the slim and ML profiles |

### 3.4 Acceptance targets (set after the first baseline; proposals)
- Text-layer statements, held-out layouts: row F1 ≥ 0.99, amount and direction accuracy ≥ 0.995, reconciliation
  rate ≥ 0.98, false alarms = 0.
- Scanned (moderate degradation): row F1 ≥ 0.95; every remaining extraction error is *caught* by a failing check or
  a low-confidence flag (silent error rate ≤ 0.5% of rows).
- Throughput (slim profile): ≤ 1 s/page text-layer, ≤ 8 s/page scanned, within 512 MB.
These are targets to argue about, not results.

## 4. Other benchmarks (summary specs)

- **HB v1 (claims).** Grow to ≥ 500 claims: keep v0 as dev; add a test split written by two independent annotators
  over new documents, including the failure classes found in v0 (converse verbs, computed percentages, table-column
  semantics, "declined"). Add an external sanity check on a public RAG hallucination set (e.g. RAGTruth's QA subset,
  after verifying its licence) to measure false flags on real LLM answers.
- **FB (cases).** MindDoc-Synth borrower groups with seeded schemes (fund diversion to related parties, round-tripping,
  circular transfers, invoice inflation vs GST, end-use deviation, structuring around thresholds) **and benign
  look-alikes** (legitimate supplier payments, sweep transfers, FD creations). Ground truth: which transactions and
  documents constitute each scheme. Metrics: scheme recall, false flags per 10 benign look-alikes, evidence
  completeness (share of gold evidence cited), and — later — reviewer minutes per finding.
- **EB (entities).** Synthetic name/identifier variants (abbreviations, punctuation, "Pvt Ltd" forms, typos,
  transliterations, shared addresses, conflicting identifiers). Metrics: pairwise precision/recall at the auto-merge
  band, high-risk-merge precision (merges that would join two entities with different valid PANs/GSTINs must be 0).
- **DB (DocBench-50).** 50 labelled pages across classes (digital, scanned, tables, forms, stamps) for CER/WER, layout
  F1 and table TEDS + cell F1; the gate for any ADR-0006 component swap.
- **RB (retrieval).** 200+ human-written questions over the synthetic corpus with gold passages; Hit@5, MRR, nDCG@10;
  ablations hybrid vs dense vs FTS vs BM25 (ADR-0002 R1).
- **CB (calibration).** Answers labelled correct/incorrect (from HB and RB runs); reliability diagram, ECE; only after
  ECE ≤ 0.1 on held-out data may any score be shown as a probability.
- **LB (fragility).** Defined in I.

## 5. Infrastructure

```
benchmarks/
  hallucination/            (exists)   cases, runner, legacy baseline
  statements/                          generator (seeded), layouts/, degrade.py, gold/, run.py, README (datasheet)
  cases/                               MindDoc-Synth borrower groups + schemes
  entities/  docbench/  retrieval/  calibration/  fragility/
  reports/                             <bench>-<split>-<profile>-<date>.json + .md, never edited after commit
```
- Every runner prints and stores: commit hash, profile (slim/ML), model versions, seeds, wall time, peak memory.
- A scorecard page (System page or `benchmarks/reports/SCORECARD.md`) shows the latest result per benchmark with its
  interval and data tier (synthetic / public / real).

## 6. Data governance for any real data
- Written consent / DPA with the provider; purpose limited to evaluation; retention limit; deletion on request.
- Redaction before labelling (names, account numbers, PAN/Aadhaar), stored encrypted outside git, access logged.
- Only aggregate metrics leave the secure environment.
- See D for DPDP Act obligations.

## 7. Build order
1. SB-Synth generator + metrics + baseline of the *current* parser (it will score poorly — that is the point).
2. HB v1 independent test split (re-measure verifier v2 honestly).
3. EB synthetic set (needed with Phase 4).
4. FB cases (needed with Phase 6), DB, RB, CB as their phases start.
