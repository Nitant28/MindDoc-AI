# MindDoc hallucination test sets (v0 and HB-Synth v1)

Measures whether the claim verifier catches answer sentences that contradict, or are not in, the cited source.

- `cases.py` — 146 hand-labelled claims over 16 fictional lending documents (sanction letter, bank statements,
  invoice, board minutes, loan agreement, GST return, MCA directorship data, stock statement, lease, auditor's
  report, purchase order, email, valuation, insurance policy, credit appraisal).
- Split: **dev** (D1–D8, 74 claims) was used to build and tune the verifier; **test** (T1–T8, 72 claims) was
  scored after the verifier and its NLI threshold were frozen.
- Labels: `supported` (faithful paraphrase, or hard: reformatted numbers/dates, passive voice, number words,
  arithmetic, approximations, unit conversion) or `unsupported` (wrong_number, wrong_scale, wrong_date,
  wrong_period, swapped_parties, negation, direction, wrong_entity, contradiction, invented).
- `legacy.py` — frozen copy of the v1 similarity check, for the baseline column.
- `run.py` — scorer. Positive class = unsupported. Reports catch rate (recall), false-flag rate and F1, each with
  Wilson 95% intervals, per error type.

```bash
python -m benchmarks.hallucination.run --split dev --configs legacy value rules rules+nli --show-errors
python -m benchmarks.hallucination.run --split test --configs legacy value rules rules+nli --nli-threshold 0.95 --report
python -m benchmarks.hallucination.run --split test --configs legacy value rules --hashing --report   # slim/Render embedder
```
`value` = what marks a sentence "contradicts source" (red); `rules` = everything the UI flags (red + amber
"check wording"). Results and analysis: `../reports/HALLUCINATION_BENCHMARK.md`.

## Limitations — read before quoting a number

1. **Not independent.** The same developer wrote the cases and the verifier. The test split was held out from
   tuning, but its author knew which error types the verifier targets. Treat the test numbers as an upper bound on
   real-world performance, and replace them with a third-party set (e.g. RAGTruth) or labelled production answers.
2. **Small.** 44–45 unsupported and 28–29 supported claims per split: the 95% intervals are wide (±10–15 points).
3. **Claim-level, single source.** Each case is one sentence against one passage. Real answers mix several claims
   and several passages; retrieval errors are not measured here.
4. **Synthetic, one domain, English.** Indian lending documents with ₹ amounts. Other domains will differ.
5. **The rules are heuristics.** Paraphrases with new numbers (unit conversions, percentages computed from two
   figures) are flagged as unsupported; contradictions that use only the source's own words often pass.

## HB-Synth v1 (R6): generated, held-out test

`synth.py` generates 1,092 claims: dev 492 (44 documents, 11 families) and test 600 (56 documents, 14 families).
Families: sanction letter, statement table, invoice, board minutes, lease, two-year financials, valuation,
insurance schedule, GST return, repayment clause, director data; **test only:** guarantee deed, fund-flow note,
borrower correspondence. The output is deterministic (string seeds per split, family and document).

What the test split holds out:
- **names:** companies, people, banks, cities, valuers and insurers come from disjoint pools;
- **phrasing:** every passage template and every claim template has a separate test wording;
- **layouts:** test statements use "Withdrawals (Dr) / Deposits (Cr)" headers, test financials are a table in
  ₹ crore, test invoices state no totals (they must be computed);
- **document families:** three families appear only in test.

Each claim has a `type` (as in v0, plus `arithmetic` for a wrong computed figure) and a `tag` naming the failure
class it targets: `converse` (rents from / leases to), `computed_pct`, `computed_total`, `computed_product`,
`computed_ratio`, `computed_pct_change`, `computed_diff`, `period_conversion`, `unit_conversion`, `interval`,
`from_to`, `declined` (refused vs decreased), `possessive`, `table_column`, `negation_paraphrase`, and others.

### Pre-registration (committed before any verifier v3 change)

- **Primary result:** red tier (`value` config) catch rate and false-flag rate on HB-Synth v1 **test**, with Wilson
  95% intervals, MiniLM embeddings (hashing embedder as a secondary run).
- **Acceptance (J_ROADMAP R6):** red-tier catch ≥ 68% (the v0 test result) and false flags ≤ 10%.
- **Comparison:** `legacy` (v1), `v2-value` / `v2-rules` (frozen v2, `verifier_v2_frozen.py`) and `value` /
  `rules` (current) are all scored on test once, at the same final commit. `run.py` refuses to score the test split
  without `--final` or with uncommitted changes under `app/ai` or `benchmarks/hallucination`.
- **Tuning:** rules may be changed using HB v0 (both splits are now known) and HB-Synth v1 **dev** only. HB v0 test
  numbers after this point are reported as "no longer held out".
- **Calibration:** any probability model is fitted on dev only and evaluated on HB-Synth test: ECE (10 equal-width
  bins), adaptive ECE, Brier, with bootstrap 95% intervals. A probability may be displayed only if test ECE ≤ 0.1,
  and, because this set is synthetic with about 59% unsupported claims, not to users until it is re-checked on
  labelled real answers.
- **Label audit:** one document per family in each split was read by the developer to check labels before any
  scoring. One ambiguous test claim (a recall threshold that was still "technically true") was rewritten. No
  verifier was run on test.

### Annotation guideline (used by the generator; the same rules for independent annotators)

1. Read only the passage. A claim is **supported** if a careful credit analyst would accept it as stated by the
   passage.
2. Allowed: paraphrase; reformatted numbers (₹12,40,000 = ₹12.4 lakh = Rs 12.40 lakh) and dates; converse verbs
   (A leases to B = B rents from A); passive voice; unit conversion (36 months = 3 years; a monthly figure × 12 =
   the annual figure when nothing else changes); simple arithmetic over stated figures (sum, difference, product,
   percentage, ratio); a computed percentage rounded to a whole number; "about/roughly" for a figure within 3%.
3. **Unsupported:** any figure, date, name, period or relation that is not stated or computable; a direction
   (debit/credit, rose/fell, above/below, includes/excludes) opposite to the passage; swapped roles; a flipped
   negation; a changed threshold or condition even if it is "technically" still true; a table entry read from the
   wrong column.
4. One label per claim. Exclude claims you cannot decide (mark them `ambiguous` and drop them before scoring).
5. Two annotators label independently; report agreement with `agreement.py` (Cohen's κ); a third person
   adjudicates disagreements before scoring.

External sets use JSONL, one claim per line:
`{"passage": "...", "claim": "...", "label": "supported" | "unsupported", "type": "...", "question": "..."}`

```bash
python -m benchmarks.hallucination.run --set synth --split dev --configs v2-value value rules --show-errors
python -m benchmarks.hallucination.run --set synth --split test --configs legacy v2-value v2-rules value rules --final --report
python -m benchmarks.hallucination.agreement annotator_a.jsonl annotator_b.jsonl
python -m benchmarks.hallucination.run --file adjudicated.jsonl --configs value rules --report
```

### Result (scored once, 2026-11-12, commit `28d868a`)

v3 red tier: caught 72% (95% CI 67–76%), wrongly flagged 11% (8–16%); v2 71% / 30%. The pre-registered false-flag
target (≤ 10%) was **not met**. Full tables, per-class results, calibration and test-revealed bugs:
`../reports/HALLUCINATION_BENCHMARK.md`. The test split has now been seen: fixes for what it revealed need a fresh
held-out set.

### HB-Synth v1 limits

1. **Same developer.** Templates and verifier were written by the same person. The held-out phrasing, names and
   families reduce, but do not remove, the bias. An independent annotated split (two annotators, the guideline
   above) is still required by J_ROADMAP R6 and is an owner action.
2. **Generated text is regular.** Real LLM answers mix claims, hedge, and cite several passages.
3. **One error per unsupported claim**, one passage per claim, English, Indian lending documents.
