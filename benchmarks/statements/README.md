# StatementBench (v0) — datasheet

Measures bank-statement extraction and reconciliation (deliverable H §3, ADR-0011).

```bash
pip install -r requirements-dev.txt                       # reportlab (BSD), generator only
python -m benchmarks.statements.generator --out benchmarks/statements/data --dev 10 --test 10
python -m benchmarks.statements.run --split dev --extractors current engine --report
```

| Property | v0 |
|---|---|
| Source | fully synthetic, seeded (`--seed 2026`); generated data is not committed (reproducible) |
| Statements | 60: 40 dev (layout families A–D, 10 each), 20 test (E–F, held out) |
| Rows / pages | 3,839 rows / 94 pages (seed 2026) |
| Layout variation | separate debit/credit columns; single amount + Dr/Cr column; amount with (Dr)/(Cr); balance with Cr/Dr suffix (cash-credit / overdraft accounts); Indian vs western digit grouping; 5 date formats; wrapped narrations; value-date column on/off; header on every page vs first page only; opening / B/F / C/F rows |
| Transactions | UPI, NEFT, RTGS, IMPS, NACH, cheque, cash/ATM, interest, charges, reversals; exact paise |
| Ground truth | per row: date, value date, narration, reference, debit, credit, balance (paise), page; header facts |
| Not yet included | scanned/degraded variants (R4), bounding boxes in gold, missing/duplicate/broken-row injections (R3 error-localisation set) |
| Licence | generated data: same as the repository; fictional banks, parties and identifiers |
| Known bias | layouts are generic and clean; real statements are messier — see tier SB-Real in H §3.1 |

**Split discipline.** Families E and F are never inspected during engine development. A test score is recorded once
per release with its commit hash.

## Results
See `benchmarks/reports/STATEMENTBENCH.md`.
