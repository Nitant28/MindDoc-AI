# FB-Synth v0: discovery benchmark (R7)

Seeded borrower-group cases for the deterministic detectors in `app/discovery/detectors.py`
(`benchmarks/discovery/synth.py`). This README pre-registers the metrics and acceptance criteria. It was committed
before any detector parameter was tuned.

## What is in a case
- Three accounts in the case: the borrower's, a group company's and an intermediary's (all three holders count as
  "group"), plus one person the analyst has tagged as related.
- Background activity: 90–130 customer receipts and supplier payments, monthly salaries, a monthly EMI, charges and
  the group company's own trade.
- **Schemes** (should be reported):
  - `end_use`: a loan disbursement, then 28–90% of it paid to the group company or the related person within 20–27 days;
  - `round_trip`: out to an outside party and back within 2–12 days (on test, 3–10% fees kept back), and a 3-transfer
    loop through the group company and the intermediary;
  - `structuring`: 4–8 cash deposits just below ₹50,000 within 20 days, or the same day split on 2–4 days;
  - `pass_through`: 3–6 credits paid on to someone else within 0–2 days at 98.5–100% of the amount;
  - `duplicate_payment`: the same amount to the same supplier 1–6 days apart;
  - `window_dressing`: a large credit in the last 4 days of a quarter, 92–100% of it paid back 2–12 days after.
- **Benign look-alikes** (should not be reported):
  - a disbursement spent on unrelated suppliers;
  - a sweep to a fixed deposit and back;
  - a supplier refund (the narration says "REFUND");
  - a loan given and repaid 45–75 days later;
  - daily retail cash takings of ₹5,000–₹60,000;
  - trading at an 8–18% margin;
  - two invoices of the same amount 15–28 days apart;
  - a quarter-end collection followed by a smaller purchase.

## Splits
- `dev`: seeds 0–39. Used for tuning.
- `test`: seeds 5000–5039. Held out, with different names, a later period and the variants marked above (fees on
  round trips; structuring nearer the threshold; smaller diverted shares; slightly longer lags).

## Metrics (pre-registered)
- **Scheme recall:** share of planted schemes found by their detector, where found means a lead citing at least half
  of the scheme's transactions. Reported with a Wilson 95% interval and per family.
- **False flags per 10 benign look-alikes:** a look-alike is flagged if any lead from any detector cites any of its
  transactions.
- **Background false flags per 1,000 background transactions:** leads that cite only background transactions.
- **Evidence completeness:** the mean share of a found scheme's transactions that the lead cites.

## Acceptance (J_ROADMAP R7)
On the test split, scored once from a committed tree (`--final`):
- scheme recall ≥ 0.9;
- at most 1 false flag per 10 benign look-alikes.

The runner refuses to score the test split without `--final`, or with uncommitted detector or benchmark code.

## Limits
- Same author as the detectors, so not independent.
- Synthetic transactions only: no PDFs, no extraction errors, clean party resolution.
- Detectors that need documents the product does not read yet (GST returns, invoices, sanction terms, registry data)
  are not covered: D3 to D5 and D7.
