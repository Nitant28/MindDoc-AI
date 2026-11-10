# Claim verifier v1 → v2: hallucination benchmark (2026-11-10)

**Question:** when an answer sentence contradicts, or is not in, the passage it cites, does MindDoc flag it — and how
often does it wrongly flag a correct sentence?

**Data:** `benchmarks/hallucination/cases.py` — 146 hand-labelled claims over 16 fictional Indian lending documents.
Dev split (74) was used to build and tune v2; **test split (72) was scored once, after the rules and the NLI
threshold were frozen.** Raw per-claim results: `hallucination-{dev,test}-{minilm,hashing}-2026-11-10.json`.

**Systems:**
- **v1:** the shipped similarity + word-overlap check, frozen in `benchmarks/hallucination/legacy.py`.
- **v2 red:** the value checks, which mark a sentence "contradicts source". They cover numbers (including
  lakh/crore), dates, IDs, periods, party names and content that isn't in the source.
- **v2 red + amber:** red, plus the wording heuristics shown as "check wording": negation, direction words and
  party roles.
- **+NLI:** LettuceDetect `tinylettuce-ettin-68m-en` (MIT) at threshold 0.95. It is off by default (see below).

## Headline: held-out test split (MiniLM embeddings)

| | Errors caught (of 44) | Correct sentences wrongly flagged (of 28) | F1 |
|---|---|---|---|
| v1 (before) | 9 = **20%** (95% CI 11–35%) | 4 = **14%** (6–31%) | 0.32 |
| **v2 red (after, decides "not supported")** | 30 = **68%** (53–80%) | 3 = **11%** (4–27%) | 0.78 |
| v2 red + amber (everything the UI flags) | 40 = 91% (79–96%) | 12 = 43% (27–61%) | 0.83 |
| v2 red + amber + NLI | 40 = 91% (79–96%) | 15 = 54% (36–70%) | 0.81 |

With the offline hashing embedder that the slim Render image runs:
- **v1:** catches 18%, wrongly flags 29%.
- **v2 red:** catches 68%, wrongly flags 18%.
- **v2 red + amber:** catches 91%, wrongly flags 50%.

Dev split (used for tuning, so optimistic):
- **v1:** catches 11%, wrongly flags 10%.
- **v2 red:** catches 71%, wrongly flags 7%.
- **v2 red + amber:** catches 93%, wrongly flags 7%.
- **v2 red + amber + NLI:** catches 96%, wrongly flags 10%.

## By error type (test split, number caught or wrongly flagged)

| Type | n | v1 | v2 red | v2 red + amber | v2 red (hashing) |
|---|---|---|---|---|---|
| wrong number | 9 | 1 | **9** | 9 | 9 |
| wrong scale (lakh ↔ crore) | 2 | 0 | **2** | 2 | 2 |
| wrong date | 7 | 1 | **7** | 7 | 7 |
| wrong period (per month ↔ per year) | 2 | 0 | **2** | 2 | 2 |
| wrong party name | 4 | 0 | **4** | 4 | 4 |
| invented content | 7 | 6 | 6 | 7 | 6 |
| negation flipped | 4 | 0 | 0 | 4 | 0 |
| direction (rose/fell, above/below, credit/debit) | 4 | 1 | 0 | 2 | 0 |
| parties swapped | 4 | 0 | 0 | 3 | 0 |
| subtle contradiction | 1 | 0 | 0 | 0 | 0 |
| *faithful (wrongly flagged)* | 9 | 0 | 1 | 3 | 1 |
| *faithful, hard (wrongly flagged)* | 19 | 4 | 2 | 9 | 4 |

## What this shows

1. **Value errors are now caught almost completely.** Wrong amounts, lakh/crore scale slips, dates, payment
   periods and party names went from 2/24 caught to 24/24 on the held-out split. v1 couldn't see any of them,
   because they share almost every word with the source.
2. **Meaning errors are not reliably caught.** Flipped negation, swapped payer/payee and rose/fell are only
   caught by the wording heuristics. On test those heuristics found 12 real errors but also flagged 9 correct
   sentences: dev had 0 such false flags, so they overfit dev phrasings. That's why they show as amber
   "check wording" and don't count against the answer.
3. **The NLI model did not help on test.** It added no catches and 3 more false flags, so it ships disabled
   (`ENABLE_NLI_VERIFIER=false`). The larger LettuceDetect base model (598 MB) was not evaluated.
4. **Known false flags in the red tier:**
   - Percentages computed from two source figures ("about 80% of the fair market value").
   - An entity-span bug with a plural possessive followed by an acronym ("Sunrise Traders' FY").

## Caveats

- The decision to show wording heuristics as amber, and to switch NLI off, was made **after** seeing the test
  results. No rule was changed after the test run; only how the existing outputs are grouped.
- `tests/test_verifier.py` has a regression guard (≥90% of number/scale/date/period/party errors caught on both
  splits). It ran once before the final scoring and passed; it reports pass/fail only, and no rule was changed
  because of it.
- The same developer wrote the cases and the verifier. Treat these numbers as optimistic, and replace them with a
  third-party set (e.g. RAGTruth) or labelled production answers.
- The set is small: read the confidence intervals. It covers one domain and one language, with single-claim
  cases.

## Next steps (not done)

1. Fix the test-revealed bugs and score on a **fresh** labelled set, not this test split again. The bugs:
   - converse verbs (rents *from* / leases *to*)
   - local passive detection
   - "declined" meaning both *refused* and *decreased*
   - plural-possessive entity spans
   - computed percentages
   - table column semantics (Debit/Credit headers)
   - "from X to Y" arithmetic for rose/fell
2. Independent evaluation on RAGTruth (QA subset) to measure false flags on real LLM answers.
3. Calibrate the evidence score against these labels (backlog Phase 5).
