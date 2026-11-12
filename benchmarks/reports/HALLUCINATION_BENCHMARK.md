# Verifier v3.1 (the five R6 fixes) on HB-Synth v2 (2026-11-13)

**Question:** do the fixes for the five bugs that HB-Synth v1's test exposed hold up on text written after those bugs
were known but before the fixes were written?

**Data:** HB-Synth v2 (`benchmarks/hallucination/synth2.py`), 610 claims (280 supported, 330 unsupported) over 60
documents of twelve document types that appear in no earlier set. It was pre-registered in `e472438` before any fix.
The fixes were tuned on HB v0 and both HB-Synth v1 splits only. **The set was scored once**, at `90dbf32` (clean
tree), for every configuration. Raw rows: `hbsynth2-test-{minilm,hashing}-2026-11-13.json`.

## Headline (MiniLM embeddings)

| | Errors caught (of 330) | Correct sentences wrongly flagged (of 280) | F1 |
|---|---|---|---|
| v1 (similarity only) | 45% (95% CI 40–50%) | 36% (30–41%) | 0.51 |
| v2 red | 77% (72–81%) | 54% (48–59%) | 0.69 |
| v3 red (as scored on HB-Synth v1) | 78% (73–82%) | 41% (35–47%) | 0.73 |
| **v3.1 red (decides "not supported")** | **74% (69–78%)** | **21% (16–26%)** | **0.77** |
| v3.1 red + amber (everything the UI flags) | 84% (80–88%) | 26% (21–32%) | 0.82 |

**Acceptance (pre-registered, unchanged from R6):** catch ≥ 68% **met** (74%). False flags ≤ 10% **not met**
(21%).

With the hashing embedder (slim/Render image):
- **v2 red:** catches 81%, wrongly flags 57%.
- **v3 red:** catches 82%, wrongly flags 48%.
- **v3.1 red:** catches 77%, wrongly flags **23%**.

**What it shows.**
- The fixes roughly halve the false flags again on unseen text (41% → 21%). The slim embedder now behaves like
  MiniLM (23%) instead of much worse.
- This set is much harder than v1: v3 went from 11% false flags on v1 to 41% here.
- The 10% target is still far off.

## Where the 58 false flags come from

| Cause | Count | Status |
|---|---|---|
| Claim kinds declared unhandled when the set was written: three-figure total, date + days, label written after the figure, "₹10 each" | 20 | known gaps |
| Term sheet with units only in the column header ("Rate (% p.a.)", "Tenor (months)"): 10.75 is not read as a percentage, 60 not as months; "the two facilities" counts "two" as a figure | 20 | new, found here |
| Relevance check on plain paraphrase ("The month ended with a balance of …", "The money went straight to the machinery supplier") | 18 | reduced, not solved |

## The five fixed classes on held-out text (red tier, flagged of n)

| Class | n | v3 | v3.1 |
|---|---|---|---|
| correct: figure or difference from a table in ₹ lakh | 25 | 25 | **0** |
| correct: ratio, percentage or product from "Label: value" figures | 30 | 25 | **5** |
| correct: reformatted figures and dates | 45 | 2 | 0 |
| correct: plain paraphrase | 65 | 22 | 18 |
| wrong lakh/crore scale against a ₹ lakh table | 10 | 10 | 10 |
| wrong computed percentage, product, ratio, total | 35 | 33 | 33 |

## Errors no longer caught (14 vs v3; none gained)

- **5 swapped parties and 5 figures attributed to the wrong year.** v3 flagged these only because it could not read
  the ₹ lakh table, so every figure looked wrong. Now the figures match, and v3.1 does not check which column a
  figure came from.
- **4 "raised from A to B" where A > B.** "Raised" is not among the change verbs. v3 flagged these through the
  relevance check, which now counts the verified figures.

## Calibration

The model was refitted on the non-held-out reports (1,238 claims) and frozen in `90dbf32`. On HB-Synth v2:

| Metric | Value | 95% CI |
|---|---|---|
| ECE | 0.110 | 0.090–0.140 |
| Adaptive ECE | 0.097 | 0.084–0.139 |
| Brier | 0.168 | — |

It is too sure that flagged sentences are wrong: in its lowest bin it predicts 1.6% supported, and 16.5% are. ECE is
above 0.1, so **no probability is displayed**. Report: `calibration-hbsynth2-test-minilm-2026-11-13.json`.

## Caveats

- The same developer wrote HB-Synth v2 and the fixes, knowing the five bug classes. The set includes claim kinds
  outside the fix list on purpose; they are a third of the false flags. Still not an independent test.
- HB-Synth v2 has now been seen. Any fix for the term-sheet header units or the relevance check needs another fresh
  set, or the independently annotated split (owner action).

---

# Claim verifier v3 on HB-Synth v1 (R6, 2026-11-12)

**Question:** on a fresh, larger set built before any change, does verifier v3 (recomputation, money direction,
change arithmetic, wording fixes) flag fewer correct sentences than v2 without catching fewer errors?

**Data:** HB-Synth v1 (`benchmarks/hallucination/synth.py`), generated and pre-registered in commit `13cdd34`
before any v3 change. Dev 492 claims, test 600 claims. The test split holds out names, every passage and claim
wording, two layouts and three document families. v3 was tuned on HB v0 (both splits) and HB-Synth dev only.
**The test split was scored once**, at commit `28d868a` (clean tree, recorded in the report), for all five
configurations. Raw rows: `hbsynth-test-{minilm,hashing}-2026-11-12.json`.

## Headline: held-out test (MiniLM embeddings), n = 356 unsupported, 244 supported

| | Errors caught | Correct sentences wrongly flagged | F1 |
|---|---|---|---|
| v1 (similarity only) | 30% (95% CI 26–35%) | 32% (26–38%) | 0.40 |
| v2 red | 71% (66–76%) | 30% (25–36%) | 0.74 |
| **v3 red (decides "not supported")** | **72% (67–76%)** | **11% (8–16%)** | **0.80** |
| v2 red + amber | 82% (77–85%) | 39% (33–46%) | 0.78 |
| v3 red + amber (everything the UI flags) | 84% (80–88%) | 18% (14–23%) | 0.86 |

**Acceptance (J_ROADMAP R6, pre-registered):** red-tier catch ≥ 68% — **met** (72%). False flags ≤ 10% — **not
met** (11%, interval 8–16%).

Offline hashing embedder (what the slim Render image runs), same test split:
- **v2 red:** catches 76%, wrongly flags 42%.
- **v3 red:** catches 75%, wrongly flags **31%**.
- **v3 red + amber:** catches 88%, wrongly flags 38%.

The relevance gate leans on embedding similarity, so it is much weaker with hashing. The deployed slim image
therefore flags far more correct sentences than the MiniLM numbers suggest.

Dev results (tuned, so optimistic): v3 red caught 76% with 0% false flags on HB-Synth dev (v2: 73% / 20%). The gap
between 0% on dev and 11% on test is the overfitting this protocol was designed to expose.

## By failure class (test, number flagged of n)

For correct sentences a lower count is better; for errors, higher.

| Class | n | v2 red | v3 red | v2 red + amber | v3 red + amber |
|---|---|---|---|---|---|
| correct: percentage computed from two figures | 16 | 15 | 7 | 15 | 8 |
| correct: % change | 4 | 4 | 0 | 4 | 0 |
| correct: count × rate | 4 | 4 | 0 | 4 | 0 |
| correct: total of figures | 12 | 5 | 4 | 5 | 4 |
| correct: difference (table in ₹ crore) | 4 | 4 | 4 | 4 | 4 |
| correct: ratio (“6 times the rent”) | 4 | 4 | 4 | 4 | 4 |
| correct: monthly → annual | 4 | 4 | 0 | 4 | 0 |
| correct: months ↔ years | 12 | 6 | 0 | 6 | 0 |
| correct: interval between dates | 16 | 2 | 0 | 2 | 0 |
| correct: table row (Withdrawals/Deposits) | 12 | 3 | 0 | 3 | 0 |
| correct: converse verb (rents from / leases to) | 16 | 1 | 0 | 4 | 4 |
| correct: “declined” = refused or decreased | 12 | 0 | 0 | 4 | 4 |
| correct: possessive name | 8 | 0 | 0 | 4 | 0 |
| correct: negation paraphrase | 8 | 0 | 0 | 4 | 4 |
| correct: paraphrase | 68 | 15 | 4 | 22 | 8 |
| correct: reformatted figures or dates | 44 | 7 | 4 | 7 | 4 |
| wrong number / date / entity / period / scale | 156 | 156 | 153 | 156 | 153 |
| wrong identifier | 8 | 8 | 8 | 8 | 8 |
| wrong interval | 8 | 7 | 7 | 7 | 7 |
| wrong computed percentage | 16 | 16 | 16 | 16 | 16 |
| wrong % change | 4 | 4 | 4 | 4 | 4 |
| wrong computed total | 12 | 12 | 12 | 12 | 12 |
| wrong ratio | 4 | 4 | 4 | 4 | 4 |
| direction against a table column | 8 | 1 | 8 | 4 | 8 |
| rose/fell against from → to figures | 4 | 4 | 4 | 4 | 4 |
| direction words | 16 | 0 | 0 | 8 | 8 |
| swapped parties, converse verb | 16 | 0 | 0 | 3 | 8 |
| swapped parties, other | 20 | 0 | 0 | 12 | 12 |
| negation flipped | 20 | 0 | 0 | 8 | 8 |
| “declined” turned into approved | 8 | 1 | 0 | 5 | 4 |
| contradiction in the source's own words | 8 | 0 | 0 | 0 | 4 |
| invented content | 48 | 40 | 40 | 40 | 40 |

## What the test revealed (not fixed: the test split has now been seen)

27 correct sentences were wrongly flagged red by v3, and 3 scale errors slipped through:

1. **Relevance gate (11 of 27).** "Deposits during the period added up to …" and "Eligible input tax credit was …"
   fail the coverage/similarity gate with held-out wording or layouts. With the hashing embedder this is the main
   source of the 31% false-flag rate.
2. **"Label: value" layouts lose their label (11).** In "Fair market value: Rs 6,00,00,000" the label sits before a
   colon, and the figure's label window starts after it. Shares ("25% below the fair market value"), ratios
   ("6 times the monthly rent") and some fund-flow percentages could not be matched to what the claim names.
3. **Tables in ₹ crore (5).** Figures in a table headed "(₹ crore)" are not scaled; this layout was test-only
   and was deliberately not implemented from dev.
4. **Percent-of does not check what the claim names (3 misses).** "The sanctioned amount is ₹6 lakh" (a lakh/crore
   slip) was explained as "1% of ₹6 crore", which happens to be the processing fee.
5. **Intervals ignore the claim's unit (1 miss).** "Roughly 35 months" matched an interval of 33.4 *weeks*.

Meaning errors (swapped parties, flipped negation) remain amber-only, as designed.

## Calibration (CB)

L2 logistic model of P(supported) from the verifier's output (red, amber, coverage, similarity, recomputed), fitted
on dev reports only (638 claims) and frozen in `benchmarks/calibration/model.json` before the test run.

| Held-out test (600) | Value | 95% CI (bootstrap over documents) |
|---|---|---|
| ECE (10 bins) | 0.096 | 0.077–0.115 |
| Adaptive ECE | 0.102 | 0.077–0.126 |
| Brier | 0.142 | 0.127–0.157 |

The model is **overconfident**: in its 0.8–0.9 bin, 74% of sentences are supported; in its lowest bin, 11.5% are
supported where it predicts 3.7%. The interval crosses the ECE ≤ 0.1 rule, and the set is synthetic with 59%
unsupported claims, far from the mix in real answers. **No probability is displayed.** The answer-level evidence
score stays a labelled, uncalibrated weighting. Report: `calibration-hbsynth-test-minilm-2026-11-12.json`.

## Caveats

- Same developer for templates and verifier. The developer read one test document per family during the label
  audit, before any v3 work. v3 changes were limited to dev evidence and the known v0 bug list, and some test
  phrasings were deliberately left unhandled (above). It is still not an independent test; an annotated split by
  two independent annotators (`README.md` guideline, `agreement.py`) remains an owner action.
- Generated text is regular. Real LLM answers mix claims and cite several passages.
- HB v0 numbers after R6 are not held out: v0 all 146, v3 red 74% caught / 4% false flags (v2 70% / 9%).

## Next steps (not done)

1. Fix items 1–5 above, then measure on a **fresh** held-out set: new seeds and templates, or, better, the
   independent annotated split.
2. Make the relevance gate amber, or embedder-aware, when only the hashing embedder is available. Measure this on
   dev first.
3. Recalibrate on labelled real answers before any probability is shown.

---

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
