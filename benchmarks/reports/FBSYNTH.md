# FB-Synth v0: discovery detectors (R7)

Benchmark, splits, metrics and acceptance were pre-registered in `benchmarks/discovery/README.md` (commit `4c69d8f`).
The untuned detectors were committed next (`fbd3ab0`), then tuned on the dev split only (`85eece8`). The test split
was scored **once**, from a clean tree at `85eece8`, on 2026-11-14.

## Results

| Split | Cases | Scheme recall (95% CI) | False flags per 10 benign look-alikes | Background false flags per 1,000 txns | Evidence completeness |
|---|---|---|---|---|---|
| dev, untuned (r7.0) | 40 | 0.974 (0.949–0.987) | 2.34 | 15.1 | 0.960 |
| dev, tuned (r7.1) | 40 | 0.983 (0.962–0.993) | 1.09 | 5.1 | 0.962 |
| **test (r7.1, once)** | 40 | **0.976 (0.952–0.988)** | **1.38** (share flagged 10.4–18.0%) | **4.8** | **0.972** |

**Acceptance:**
- Scheme recall ≥ 0.9: **met.**
- At most 1 false flag per 10 benign look-alikes: **not met** (1.38).

## Test split, per family

| Scheme | Found |
|---|---|
| end_use | 48 / 55 |
| round_trip, two transfers with 3–10% fees (variant not in dev) | 40 / 40 |
| round_trip, three transfers | 40 / 40 |
| structuring, clustered below ₹50,000 | 27 / 27 |
| structuring, same-day splits | 13 / 13 |
| pass_through | 40 / 40 |
| duplicate_payment | 40 / 40 |
| window_dressing | 40 / 40 |

| Benign look-alike | Flagged |
|---|---|
| trading at a margin | 22 / 40 |
| disbursement spent on suppliers | 13 / 40 |
| refund | 3 / 40 |
| daily cash takings | 3 / 40 |
| quarter-end collection | 2 / 40 |
| loan repaid after two months | 1 / 40 |
| sweep to a fixed deposit | 0 / 40 |
| two invoices of the same amount | 0 / 40 |

## Where the false flags come from
- **Two-transfer round trips with busy trading partners.** In this generator every firm is both customer and
  supplier of the borrower, with a dozen transfers each way. Money out, then 90–100% back from the same firm within
  15 days, happens by chance. The trading look-alike is flagged through those coincidences, not through its own
  margin trades.
  - Tried on dev: allowing only the first transfer back from that party to close the loop. It cut dev false flags to
    0.88 but lost 12 of 40 planted round trips, so it was not adopted.
  - Real customer and supplier sets overlap less, so this is probably pessimistic, but that has not been measured.
- **Disbursements whose windows overlap.** The benign disbursement is placed independently of the planted one. When
  payments to the group follow both disbursements, they are counted against the later one. That flags the benign
  disbursement and misses the planted one (7 of the 55 misses). The data alone cannot separate these cases; a
  reviewer has to read the sanction terms.

## Limits
- Same author as the detectors; synthetic transactions only (no PDFs, no extraction or resolution errors).
- D3 (undisclosed related parties), D4 (turnover against GST and books), D5 (invoice integrity) and D7
  (document-integrity cues) are not built, because the product does not read those documents yet.
- Thresholds are parameters stored with every run.
  - ₹10 lakh (cash-transaction reports, PML Rules rule 3) is from FIU-IND and RBI material.
  - ₹50,000 (Income-tax Rule 114B) is from secondary summaries only.
  - Verify both against the current rules.
