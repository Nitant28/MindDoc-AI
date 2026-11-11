# StatementBench (v0) — datasheet

Measures bank-statement extraction and reconciliation (deliverable H §3, ADR-0011).

```bash
pip install -r requirements-dev.txt                       # reportlab (BSD), generator only
python -m benchmarks.statements.generator --out benchmarks/statements/data --dev 10 --test 10
python -m benchmarks.statements.run --split dev --extractors current engine --report
python -m benchmarks.statements.faults --split dev --n 300 --report   # v1: fault injection (no PDFs needed)
```

| Property | v0 |
|---|---|
| Source | fully synthetic, seeded (`--seed 2026`); generated data is not committed (reproducible) |
| Statements | 60: 40 dev (layout families A–D, 10 each), 20 test (E–F, held out) |
| Rows / pages | 3,839 rows / 94 pages (seed 2026) |
| Layout variation | separate debit/credit columns; single amount + Dr/Cr column; amount with (Dr)/(Cr); balance with Cr/Dr suffix (cash-credit / overdraft accounts); Indian vs western digit grouping; 5 date formats; wrapped narrations; value-date column on/off; header on every page vs first page only; opening / B/F / C/F rows |
| Transactions | UPI, NEFT, RTGS, IMPS, NACH, cheque, cash/ATM, interest, charges, reversals; exact paise |
| Ground truth | per row: date, value date, narration, reference, debit, credit, balance (paise), page; header facts |
| Not yet included | real scans, bounding boxes in gold, PDF-level fault injection (v1 injects at row level) |
| Licence | generated data: same as the repository; fictional banks, parties and identifiers |
| Known bias | layouts are generic and clean; real statements are messier — see tier SB-Real in H §3.1 |

**Split discipline.** Families E and F are never inspected during engine development. A test score is recorded once
per release with its commit hash.

## v1 — fault injection

`faults.py` injects one fault per synthetic history (one-edit amount, swapped direction, one-edit balance, dropped row, swapped same-day rows) and scores detection, localisation and hypothesis ranking, plus false alarms on the clean history. Splits are seed ranges: dev 10,000+, test 90,000+ (scored once per release).

## Scan — image-only variants (R4)

`scan.py` renders every StatementBench PDF to a grey image, degrades it with seeded scanner-like noise, and writes an
image-only PDF with the same page size; gold files are copied unchanged, so `run.py --data <scan dir>` scores the OCR
path with the same metrics. Two profiles, both chosen by the developer and **not calibrated against real scans**:
`mild` (200 dpi, ±0.3° rotation, slight blur, light noise, JPEG 70–90) and `rough` (150 dpi, ±1° rotation, more
blur and noise, JPEG 45–70). Same dev/test split as v0 (families A–D / E–F).

```bash
python -m benchmarks.statements.scan --profile mild --out benchmarks/statements/data_scan
python -m benchmarks.statements.run --data benchmarks/statements/data_scan --split dev --extractors engine --report --tag scan-mild
```

## Results
See `benchmarks/reports/STATEMENTBENCH.md`.
