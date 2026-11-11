# StatementBench results

| Date | Code | Split | Extractor | Row F1 | Row recall (95% CI) | Balance acc. | Statement exact | Reconciled | s/page |
|---|---|---|---|---|---|---|---|---|---|
| 2026-11-10 | 2.1.0 pipeline (`ee814b0`) | dev (40 stmts, 2,602 rows) | `current` | 0.000 | 0.000 (0.000–0.001) | — | 0.000 | 0.000 | 0.55 |
| 2026-11-11 | R3 engine v1 | dev (40 stmts, 2,602 rows) | `engine` | **1.000** | 1.000 (0.999–1.000) | 1.000 | **1.000** | 1.000 | 0.51 |
| 2026-11-11 | R3 engine v1 (frozen; scored once) | **held-out test** (20 stmts, 1,237 rows, families E–F) | `engine` | **1.000** | 1.000 (0.997–1.000) | 1.000 | **1.000** | 1.000 | 0.51 |

## What these numbers do and do not show

**They show** that on clean, digitally generated statements the layout-generic extractor recovers every
transaction exactly — dates, paise amounts, direction, signed balances (including overdraft `Dr` balances), wrapped
narrations — across six column arrangements, Indian and western digit grouping, five date formats, separate
debit/credit columns, single amount + Dr/Cr column, `(Dr)/(Cr)` amount suffixes, header-on-first-page-only
continuation pages and brought/carried-forward rows, and that every extracted statement reconciles.

**They do not show** real-world accuracy:
1. **Same author.** The generator, its held-out layouts (E–F) and the engine's header lexicon were written by the same
   developer; the lexicon contains generic synonyms ("posting date", "running balance", "remarks", "amount (INR)") that
   E–F use. The test split measures generalisation of the geometry and row segmentation, not lexicon coverage of
   unseen banks.
2. **Synthetic and clean.** No real bank statement has been processed. Real statements add merged cells, multi-column
   narrations, headers split across lines, rotated/scanned pages, logos and watermarks.
3. **Faults are measured separately** (StatementBench v1, below) and only at the row level, so the extractor's own
   error rate on real statements is still unknown.
4. **Text-layer PDFs only.** Scanned statements (OCR word boxes) are R4.

## StatementBench v1 — fault injection (reconciliation and diagnosis)

`python -m benchmarks.statements.faults --split {dev,test} --n 300 --report`. One fault per statement is injected at
the row level into 300 synthetic histories per split (20–60 rows; 30% overdraft accounts). Each history also runs
clean, to measure false alarms. Code was developed on `dev` (seeds 10,000+). `test` (seeds 90,000+) was scored once
with frozen code.

**Metrics.** *Detect* means the statement gets ≥1 failing check. *Locate* means the first failing row check is the
faulty row (or, for a dropped row, the row after the gap). *Diag* means the correct hypothesis is in that check's
list. *Top-1* means it is ranked first.

| Split | Fault | n | Detect | Locate | Diag | Top-1 (text prior) | Top-1 (OCR prior) |
|---|---|---|---|---|---|---|---|
| test | clean statement (false alarm) | 300 | **0.000** false-alarm rate (0.000–0.013) | — | — | — | — |
| test | amount misread by one edit | 300 | 1.000 | 1.000 | 0.993 | 0.000 | 0.993 |
| test | debit/credit direction swapped | 300 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| test | balance misread by one edit | 300 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| test | row dropped | 300 | 1.000 | 1.000 | 1.000 | 0.997 | 0.917 |
| test | adjacent same-day rows swapped | 300 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

Dev results show the same pattern (`statementbench-faults-dev-2026-11-11.json`). Amount Diag is 0.997 on dev.
Dropped-row top-1 is 0.883 on dev under the OCR prior and 1.000 under the text prior. Everything else matches exactly.

**Knock-on failures.** A misread balance also breaks the next row. A same-date swap also breaks the other swapped
row and the row after the block. These knock-on failures are now labelled `follows_previous_error` and point back to
the root row. Held-out test: **300/300** labelled for misread balances, **569/569** for same-day swaps.

**Test-split history.** The test split was scored twice, both times with frozen code and with no tuning on its
results.
1. After the ranking and reorder-search changes.
2. After the knock-on labelling was added. This change came from a manual check in the browser, not from test
   results.

The second change cannot alter detection, localisation or the target row's hypotheses. The second test run
reproduced every earlier test number exactly.

**What changed during development (dev only).** In the first dev run, a misread balance was ranked first in 0.76 of
cases, a dropped row in 0.86 and a same-day swap in 0.82. Same-day swaps were missed entirely in 0.09 of cases,
because blocks of more than four same-date rows were never searched. Two fixes followed:
- Hypotheses that other rows corroborate are now ranked first: a misread balance (the next row reconciles from the
  expected value) and a same-date reordering (the whole block and the row after it reconcile).
- The reorder search now covers same-date blocks of up to 12 rows.

**An ambiguity that cannot be removed.** A one-edit amount misread and a missing transaction of the offset amount
produce *identical* balances. Both hypotheses are always listed (Diag ≈ 1.0); only their order depends on the source
prior. A PDF text layer carries exact characters, so a missing or merged row is the likelier cause there (the engine
uses this prior today). OCR misreads digits, so R4 will use the OCR prior. The top-1 columns show this
trade-off rather than hide it. Neither number measures how often each failure actually happens on real statements.
The residual 0.007 amount miss comes from dropping a leading digit, which needs two edits to undo.

**Not covered.** Two faults in one statement, merged rows, a wrong opening balance, and faults in statements without
running balances (always `not_checkable`).

Next measurement that would change confidence: SB-Real (20–50 redacted real statements under a data-processing
agreement, labelled independently) and the public `AgamiAI/Indian-Bank-Statements` set (Apache-2.0).

Raw: `statementbench-{dev,test}-2026-11-1x.json`. Throughput measured on a laptop CPU (Windows, Python 3.11), single
process; the earlier 218 s/page figure from an interrupted run (machine asleep) was discarded.
