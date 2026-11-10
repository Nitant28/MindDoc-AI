# MindDoc hallucination test set (v0)

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
