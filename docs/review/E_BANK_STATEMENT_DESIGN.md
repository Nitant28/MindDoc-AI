# E — Bank-statement intelligence: parsing and deterministic reconciliation (design)

**Status: PLANNED** (milestones R3 and R4 in J). Implements proposed ADR-0010 (money), ADR-0011 (extraction
strategy) and ADR-0015 (Account Aggregator input). Data model: F §2.3. Benchmark: H §3 (StatementBench).

Tags: **[u]** marks an external fact still to be confirmed against `research/BANK_STATEMENT_RESEARCH.md` or a
primary source. Everything else is design.

## 1. Goal, scope and non-negotiables

**Goal.** Turn any Indian bank statement into a list of transactions where every value is:
- exact (integer paise)
- traceable to its page and bounding box
- arithmetically checked against the statement's own running balances

When the arithmetic fails, show the reviewer exactly where and why.

**Inputs**, in order of priority:
1. Text-layer PDF e-statements.
2. Net-banking CSV/XLSX exports.
3. Account Aggregator (AA) JSON (deposit accounts).
4. Scanned PDFs or photos of statements and passbooks (R4).

Password-protected PDFs are opened with a password the user types for that upload. The password is never stored or
logged.

**Non-negotiables**
1. **Never modify an extracted value to make a balance reconcile.** Suggested corrections are shown as suggestions.
   Only a reviewer's action creates a corrected version (F §2.3, `supersedes_id` plus a review event).
2. **Numbers are integers in paise** from the moment they're parsed (ADR-0010). Each one keeps its raw text.
3. **Deterministic.** The same file and the same extractor version give the same rows, IDs and check results.
4. **No LLM produces or edits an amount, date or balance.** An LLM may at most suggest which column is which on an
   unknown layout, and only if the user enabled an LLM. Its suggestion is still checked by the balance arithmetic.
5. **Findings are not fraud verdicts.** Anomalies are leads for a professional's judgement.

## 2. Pipeline

```
S0 detect & classify ─> S1 words+boxes ─> S2 columns ─> S3 rows ─> S4 fields ─> S5 reconcile ─> S6 review items
                                                                                         └──> S7 claims/entities (R5)
AA JSON / CSV ───────────────────────────── (mapping) ─────────────> S4' fields ─> S5 ...
```

### S0 — Detect and classify
- **Is this a statement?** Score the page text for statement cues: header words (date, narration/particulars,
  withdrawal/debit, deposit/credit, balance), an account-number pattern, an IFSC, and "statement of account" or
  period phrases.
- Extract the **header block**: bank name, branch, IFSC, account number (stored masked plus a keyed hash), holder
  name, account type, period, opening and closing balance if printed.
- **Layout signature:** a hash of normalised header tokens plus column count. It's used to reuse a column map a
  reviewer previously confirmed (§4), never to pick a hand-written template.

### S1 — Words with boxes
- **Text-layer PDF:** words and character boxes from pdfplumber/pdfminer (MIT) [u] or pypdfium2 (Apache-2.0/BSD)
  [u]. Coordinates are normalised to 0–1.
- **Scans (R4):** OpenCV preprocessing (existing `cv.py`) → OCR word boxes with per-word confidence. Two engines:
  - **Tesseract** (TSV output).
  - **RapidOCR** (Apache-2.0 **[verified]**), which runs PP-OCR models on ONNX Runtime with **no torch or
    PaddlePaddle dependency** (`research/BANK_STATEMENT_RESEARCH.md`). It fits the slim profile.

  The engine is chosen by StatementBench. Heavier OCR (PaddleOCR-VL, Docling) stays in the ML profile.
- Output: `Word(text, bbox, page, line_id, confidence)`.

### S2 — Column model (layout-generic, no bank regex)
1. **Header candidates:** lines whose words match a **header lexicon**. The lexicon is a data file, not code: date,
   txn date, value date, narration, particulars, description, remarks, chq/ref no, withdrawal (dr), debit, deposit
   (cr), credit, amount, balance, plus Hindi/bilingual variants as found.
2. **Column intervals:** from the header word x-ranges, refined by **alignment of numeric tokens**. Amounts are
   right-aligned, so their right edges cluster. Use 1-D clustering of right edges across all candidate rows.
3. **Column roles:** `date | value_date | narration | ref | debit | credit | amount(+Dr/Cr) | balance(+Cr/Dr)`,
   assigned from header labels, then checked against data:
   - date columns parse as dates in ≥ 90% of rows
   - amount columns parse as amounts
   - the balance column is the one whose successive differences explain the other amount column(s)
4. **Pages without a header** inherit the previous page's column model, with a drift tolerance. Large drift triggers
   re-detection from numeric alignment.
5. **Ambiguity** (two plausible role assignments): keep both and let S5 choose the one under which the balances
   reconcile. Record `column_model_source = {header|alignment|balance_arbitration|reviewer_profile}`.

### S3 — Row segmentation
- A **transaction row starts** at a line with a parsable date in the date column. Following lines without a date but
  with narration text are **continuations** (wrapped narration), attached to the open row.
- **Special rows** are classified by keywords plus geometry: opening balance, balance brought/carried forward, page
  totals, statement summary boxes, "closing balance". They're used by S5, not counted as transactions.
- **Repeated page headers and footers** are removed by matching them against the detected header and by vertical
  position.

### S4 — Field parsing (deterministic)

| Field | Rules |
|---|---|
| Dates | `dd/mm/yyyy`, `dd-mm-yy`, `dd MMM yyyy`, `dd-MMM-yy`, ISO. Day-first by default (Indian convention). Two-digit years resolved within the statement period |
| Amounts | Indian grouping (`1,23,456.78`), western grouping, trailing `Cr`/`Dr`, `CR`/`DR`, parentheses or minus. Converted with `Decimal` → paise. `amount_raw` kept |
| Direction | separate debit/credit columns → `column`. One amount column with a Dr/Cr marker → `suffix`. Neither → computed from the balance delta in S5 → `inferred_from_balance`, always flagged |
| Balance | signed: `Cr`/no suffix positive, `Dr` negative for overdraft, cash-credit and OD accounts. `balance_side` stored |
| Narration | raw text kept. Normalised mode: UPI, NEFT, RTGS, IMPS, NACH/ECS, CHQ, CASH, ATM, CARD, INT (interest), CHG (charges), REV (reversal/return), SWEEP, OTHER — from a keyword table (data file) |
| References | UTR/RRN/UPI reference, cheque number, UPI VPA, IFSC of counterparty if present. Format checks per §6; invalid → kept as text, not used for identity |
| Counterparty | the text segment after mode markers, cleaned. Becomes an entity *candidate* (R5), never a resolved entity at this stage |

### S5 — Reconciliation engine (the core)

**Notation.** For rows $i = 1..n$ in printed order: credit $c_i \ge 0$, debit $d_i \ge 0$ (paise), observed balance
$b_i$ (signed, possibly missing), opening $B_0$.

**Checks.** Each produces a `reconciliation_check` row with expected, observed, difference, status, reason code,
affected rows, page and bbox.

| Check | Rule |
|---|---|
| **Row** | $e_i = b_{i-1} + c_i - d_i$; pass iff $e_i = b_i$ exactly. If $b_{i-1}$ is missing, use the last observed balance and the sum of the intervening rows (**segment check**) |
| **Opening** | $B_0$ from the header, or a "brought forward / opening" row. If absent, derive $b_1 - c_1 + d_1$ and mark it `derived`: unverifiable, not a pass |
| **Page continuity** | carried-forward balance on page *p* = brought-forward balance on page *p + 1* = last row balance of page *p* |
| **Statement** | $B_0 + \sum c_i - \sum d_i = $ closing balance (header) $= b_n$ |
| **Printed totals** | summary-box totals (debit, credit, count) = computed totals |
| **Cross-statement** | for the same account (account hash + IFSC): closing of period *k* = opening of period *k + 1*. A gap in dates means a missing period |

Exact integer equality: no tolerance. The paisa rounding of interest calculations is the bank's; we only check that
the printed numbers are consistent with each other.

**Diagnosis when a check fails.** Ranked hypotheses, shown to the reviewer. Values are never changed.

| Reason code | Test (deterministic) | Shown to reviewer |
|---|---|---|
| `direction_suspect` | $b_{i-1} - c_i + d_i$ (direction swapped) equals $b_i$ | "Row reconciles if this is a debit, not a credit" |
| `amount_ocr_suspect` | the implied amount $\hat{a} = \lvert b_i - b_{i-1} \rvert$ differs from the extracted amount by one digit substitution, transposition, dropped/added digit, or a misplaced decimal point | extracted vs implied amount, with the digit difference highlighted, plus OCR confidence of that word |
| `balance_ocr_suspect` | row *i* fails but row *i + 1* passes when computed from $e_i$ instead of $b_i$ | the observed vs implied balance |
| `missing_row_suspect` | a constant offset Δ persists from row *i* onward (later rows reconcile among themselves) | "A transaction of net Δ appears to be missing between rows *i − 1* and *i*" |
| `merged_rows_suspect` | the row's amount equals the sum of two plausible amounts and the narration contains two mode markers | the split suggestion |
| `order_ambiguous` | rows fail in printed order but a reordering **within the same date** reconciles | the reconciling order, flagged; printed order is kept |
| `reversal_pair` (not a failure) | a debit and a later credit of the same amount with REV/RTN/return markers, or matching references | linked pair; excluded from net fund-flow totals in R7 |
| `unreconcilable_no_balance` | the statement prints no running balances | statement status `not_checkable`; extraction confidence alone governs |

**Statement status**

| Status | Meaning |
|---|---|
| `reconciled` | all checks pass |
| `reconciled_with_flags` | passes, but some direction values are `inferred` or the opening is `derived` |
| `needs_review` | one or more checks failed |
| `not_checkable` | no balances printed |
| `failed` | parsing error |

**Findings built on transactions inherit this status.** A finding that uses a row from a `needs_review` statement is
held back (J R7/R8).

### S6 — Review items
- Each failing check or low-confidence field becomes a `review_queue` item. The item shows:
  - the original extracted values
  - expected vs observed balance and the difference
  - the affected row(s)
  - the page image with the row and cell boxes highlighted
  - OCR confidence
  - the ranked hypotheses
- **Reviewer actions:**
  - accept a suggestion → a new transaction version is created
  - edit a value → new version, with a mandatory reason
  - mark "bank error / genuine inconsistency" → kept as is, and it becomes evidence
  - dismiss
- Every action is a `review_event`, and the checks re-run. A reviewer-confirmed column map can be saved for the
  `layout_signature` (§4).

### S7 — Hand-off to claims and entities (R5)
Each reconciled transaction can produce a `TRANSFERRED_TO` / `RECEIVED_FROM` claim, with evidence pointing at the
row's regions. Counterparty text and identifiers become entity candidates for Splink (ADR-0009).

## 3. Other inputs mapped to the same model

- **Account Aggregator JSON.** The ReBIT deposit FI schema
  ([spec](https://specifications.rebit.org.in/api_schema/account_aggregator/documentation/deposit.html), read
  2026-11-10) **[verified]** defines:
  - **Transaction:** `type` (CREDIT | DEBIT), `mode` (CASH | ATM | CARD | UPI | FT | OTHERS), `amount`,
    `currentBalance`, `transactionTimestamp`, `valueDate`, `txnId`, `narration`, `reference`.
  - **Transactions:** `startDate`, `endDate`.
  - **Summary:** `currentBalance`, `currency`, `balanceDateTime`, `type` (SAVINGS | CURRENT), `facility` (OD | CC),
    `currentODLimit`, `drawingLimit`, `ifscCode`, `micrCode`, `branch`, `openingDate`, `status`.

  Major version 2.0.0 of the deposit schema was announced on 2025-01-23
  ([Sahamati](https://sahamati.org.in/?p=2603)) **[unverified: secondary]**. Pin the version per FIP payload.
  `mode` is coarse (FT covers NEFT, RTGS and IMPS), so MindDoc's finer mode still comes from the narration.

  These fields map 1:1 onto `statement` and `statement_txn` with `direction_source=column` and no bounding boxes.
  Provenance is the AA consent artefact and the FI-data hash. S5 runs unchanged. AA data with balances should
  reconcile exactly, and a failure there is itself a notable finding. *Implication (D):* where lenders already get
  AA data, MindDoc adds value by checking, linking and analysing it, not by OCR.
- **CSV/XLSX exports.** Header-row detection plus the same lexicon gives the column roles. The reviewer confirms the
  mapping once per layout signature. Then S4–S5 run.

## 4. Supporting many banks without fragile regex

1. **Generic geometry plus a lexicon** handles the common case. The lexicon and mode keywords are versioned data
   files, extended by adding entries, not code.
2. **The balance constraint is the arbiter.** Among competing interpretations (column roles, direction,
   continuation vs new row), choose the one under which the statement reconciles. Record that the choice was made by
   arbitration.
3. **Reviewer-confirmed layout profiles.** After a reviewer fixes a column map, it's stored against the layout
   signature and reused for that layout. These are data-driven templates, learned from reviews and auditable, not
   hand-written regex.
4. **Template code only as a last resort**, for a layout that defeats (1)–(3). It must be justified by a
   StatementBench failure and covered by a test.

## 5. Approaches compared (decision for ADR-0011)

| Approach | Accuracy evidence | CPU cost | Explainable | Licence | Maintenance | Main failure mode |
|---|---|---|---|---|---|---|
| Bank-specific templates/regex | high on known layouts, zero on new ones (to measure on SB held-out layouts) | very low | yes | own code | **high**: breaks on every format change | new or changed layouts |
| **Layout-generic geometry + balance arbitration** (recommended) | to measure on SB; the balance check bounds silent errors | low | **yes**: every decision has a reason | own code + pdfplumber/pypdfium2 [u] | low: data files | wrapped narrations; headerless pages (mitigated in S2/S3) |
| Table-recognition models (Docling TableFormer, PP-Structure, img2table) [u] | published TEDS on general tables, not on statements | medium–high; torch or Paddle for some [u] | partial | to check per component [u] | external | borderless statement tables; merged cells |
| LLM/VLM structured extraction | not measured for paise-exact amounts; hallucination risk | high (API) or GPU | no | provider terms; data egress | prompt drift | invented or altered numbers: unacceptable for amounts |
| Hybrid: generic first, then table model on scans, LLM only for header-role hints | best expected | medium | yes, with the arbitration record | as above | medium | complexity |

**Decision proposed:** the generic + arbitration path is the default (slim profile). Table models are optional for
scans after they win on StatementBench (ML profile). LLMs never touch amounts.

**Published evidence (the only comparison found).** AI-BAAM ([arXiv 2510.16066](https://arxiv.org/abs/2510.16066))
**[verified: paper exists; figures as reported by the research note]** compared approaches on six *known* Malaysian
bank formats:
- **Accuracy:** template extraction scored 97.80% exact-match normalised edit distance; the best LLM pipeline scored
  94.23%.
- **Speed:** templates took about 0.11 s per document; end-to-end VLMs took 104–150 s.

It doesn't test unseen layouts, which is exactly what StatementBench's held-out layout families measure.

**No paper or tool was found that uses running balances to locate extraction errors.** The diagnosis in S5 is
MindDoc's own design, and a candidate contribution (H, I).

**Component facts** (`research/BANK_STATEMENT_RESEARCH.md`):
- Docling's models need torch (via `docling-ibm-models`).
- Camelot 2.0 is MIT (torch only in an optional extra).
- img2table and RapidTable (SLANet+) are torch-free.
- PaddleOCR-VL weights are Apache-2.0.
- OCRmyPDF is MPL-2.0 but depends on Ghostscript, which is AGPL **[u]**, so it's kept out of the shipped image.
- Surya/Marker weights are revenue-restricted or non-commercial, so they're excluded.

## 6. Identifier rules (validation before use)

| Identifier | Rule (sources checked 2026-11-10; official specs still to cite before implementation) | Use |
|---|---|---|
| IFSC | 11 characters: 4 letters (bank), `0` (reserved), 6 alphanumerics (branch; usually digits), e.g. `SBIN0001707` ([Wikipedia](https://en.wikipedia.org/wiki/Indian_Financial_System_Code), [Razorpay](https://razorpay.com/blog/decoding-ifsc-codes)) **[verified: secondary sources agree]**. Validate the format, then look it up in RBI's published IFSC list | counterparty bank and branch; account identity together with the account number |
| PAN | 10 characters: 5 letters, 4 digits, 1 letter; 4th letter encodes the holder type **[u]** | strong identifier (ADR-0009) |
| GSTIN | 15 characters: state code (01–37) + PAN (10) + entity number (1–9, A–Z) + `Z` + check character ([TaxGuru](https://taxguru.in/goods-and-service-tax/gstin-goods-and-service-tax-identification-number-structure.html)) **[verified: layout]**. Secondary sources **disagree on the check-character algorithm** (mod-36 vs "Luhn"): implement only from the GSTN specification, with official test vectors | strong identifier, after the check character is verified |
| CIN / DIN | CIN is 21 characters (listing status, industry code, state, year, ownership, registration number); DIN is 8 digits | company and director identity |
| UTR / RRN / UPI reference | formats differ for NEFT, RTGS, IMPS and UPI | link payer and payee rows across accounts (round-trip detection, R7) |
| UPI VPA | `handle@psp` | counterparty identity candidate |

Invalid identifiers are never used for merges and are shown as text.

## 7. What the reviewer sees (UI, R3)
- **Transactions** tab per statement: a table with the date, narration, mode, debit, credit and balance columns,
  plus a check status per row.
- Clicking a row opens the page with the row box highlighted.
- **Reconciliation summary:** opening, total credits, total debits, closing, computed vs printed, and a status badge.
- **Review queue:** the failing checks, ordered by impact (the amount at stake).
- A "suggested correction" never displays as the value: it's always shown beside the original, in a different style.

## 8. Measurement and acceptance
- StatementBench (H §3): row F1, field accuracy, direction accuracy, reconciliation rate, **error localisation**,
  **false alarms** (must be 0 on correctly extracted statements), review load and throughput, per layout family,
  slim vs ML profile.
- Acceptance is in J (R3 text-layer, R4 scans).

## 9. Risks

| Risk | Mitigation |
|---|---|
| Synthetic layouts don't represent real banks | held-out layout families; the SB-Real tier with partners (D's pilot); reviewer profiles |
| Statements without running balances | `not_checkable` status; rely on totals and cross-statement continuity; extra review |
| Same-day ordering differences between banks | the `order_ambiguous` diagnosis rather than silent reordering |
| OCR on poor scans | confidence-aware flags; reconciliation bounds the impact; "needs review" rather than guessing |
| Scope creep into credit scoring | out of scope: MindDoc produces evidence for reviewers, not scores |
