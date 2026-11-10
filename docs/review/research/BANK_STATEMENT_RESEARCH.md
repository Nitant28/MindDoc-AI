# Bank-Statement Engine: Research for Deliverables E and H

*Research date: 2026-11-10. Scope: Indian bank statements (PDF text-layer and scanned), transaction extraction, normalisation and deterministic running-balance reconciliation. Companion to [TECHNOLOGY_EVALUATION.md §4](../../research/TECHNOLOGY_EVALUATION.md) and [BENCHMARK_DATASETS.md](../../research/BENCHMARK_DATASETS.md). Items already verified there are referenced, not repeated.*

**Tags.** **[verified]** means a primary page, repository file, or registry API response was read during this research. **[unverified]** means only a secondary source, a search excerpt, or an unreachable page was seen. "Not found" means a search ran and found nothing usable.

**Privacy rule followed.** No real statement was downloaded, opened or stored. Where search results surfaced real statements posted publicly (court filings, document-sharing sites), only the column-header text visible in the search snippet was noted. Those links are left out on purpose.

> Not legal advice. Licence notes describe published terms only.

---

## 0. Summary

- **Best evidence on approach.** The only published head-to-head on bank statements found is AI-BAAM. On six known Malaysian bank formats, **template matching beat every OCR + LLM and VLM pipeline**: 97.80% exact NED against 94.23% for the best LLM pipeline. It ran in about 0.11 s per document against 104–150 s for end-to-end VLMs ([arXiv 2510.16066](https://arxiv.org/html/2510.16066v4)) **[verified]**. That paper did **not** use balance reconciliation.
- **Recommendation.** Build a **layout-aware, rule-based extractor on word boxes**, with declarative per-layout profiles (not per-bank code), and a **Decimal reconciliation engine** that checks every row and localises errors. ML table models and LLMs are optional helpers, never the source of amounts.
- **Torch and Paddle findings that change ADR-0006.**
  1. Docling's layout and TableFormer models **need PyTorch**. `docling-ibm-models` lists `torch` and `torchvision` as hard dependencies. So Docling's model pipeline cannot sit on the slim (no-torch) path.
  2. PaddleOCR needs the PaddlePaddle framework. **RapidOCR** (Apache-2.0) runs the same PP-OCR models on ONNX Runtime, and its `requirements.txt` lists no torch or paddle. It should be the slim-path OCR engine.
  3. OCRmyPDF is **MPL-2.0** (not AGPL), but it needs Ghostscript as an external program. Keep it out of the shipped image.
  4. Camelot 2.0 is MIT and pypdfium2-based. Torch appears only in its optional `ml` extra.
- **Account Aggregator schema.** The ReBIT Deposit FI schema is at [specifications.rebit.org.in/…/deposit.html](https://specifications.rebit.org.in/api_schema/account_aggregator/documentation/deposit.html) **[verified]**. Adopt its field names as the canonical core, plus MindDoc extensions for provenance and raw values.
- **Datasets.** No public, real, annotated Indian statement set was found. Usable sets:
  - [AgamiAI/Indian-Bank-Statements](https://huggingface.co/datasets/AgamiAI/Indian-Bank-Statements): synthetic, Apache-2.0, current accounts only.
  - [Bankstatemently benchmark](https://github.com/bankstatemently/bank-statement-parsing-benchmark): MIT. Only 5 statements are released, and the Indian one is "coming soon".
  - [SynFinTabs](https://huggingface.co/datasets/ethanbradley/synfintabs): MIT, synthetic financial tables.

---

## 1. How Indian bank statements vary

### 1.1 What is confirmed

| Feature | Evidence | Tag |
|---|---|---|
| HDFC header row: `Date · Narration · Chq./Ref.No. · Value Dt · Withdrawal Amt. · Deposit Amt. · Closing Balance` | The same header appears in many publicly posted statements in search snippets (links withheld) | [verified, snippet text only] |
| Axis header row: `Tran Date · Chq No · Particulars · Debit · Credit · Balance · Init. Br` | One snippet of a document-sharing upload (link withheld) | [unverified] |
| SBI has at least three layouts: YONO app, OnlineSBI net banking, branch-printed | [Terra Insight](https://www.terra-insight.com/insights/bank-statement-column-variant-parsing) | [unverified, secondary] |
| HDFC has separate net-banking, corporate-portal and legacy formats | same source | [unverified] |
| Older Finacle deployments print `Txn Date`, newer ones print `Transaction Date` | [Terra Insight](https://www.terra-insight.com/insights/bank-statement-column-variant-parsing) | [unverified] |
| After the 2019–20 PSU mergers, migrated accounts kept legacy formats next to the acquirer's format | same source | [unverified] |
| A trailing Dr/Cr indicator after the balance (OD accounts), and some banks with one `Amount` column plus a +/- or Dr/Cr indicator | same source; also the synthetic AgamiAI "Type 2" layout | [unverified] / [verified as dataset content] |
| RBI requires "brief, intelligible particulars" and warns against bare "by clearing" or "by cheque" entries and undecipherable codes. MICR and IFSC must be printed on passbooks and statements. | [RBI Master Circular on Customer Service, 1 Jul 2015, §5.6.3 and §5.6.7](https://rbi.org.in/commonman/English/Scripts/Notification.aspx?Id=1587) | [verified] |
| Overdraft (OD) and cash-credit (CC) facilities are first-class account attributes | ReBIT Deposit schema `Summary/@facility` = `OD`, `CC` | [verified] |
| Branch-printed PSU statements often use a single `Date` label | [Terra Insight](https://www.terra-insight.com/insights/bank-statement-column-variant-parsing) | [unverified] |
| Abbreviation sets differ by bank (e.g. Central Bank `XFER` against other PSU banks' `TR`) | [DNA India](https://www.dnaindia.com/business/report-too-many-acronyms-make-passbooks-a-puzzling-read-1270460/amp) | [unverified] |

**Not found:** an official, public header specification for ICICI, Kotak, PNB, Bank of Baroda, Canara, Union, IDFC First, Yes or IndusInd. Bank help pages describe how to *download* a statement, not its column layout. So the per-bank column sets must come from MindDoc's own (consented, redacted) samples, not from this research.

### 1.2 Variation axes the engine must handle

This list is a synthesis. Each item is supported by the table above, the Bankstatemently challenge list ([README](https://github.com/bankstatemently/bank-statement-parsing-benchmark) **[verified]**), or the AgamiAI dataset card **[verified]**.

1. **Column sets.** Dates are `Date`, `Txn Date`, `Tran Date`, `Transaction Date`, `Value Date` or `Value Dt`. The description column is `Narration`, `Description`, `Particulars` or `Remarks`. The reference column is `Chq./Ref.No.`, `Ref No./Cheque No.` or `Chq No`. Debits are `Withdrawal Amt.`, `Debit` or `Dr`, and credits are `Deposit Amt.`, `Credit` or `Cr`. The balance is `Balance` or `Closing Balance`. Some layouts add extra columns such as `Init. Br` or a branch code.
2. **Direction encoding.** There are four encodings:
   - two amount columns,
   - one amount column with a `Dr`/`Cr` suffix,
   - one signed amount column,
   - one amount column plus a separate indicator column.
3. **Balance sign.** A balance can carry a `Cr`/`Dr` suffix or a minus sign. A `Dr` balance means the account is overdrawn (OD/CC). The balance column can also be sparse, showing only an end-of-day figure (a Bankstatemently challenge).
4. **Multi-line narrations.** Continuation lines have no date and no amount.
5. **Same-day rows with a blank date.** The Bankstatemently Indian sample `bsb-010` lists "Blank Dates for Same-Day Transactions".
6. **Repeated page furniture.** Page headers, column headers and footers ("This is a computer generated statement…") repeat on every page. `bsb-010` also lists "Phantom Balance Rows on Every Page", which are carry-forward rows.
7. **Opening and closing balances.** They can sit in a summary box above the table, in a first row ("Opening Balance" / "B/F"), in a last row, or in a footer summary with debit and credit counts and totals.
8. **Number format.** Indian digit grouping (`1,23,456.78`), with or without `₹`/`INR`, and sometimes `-` or blank for zero.
9. **Dates.** `DD/MM/YYYY`, `DD-MM-YY`, `DD-Mon-YYYY` and `DD Mon YY` all occur. The transaction date and value date can differ. NEFT and cheque entries often post a day apart ([Terra Insight](https://www.terra-insight.com/insights/bank-statement-column-variant-parsing) **[unverified]**).
10. **Password protection.** E-mailed e-statements are often password-protected. Third-party guides give SBI's pattern as the last 5 digits of the mobile number plus the date of birth as `DDMMYY`, and say net-banking downloads are often unprotected ([ClearTax](https://cleartax.in/s/sbi-statement-password) **[unverified]**). **Design rule:** MindDoc accepts a user-typed password per upload, never stores it, and never guesses or brute-forces one.
11. **Passbooks and cooperative banks.** These are scanned or photographed pages from dot-matrix printers, often with no gridlines, a `Folio` or page number, and handwritten annotations. No public description was found **[not found]**, so treat this as the hardest stratum in the benchmark.

---

## 2. Narration semantics in India

### 2.1 Identifiers (formats)

| Identifier | Format | Source | Tag |
|---|---|---|---|
| **IFSC** | 11 characters: 4 letters (bank), `0`, then 6 branch characters. Regex `^[A-Z]{4}0[A-Z0-9]{6}$`. | [RBI NEFT FAQ (updated 2 Sep 2024)](https://rbi.org.in/Scripts/FAQView.aspx?Id=60) | [verified] |
| **RTGS UTR** | 22 characters | [RBI RTGS FAQ (updated 14 Oct 2026), Q23](https://www.rbi.org.in/SCRIPTs/FAQView.aspx?Id=65) | [verified] |
| RTGS UTR inner structure (IFSC prefix + date + channel) | Described in an RBI ISO 20022 FAQ; the PDF redirected and was not read | — | [unverified (unreachable)] |
| **NEFT UTR** | The RBI NEFT FAQ gives **no** length. Blogs disagree (16, 20 or 22 characters). | [RBI NEFT FAQ](https://rbi.org.in/Scripts/FAQView.aspx?Id=60); [Winvesta blog](https://www.winvesta.in/blog/businesses/understanding-utr-numbers-formats-for-neft-rtgs-and-upi) | [verified absence] / [unverified] |
| **UPI / IMPS RRN** | 12 digits is the common claim. NPCI reportedly revised RRN generation in 2024. | [Lexplosion summary](https://lexplosion.in/npci-revises-retrieval-reference-number-in-upi-to-avoid-duplicates-psps-and-banks-to-implement-revised-rrn-and-remove-validation-of-yddd-by-31st-may-2024/) | [unverified] |
| **NACH UMRN** | 20 characters (one source gives a 16-character file field) | [Terra Insight glossary](https://www.terra-insight.com/insights/nach-payments-glossary-india); [NPCI NACH FAQ](https://www.npci.org.in/what-we-do/nach/faqs/debit) does not state a length | [unverified] |
| **MICR** | 9 digits | AgamiAI glossary | [unverified] |
| **UPI VPA** | `handle@psp` | Terra Insight | [unverified] |

**Engineering consequence.** Validate IFSC strictly. Treat UTR, RRN and UMRN as *typed candidates* with length hints, not as hard rules. A validator that rejects a 16-character NEFT UTR because "UTRs are 22 characters" would be wrong.

### 2.2 Rails and how they show up

| Rail / event | What the narration usually carries | Evidence | Tag |
|---|---|---|---|
| **UPI** | `UPI/DR/` or `UPI/CR/`, reference, counterparty name, bank code, VPA or mobile, remark. NPCI Circular 43 (2018) tried to standardise this and noted that banks have about 50–65 characters of narration space. | [NPCI Circular 43](https://www.npci.org.in/PDF/npci/upi/circular/2018/UPI%20-%20Circular%20No.43.pdf) (HTTP 403; excerpt only) | [unverified (unreachable)] |
| **NEFT** | `NEFT Dr-<ref>-<IFSC>-<NAME>` style. The synthetic AgamiAI sample uses exactly this. | [AgamiAI card](https://huggingface.co/datasets/AgamiAI/Indian-Bank-Statements) | [verified as synthetic content] |
| **NEFT return** | The originating bank **must** show "NEFT-Return" in the remitter's passbook or statement. Returns are due within two hours of batch completion. | [RBI NEFT FAQ](https://rbi.org.in/Scripts/FAQView.aspx?Id=60) | [verified] |
| **RTGS** | Minimum ₹2,00,000. Available 24x7 since 14 Dec 2020. A failed credit is returned within one hour or by end of day. | [RBI RTGS FAQ](https://www.rbi.org.in/SCRIPTs/FAQView.aspx?Id=65) | [verified] |
| **NEFT timing** | 24x7, settled in half-hourly batches | [RBI NEFT FAQ](https://rbi.org.in/Scripts/FAQView.aspx?Id=60) | [verified] |
| **IMPS** | IMPS prefix and a 12-digit RRN. Some banks print `MMT` (meaning disputed across sources). | [TaxHeal](https://www.taxheal.com/?p=73494) | [unverified] |
| **NACH / ECS** | `ACH D-` / `ACH C-`, plus UMRN and a batch reference | [Terra Insight workbook](https://www.terra-insight.com/resources/bank-narration-parser-workbook/) | [unverified] |
| **Cheque / clearing** | `CLG`, `BY CLG`, `TO CLG`, cheque number in the ref column. RBI notes that bare "by clg" entries are ambiguous. | [RBI Master Circular 2015](https://rbi.org.in/commonman/English/Scripts/Notification.aspx?Id=1587); [Wishfin](https://wishfin.com/banking/clg-full-form) | [verified] / [unverified] |
| **Cash / ATM / card** | `CSH`, `CASH DEP`, `ATM WDL`, `POS` / `PCD` | Glossaries ([MoneySavingExpert](https://blog.moneysavingexpert.com/banking/bank-statement-codes) is UK) | [unverified] |
| **Interest / charges / TDS** | `Int.Pd`, `INT CR`, `SMS CHGS`, `GST`, `MIN BAL CHGS` | Not found in a primary source | [not found] |
| **Reversals** | `REV`, `RTN`, "reversal", and failed-UPI auto-reversal. AgamiAI includes "Failed transaction reversals" and a `failed` flag. | [AgamiAI card](https://huggingface.co/datasets/AgamiAI/Indian-Bank-Statements) | [verified as synthetic content] |
| **Sweep / FD auto-creation** | Sweep-out to FD and sweep-in breaks (e.g. `TRF TO FD`, `SWEEP`) | Not found in a primary source | [not found] |

### 2.3 What counterparty information can be recovered

From the evidence above, the recoverable fields are:
- rail,
- direction,
- reference (UTR, RRN, UMRN or cheque number),
- counterparty name (often cut short by the roughly 50–65 character field),
- counterparty IFSC (NEFT/RTGS/IMPS) or VPA/mobile (UPI),
- free-text remark.

**Rule.** MindDoc should parse these into *derived* fields with `derived_from = narration` and a parser version. It must keep the raw narration byte-for-byte, and must never overwrite the raw narration with a "cleaned" one.

---

## 3. Extraction approaches compared

### 3.1 Licence and activity of candidate components

Checked on 2026-11-10 with `api.github.com/repos/{owner}/{repo}` (licence SPDX, `pushed_at`, `archived`) and `/releases/latest`, Hugging Face `api/models/{id}`, and the dependency files named in the table. All rows are **[verified]** unless tagged otherwise.

| Component | Licence (where checked) | Latest release | Torch? | Paddle? | Notes |
|---|---|---|---|---|---|
| **pdfplumber** | MIT (GitHub API) | v0.11.10, 2026-06-15 | No | No | `requirements.txt`: `pdfminer.six`, `Pillow`, `pypdfium2` |
| **pdfminer.six** | MIT | 20260107 | No | No | Word and char boxes |
| **pypdfium2** | Apache-2.0 / BSD-3-Clause (README "Licensing"; GitHub API shows no single SPDX). PDFium is BSD-style. | 5.15.2, 2026-11-09 | No | No | PDFium and its dependency licences must ship with binaries (README) |
| **Camelot (camelot-py)** | MIT | v2.0.0, 2026-06-04 | Only in the `ml` extra (TATR flavour). Core "never load[s] torch". | No | Core deps: `pypdfium2`, `playa-pdf`, `opencv-python-headless`, `pandas` (pyproject) |
| **tabula-py** | MIT | v2.11.0, 2026-11-09 | No | No | Needs a **Java** runtime. tabula-java is MIT, last push 2025-03-19. |
| **img2table** | MIT | 2.0.0, 2026-05-10 | Optional extras only | Optional `paddle` extra | Core deps: `numpy`, `pypdfium2`, `opencv-contrib-python`. OpenCV-based bordered/borderless table detection. |
| **Docling** (`docling-slim` in pyproject) | MIT | v2.150.0, 2026-11-10 | **Yes for models**: extra `models-local` = `torch`, `torchvision`, `docling-ibm-models` | No | Docs: "The Docling models depend on the PyTorch library." `docling` = `docling-slim[standard]` with RapidOCR. A `models-onnxruntime` extra exists, but what it enables is undocumented on the install page **[unverified]**. |
| **docling-ibm-models** | MIT | v4.0.4, 2026-10-21 | **Yes, hard dependency** (`torch>=2.2.2`, `torchvision`, `transformers`) | No | Layout model and TableFormer |
| docling-parse | MIT | v7.25.0, 2026-11-09 | No | No | C++ PDF parser |
| docling-models (HF weights) | `cdla-permissive-2.0` and `apache-2.0` tags (HF API) | — | — | — | As in TECHNOLOGY_EVALUATION §4.1 |
| **PaddleOCR** | Apache-2.0 | v3.7.0, 2026-06-11 (last push 2026-09-16) | No | **Yes** (PaddlePaddle) | |
| PP-OCRv5 det/rec, PP-DocLayout_plus-L, SLANet_plus, SLANeXt_wired (HF weights) | `apache-2.0` (HF API, each model) | — | — | — | Table-structure weights are permissive |
| **PaddleOCR-VL** (HF weights) | `apache-2.0` (HF API; modified 2026-11-06) | — | — | Yes | Resolves the "[U]" in TECHNOLOGY_EVALUATION §4.2 |
| PaddleX | Apache-2.0 | v3.7.2, 2026-06-25 | No | Yes | Hosts PP-StructureV3 pipelines |
| **RapidOCR** | Apache-2.0. README: converted PP-OCR models stay under upstream Apache-2.0. | v3.10.0, 2026-10-08 | **No** | **No** | `requirements.txt` lists only `opencv-python-headless`, `numpy`, `pyclipper`, `Shapely` and similar. Install `rapidocr onnxruntime`. |
| **RapidTable** | Apache-2.0 | v3.0.2, 2026-04-23 | Only for the `unitable` model | No | README: `slanet_plus` ONNX is 6.8 MB at about 0.15 s; `unitable` is PyTorch, 500 MB, about 6 s on CPU (vendor numbers) |
| **Tesseract** | Apache-2.0 | 5.5.4, 2026-10-28 | No | No | |
| **OCRmyPDF** | **MPL-2.0** (GitHub API and README) | v17.14.1, 2026-11-09 | No | No | README: "requires external program installations of Ghostscript and Tesseract". Ghostscript is AGPL or commercial from Artifex **[unverified]**. |
| **doctr** | Apache-2.0 | v1.1.0, 2026-08-21 | Likely (PyTorch backend) **[unverified]** | No | |
| **Surya** | Code Apache-2.0. **Weights: "modified AI Pubs Open Rail-M"**, free for research, personal use and startups under **$5M funding/revenue** (README "Commercial usage"). Older HF weights (`datalab-to/surya_layout`, `surya-alpha`, `vikp/surya_rec2`) are tagged **cc-by-nc-sa-4.0** (HF API). | v0.23.0, 2026-10-29 | Yes | No | Excluded from shipping |
| **Marker** | Code Apache-2.0, weights same as Surya (README) | v2.1.0, 2026-10-29 | Yes | No | Excluded from shipping |
| **unstructured** | Apache-2.0 | 0.27.37, 2026-11-06 | **Yes** for `hi_res` (`unstructured-inference` pins `torch>=2.10.0`) | Optional | Also uses `pdf2image` (Poppler) |
| monopoly (bank-statement CLI) | **AGPL-3.0** (README badge) | — | No | No | Per-bank config classes and a "safety check" on totals. Uses `pdftotext`/Poppler and OCRmyPDF. Read for ideas only; do not copy code. |
| Granite-Docling-258M | apache-2.0 (HF API) | — | Yes | No | ML path only |

### 3.2 Approaches side by side

| Approach | Published accuracy evidence | CPU cost | Statement-specific failure modes | Verdict |
|---|---|---|---|---|
| **(a) Bank-specific templates / regex** | AI-BAAM: template matching scored **98.08% matching NED, 97.80% exact NED, 100% row F1** on 6 known Malaysian formats, at about **0.11 s per document** on an M4 MacBook Air ([arXiv 2510.16066](https://arxiv.org/html/2510.16066v4)) **[verified]**. Monopoly and StmtForge use per-bank parsers ([monopoly README](https://github.com/benjamin-awd/monopoly) **[verified]**; [StmtForge](https://pypi.org/project/stmtforge/0.1.0/) **[unverified]**). | Negligible | Breaks silently when a bank changes its layout. Long tail of banks, cooperative banks and passbooks. Code per bank does not scale. | **Use, but as declarative layout profiles** (header aliases, column order, date and amount formats, footer patterns), selected by a fingerprint and checked by reconciliation |
| **(b) Generic layout-aware extraction** (word boxes → header detection → column bands from header x-positions and right-aligned amount clusters → row segmentation on date anchors and y-gaps) | No published benchmark on statements **[not found]**. It is the approach behind pdfplumber's `extract_words` and tables, and AyonPal's parser exposes x-ranges per column ([repo](https://github.com/AyonPal/bank-statement-pdf-parser) **[unverified]**). | Low (pure Python) | Wrapped narrations that cross into amount columns. Headers missing on continuation pages. Single-column Dr/Cr layouts. Skewed scans (need deskew first). | **Core of the slim path.** Works for unseen layouts, and its output feeds (a) and reconciliation. |
| **(c) Table-recognition models and libraries** | TableFormer: TEDS 98.5% simple / 95% complex (abstract, [arXiv 2203.01017](https://arxiv.org/abs/2203.01017)) **[verified]**. PaddleOCR 3.0 report: OmniDocBench edit distance PP-StructureV3 0.145 EN, against 0.589 for Docling-2.14.0 (an old version, vendor-run) ([arXiv 2507.05595](https://arxiv.org/html/2507.05595v1)) **[verified]**. A tools comparison found TATR best for table detection on DocLayNet financial pages and Camelot best on tenders ([arXiv 2410.09871](https://arxiv.org/abs/2410.09871)) **[verified, abstract only]**. TabSniper (DETR, bank statements, CODS-COMAD 2024) gives no public data or numbers ([arXiv 2412.12827](https://arxiv.org/abs/2412.12827)) **[verified]**. | TableFormer 2–6 s per table on CPU (TECHNOLOGY_EVALUATION §4.1). SLANet+ ONNX about 0.15 s per table (vendor). Camelot and img2table are OpenCV-light. | Borderless statements defeat lattice methods. Cell-merge errors on multi-line narrations. Long tables split across pages. TEDS rewards structure, not numeric correctness. | **Optional helper** for scanned or bordered layouts and as a second opinion. Never the only source. |
| **(d) LLM / VLM structured extraction (JSON schema)** | AI-BAAM: best OCR + LLM pipeline (Surya + docTR + GPT-5-mini) scored 96.94% matching / 94.23% exact NED. End-to-end VLMs took **104–150 s per document** "with weaker extraction quality". PaddleOCR-VL and PP-StructureV3 were among the 16 configurations tested. **[verified]** | High (API cost, or a GPU) | Hallucinated or "corrected" amounts, dropped rows on long statements, no coordinates, data egress | **Not for amounts.** Allowed for narration parsing, counterparty normalisation and drafting new layout profiles. Outputs must be grounded to word boxes and pass reconciliation. |
| **(e) Hybrid** | AI-BAAM's ranking (templates > OCR + LLM > VLM) supports a hybrid in which deterministic extraction leads **[verified]** | Low on the default path | Complexity | **Recommended:** (b) + (a) profiles + reconciliation, with (c)/(d) as escalation |

**Key point.** No published system found combines generic extraction with balance-constraint error localisation. That is MindDoc's opportunity, and it must be measured on MindDoc's own benchmark (§6).

---

## 4. Using the balance constraint

### 4.1 What exists

- **Published research.** No peer-reviewed paper was found that uses running balances to infer direction, detect missed rows or localise OCR digit errors **[not found]**. AI-BAAM scores the balance column only by NED and runs no reconciliation check **[verified]**.
- **Open source.** Monopoly validates statement *totals* ("safety check") but is AGPL **[verified]**. The PHP library `webwingscz/bank-statements` derives the opening balance from the oldest row's running balance ([Packagist](https://packagist.org/packages/webwingscz/bank-statements) **[unverified]**). Bankstatemently lists "Running Balance Cross-Check" as a benchmark challenge **[verified]**.
- **Vendors.** Several vendors describe opening → debits/credits → closing checks and balance-delta direction inference ([DocuClipper](https://www.docuclipper.com/blog/how-to-reconcile-a-bank-statement/), [imagetotable](https://imagetotable.ai/blog/how-to-extract-bank-statement-data-into-excel)) **[unverified]**.
- **Forensics.** Practitioners use balance roll-forward *across* statements as a tamper check ([J.S. Held](https://www.jsheld.com/insights/articles/fraudulent-manipulation-of-bank-statements-in-electronic-format)) **[verified]**.

### 4.2 Proposed deterministic algorithm (MindDoc design, not an external claim)

All arithmetic uses `decimal.Decimal` in paise. Raw strings are kept. **No extracted value is ever changed.** Every inference is stored as a separate *suggestion* with its evidence.

1. **Signed balance.** `bal = value × (−1 if suffix Dr / minus / OD-negative else +1)`. The sign convention comes from the layout profile. For OD/CC accounts, a `Dr` balance is negative.
2. **Row identity.** For each row *i*: `bal[i-1] + cr[i] − dr[i] = bal[i]`. Exact equality in paise is required. Rounding tolerance is **0**, because statements print exact paise. A ±1-paise tolerance is allowed only if a profile documents rounding.
3. **Statement identity.** `opening + Σcr − Σdr = closing`. Check it against the summary box, and the debit/credit counts and totals, when they are printed.
4. **Direction inference** (single-column or unreadable Dr/Cr). `delta = bal[i] − bal[i-1]`. If `|delta| = amount`, propose the direction `sign(delta)`. Mark it `direction_source = balance_delta`.
5. **Error localisation.** Each broken row *i* is classified as follows:
   - **Amount misread:** the next identity holds using `bal[i]`, but `|bal[i] − bal[i-1]| ≠ amount[i]`. Test the single-digit-substitution and transposition candidates of `amount[i]` and report those that fix the identity.
   - **Balance misread:** the identities on both sides fail, but `bal[i-1] ± amt[i] ± amt[i+1] = bal[i+1]`. Flag `bal[i]` and test its digit candidates.
   - **Missed row:** `delta − (cr − dr)` is non-zero, the following rows are consistent, and the residual equals an amount on another page or a dropped line. Flag a gap at *i*.
   - **Merged rows:** one extracted row carries two amounts or two dates whose split satisfies two identities. Propose the split.
   - **Wrong direction:** the identity holds only with the sign flipped.
6. **Carry-forward.** Recognise `B/F`, `C/F`, "Balance brought forward", "Opening Balance" and per-page phantom balance rows (Bankstatemently `balance-carry-forward-rows`). Use them as checkpoints, never as transactions. A page-boundary mismatch is a page-level finding.
7. **Same-day ordering.** Statements are usually sorted by posting sequence, not by time. If identities fail only *within* a day, test permutations of that day's rows (bounded, for example ≤8 rows). Report "ordering ambiguity", not an error.
8. **Value date and transaction date.** Reconcile in *printed order*. Never re-sort by value date. Store both dates.
9. **Reversals and returns.** A `REV`/`RTN`/"NEFT-Return" credit that matches an earlier debit's amount (and reference, if present) is linked as `reverses = txn_id`. This does not affect arithmetic.
10. **Sparse balances** (end-of-day only). Check the identity at the end of each day over the summed rows of that day.
11. **Output.** Each row gets `recon_status ∈ {ok, inferred_direction, suspect_amount, suspect_balance, gap_before, ordering_ambiguity, unverifiable}`. The statement gets `recon_pass` (true only when every identity holds with no inference) plus counts per status.

**Interest, charges and TDS** are ordinary rows for arithmetic. Classify them by narration only.

---

## 5. Account Aggregator (ReBIT) as the canonical schema

**Spec.** The Deposit FI schema (`deposit.xsd`, namespace `http://api.rebit.org.in/FISchema/deposit`) is at [specifications.rebit.org.in/api_schema/account_aggregator/documentation/deposit.html](https://specifications.rebit.org.in/api_schema/account_aggregator/documentation/deposit.html), with [v1.2](https://specifications.rebit.org.in/api_schema/account_aggregator/documentation/deposit_v1.2.html) also published **[verified]**. A major **v2.0.0** for Deposit/RD/TD was published on 23 Jan 2025, according to a [Sahamati adoption guideline](https://sahamati.org.in/wp-content/uploads/2025/10/5-Guidelines_Adoption_Deposit_RD_TD_FI_Type_Schema_Version_2.0.0.pdf) and the [api.rebit.org.in](https://api.rebit.org.in) landing page. The v2 field list could not be read because the page is a JavaScript app **[unverified (unreachable)]**.

**Fields (v1.2 and the current documentation page) [verified]:**
- **Account:** `type=deposit`, `maskedAccNumber`, `version`, `linkedAccRef`.
- **Summary:** `currentBalance`, `currency`, `exchgeRate`, `balanceDateTime`, `type` (SAVINGS|CURRENT), `branch`, `facility` (OD|CC), `ifscCode`, `micrCode`, `openingDate`, `currentODLimit`, `drawingLimit`, `status`, and a `Pending` element (amount, CREDIT|DEBIT).
- **Transactions:** `startDate` and `endDate`. Each **Transaction** has `txnId`, `type` (CREDIT|DEBIT), `mode` (CASH|ATM|CARD|UPI|FT|OTHERS), `amount` (xs:float), `currentBalance` (xs:string), `transactionTimestamp`, `valueDate`, `narration` and `reference`.
- ReBIT's Jan 2025 clarification tells FIPs not to leave mandatory fields empty or fill them with dummy data ([Sahamati](https://sahamati.org.in/rebit-clarification-on-mandatory-and-optional-fields-in-fi-type-schema/) **[unverified]**).

**Assessment: adopt it as the core, extend it, and do not use it as storage types.**

| Issue | Consequence for MindDoc |
|---|---|
| `amount` is `xs:float` and `currentBalance` is a string | Store `Decimal(18,2)` plus the raw string. Never float. |
| `mode` is coarse: `FT` lumps NEFT, RTGS, IMPS and internal transfers | Add `rail` (UPI, NEFT, RTGS, IMPS, NACH, CHEQUE, CASH, ATM, CARD, INTEREST, CHARGE, TAX, SWEEP, REVERSAL, OTHER) and a deterministic `rail → mode` map |
| `type` has only CREDIT/DEBIT. There is no reversal link and no opening-balance row. | Add `reverses_txn_id`, plus statement-level `opening_balance` and `closing_balance` |
| `currentBalance` has no explicit sign rule for OD | Add `balance_signed` and `balance_raw` (keeping the printed Dr/Cr suffix) |
| No provenance | Add `page`, `bbox`, `source_spans`, `extractor`, `extractor_version`, `recon_status`, `confidence` |
| `txnId` and `reference` are FIP-assigned | For PDFs, `txnId` = a deterministic hash of (statement, page, row index). The printed reference goes in `reference`, with typed `utr`, `rrn`, `umrn` and `cheque_no`. |
| Holder PII (`dob`, `pan`, `mobile`) is in Profile | Map, but mask by default and keep out of indexes and LLM prompts |

The benefit is that AA JSON and parsed PDFs land in one model, so a PDF can be cross-checked against AA data for the same period when a customer consents. That is a strong authenticity check that needs no fraud verdict.

---

## 6. Datasets and evaluation

### 6.1 Datasets

| Dataset | What | Licence (checked) | Fit |
|---|---|---|---|
| [AgamiAI/Indian-Bank-Statements](https://huggingface.co/datasets/AgamiAI/Indian-Bank-Statements) | Synthetic Indian **current-account** statements. Scanned PDF plus JSON (date, value date, description, cheque number, debit, credit, balance, `failed`). Covers UPI, NEFT, RTGS, IMPS, cheque, cash, ATM, charges and reversals. HF size tag 10K–100K. | **Apache-2.0** (HF API tag and card) **[verified]** | **Best available.** Use it for row-level and reconciliation metrics. Caveats: no savings or OD accounts, "synthetic OCR", and the sample uses real-looking company names and real bank IFSC prefixes. |
| [Bankstatemently benchmark](https://github.com/bankstatemently/bank-statement-parsing-benchmark) | 15 synthetic statements planned, 5 released. The Indian `bsb-010` (27 pages, 500 transactions, phantom balance rows, blank same-day dates) is "coming soon". Ground truth is held server-side and scored via API. | **MIT** (GitHub API) **[verified]** | Useful challenge taxonomy. Little data yet. Scoring requires sending outputs to a third party. |
| [SynFinTabs](https://huggingface.co/datasets/ethanbradley/synfintabs) ([paper](https://arxiv.org/abs/2412.04262)) | Synthetic financial tables with words and positions. Generation code released. | **MIT** (HF API) **[verified]** | Table-structure pre-training and tests, not statements |
| FinTabNet, PubTables-1M, DocLayNet | Annual-report tables and layout | CDLA-Permissive (see BENCHMARK_DATASETS §1) | Table models only |
| AI-BAAM dataset (~110 Malaysian PDFs) | Real statements | **Not public** (PDPA) **[verified]** | Not usable |
| PersonaLedger, IBM AML (transaction rows) | Synthetic transactions, no PDFs | Not checked | For downstream analytics, not extraction |

**Synthetic generator (recommended).** Build a MindDoc generator that renders ground-truth JSON through **layout profiles** that imitate observed Indian variants. It should vary:
- column sets,
- Dr/Cr encodings,
- OD balances,
- multi-line narrations,
- B/F and C/F rows,
- blank same-day dates,
- page furniture.

It then degrades the output: rasterise at 150–300 dpi, skew, add noise and JPEG artefacts, add "photo of a printout". Use fictitious IFSC prefixes (BENCHMARK_DATASETS §3.6 already recommends fictitious codes). The truth is known by construction, including balances.

### 6.2 Why table metrics are not enough

- **TEDS** (tree edit distance over HTML) and **GriTS** (grid similarity, used for PubTables-1M) score *structure*.
- A table with one wrong digit in one amount can score about 0.99 TEDS and still make the statement wrong.
- A dropped row costs little in TEDS but breaks every balance after it.
- Statements are **ledgers**. The unit of truth is the transaction row, and the balance identity gives a free, label-free correctness signal.
- Report TEDS and GriTS only for table-model comparisons (§3, path c).

### 6.3 Proposed metrics for a bank-statement benchmark

| Metric | How to compute |
|---|---|
| **Row recall / precision / F1** | Match predicted to gold rows by Hungarian assignment. Cost = 0 if date, amount and direction are equal, otherwise 1 + normalised narration distance. A match needs the same amount and direction plus a date within 0 days. Recall = matched / gold, precision = matched / predicted. |
| **Field accuracy** (per field: date, value date, amount, direction, balance, reference, narration) | Over matched rows: exact match for date, value date, amount (paise), direction, balance (signed) and reference. **Normalised edit similarity** (1 − Levenshtein/max length) for narration, and also an exact-match rate. |
| **Statement exact match** | Share of statements whose row list equals gold in order, on all numeric fields |
| **Reconciliation pass rate** | Share of statements where every row identity and the opening/closing identity hold *without* inference (`recon_pass`). Report it on gold-correct and on all extractions. |
| **Error-localisation accuracy** | Inject k known faults into gold (digit substitution, transposition, dropped row, merged rows, flipped direction, swapped same-day order). Score top-1 and top-3 accuracy of the localiser pointing at the faulty row and field, and fault-type accuracy. |
| **False-alarm rate** | On statements whose extraction equals gold: share of rows flagged with any non-`ok` status. Target 0. |
| **Detection recall for real extraction errors** | Among rows where extraction ≠ gold (from row matching), share flagged non-`ok` |
| **Direction-inference accuracy** | On single-column or masked-indicator layouts: inferred direction against gold |
| **Throughput and memory** | Seconds per page (p50/p95) and peak RSS, on CPU, per stratum (text-layer, clean scan, noisy scan, photo), on the Render-sized box (512 MB) and on a laptop |
| **Grounding coverage** | Share of extracted fields with page and bbox provenance |
| **Profile coverage** | Share of statements handled by a known layout profile against the generic path |

Stratify every metric by bank or layout family, text-layer versus scan, and account type (savings, current, OD/CC).

---

## 7. Fraud and tampering cues (research only)

**Constraint.** MindDoc **never issues an automated fraud verdict.** It reports *observations* with evidence ("balance identity fails at row 41", "producer field is an image editor") for a human to weigh.

| Cue | What practitioners check | Source | Tag |
|---|---|---|---|
| Font and size differences in edited fields | Compare glyphs and fonts in amounts and balances | [J.S. Held](https://www.jsheld.com/insights/articles/fraudulent-manipulation-of-bank-statements-in-electronic-format) | [verified] |
| Scan-looking document that is actually text, or the reverse | File-type and conversion history | J.S. Held | [verified] |
| PDF security settings | Presence or absence of protection (weak alone) | J.S. Held | [verified] |
| Balance roll-forward across periods | Closing balance of month *n* = opening balance of month *n+1*. Note that forgers often roll balances forward to hide edits, so passing arithmetic is **not** proof of authenticity. | J.S. Held | [verified] |
| Fee patterns | Excess fees can reveal hidden overdrafts | J.S. Held | [verified] |
| Comparison with the bank's original | Seen as the decisive test | J.S. Held | [verified] |
| Incremental saves and xref revisions | Appended revisions show edits. Signatures add legitimate revisions. | [PDF Association talk, Sept 2025](https://pdfa.org/wp-content/uploads/2025/10/1-3-11_00-CherieEkholm-In_Defence_of_Incremental_Saves.pdf) (HTTP 403); [practitioner blog](https://dev.to/iurii_rogulia/pdf-xref-table-forensics-detect-edits-from-file-structure-3n7i) | [unverified (unreachable)] / [unverified] |
| Producer and creator, CreationDate against ModDate | Image editor or word-processor producer; a large gap between the dates | [Heron Data](https://www.herondata.io/action-guides/detect-tampering-for-bank-statements), [Inscribe](https://www.inscribe.ai/solution-explorer/fake-bank-statement-detector) | [unverified, vendor] |
| Structuring, rapid in-out, circular or round-trip flows | Repeated just-under-threshold cash. Funds credited and debited within hours. A → B → A cycles between related parties. | [Jurishour](https://www.jurishour.in/columns/money-laundering-red-flags/); [RBI 2009 STR circular with FIU-IND indicators](https://website.rbi.org.in/documents/87730/39016390/4EFSSTR_271109.pdf) (not read) | [unverified] |
| Cash reporting threshold (₹10 lakh CTR) | Context for structuring analysis | [Signzy](https://www.signzy.com/blogs/complete-fiu-ind-reporting-guide-what-you-need-to-know) | [unverified] |

**Implementation note.** Metadata, font-run and incremental-update checks need only pypdfium2/pdfminer and are torch-free. Circular-flow detection reuses the existing Postgres + NetworkX graph (ADR-0005), with counterparties taken from the narration parse.

---

## 8. Recommended extraction architecture for MindDoc

### 8.1 Slim CPU path (default; no torch, no paddle; must fit Render 512 MB)

```
upload ─► decrypt (user-typed password, pypdfium2) ─► page triage
          │   text layer present?  yes ─► word boxes (pdfplumber/pdfminer; chars → words with x0,x1,top,bottom)
          │                        no  ─► render (pypdfium2) ─► OpenCV quality/deskew (existing app/vision/cv.py)
          │                                 ─► OCR: RapidOCR (ONNX Runtime) ; fallback Tesseract (TSV word boxes)
          ▼
   statement detector (bank name, IFSC/MICR, header keywords) ─► layout fingerprint
          ▼
   layout profile? ── yes ─► profile-guided columns (aliases, order, date/amount formats, footer regexes)
          │          no  ─► generic: header-row search with alias dictionary; column bands from header x-spans,
          │                 refined by x-clustering of right-aligned numeric tokens; date-anchored row starts;
          │                 continuation lines (no date, no amount) appended to narration
          ▼
   furniture filter (repeated header/footer lines across pages, B/F–C/F rows → checkpoints)
          ▼
   value parsing (Indian grouping, ₹/INR, Dr/Cr suffix, parentheses, blank/“-”) — raw strings kept
          ▼
   reconciliation engine (Decimal; §4.2) ─► per-row recon_status, statement recon_pass, suggestions
          ▼
   narration parser (rail, refs: IFSC regex strict; UTR/RRN/UMRN as typed candidates; counterparty)
          ▼
   canonical model (ReBIT-aligned + extensions, §5) with page/bbox provenance ─► review UI
```

- **Profiles are data, not code.** Each profile is a YAML file holding header aliases, column order, date format, Dr/Cr encoding, the balance sign rule, footer and furniture regexes, and the B/F and C/F labels. Profiles live under version control, each with a test fixture. A new bank should need a profile, not a release.
- **Escalation rule.** If `recon_pass` is false after profile and generic extraction, retry with alternative column-band hypotheses (bounded) and alternative OCR (RapidOCR ↔ Tesseract). Then stop and send the statement to human review with the localised suspects. **Never** auto-fix printed values.
- **Memory.** RapidOCR's PP-OCR mobile models plus ONNX Runtime are expected to be small, but this was **not measured** here. Measure peak RSS before committing to 512 MB (open question 1).

### 8.2 Optional ML path (separate install extra; torch and/or paddle allowed; licence-clean)

| Use | Component | Why |
|---|---|---|
| Bordered or complex scanned tables | **img2table** (MIT, OpenCV) first. Then **RapidTable SLANet+** (ONNX, Apache-2.0, **no torch**). Then **PP-StructureV3** (Apache-2.0 weights, needs paddle). | Ordered by cost. The first two are still torch-free. |
| General layout and second-opinion tables | **Docling** standard pipeline (MIT + CDLA/Apache weights; **needs torch**) | Good provenance, and already chosen in ADR-0006 |
| Hard pages (photos, passbooks) | Granite-Docling-258M (Apache-2.0) or PaddleOCR-VL (Apache-2.0 weights) | GPU-preferred, so later |
| Narration normalisation and profile drafting | Existing VLM/LLM gateway with JSON schema | Grounded to word boxes and gated by reconciliation. No amounts. |
| Not allowed in shipping | Surya/Marker weights (OpenRAIL-M with a $5M cap; older HF weights CC-BY-NC-SA), monopoly (AGPL), PyMuPDF (AGPL), Ultralytics/DocLayout-YOLO (AGPL) | Licence policy |

### 8.3 Changes this implies for ADR-0006

1. **Docling moves to the ML path.** Its models need PyTorch (`docling-ibm-models` hard-depends on `torch`; the docs say so). The slim path uses pypdfium2 + pdfplumber/pdfminer directly.
2. **Primary OCR on the slim path: RapidOCR + ONNX Runtime**, not PaddleOCR. It runs the same Apache-2.0 PP-OCR models without the PaddlePaddle framework. Docling itself now ships RapidOCR as its default. Keep Tesseract as the fallback and PaddleOCR on the ML path.
3. **Table engine choice.** Add img2table and RapidTable (SLANet+ ONNX) as torch-free candidates next to TableFormer and PP-StructureV3. For bank statements, select by **row F1 and reconciliation pass rate**, not TEDS alone.
4. **OCRmyPDF:** the licence is fine (MPL-2.0), but the Ghostscript runtime dependency keeps it out of the shipped image.
5. **PaddleOCR-VL weights are Apache-2.0** (HF API). This closes an open "[U]".

---

## 9. Licence table for recommended components

| Component | Role | Licence | How checked | Torch / Paddle |
|---|---|---|---|---|
| pypdfium2 (+ PDFium) | Decrypt, render, metadata | Apache-2.0 / BSD-3-Clause; PDFium BSD-style | README "Licensing" | None |
| pdfplumber | Word and char boxes, line objects | MIT | GitHub API | None |
| pdfminer.six | Text layout under pdfplumber | MIT | GitHub API | None |
| OpenCV (opencv-python-headless) | Deskew and quality (existing) | Library Apache-2.0; wheel packaging MIT | GitHub API (`opencv/opencv`, `opencv/opencv-python`) | None |
| RapidOCR | Slim-path OCR | Apache-2.0; models Apache-2.0 (upstream PaddleOCR) | GitHub API + README | None |
| ONNX Runtime | Inference for RapidOCR / RapidTable | MIT | GitHub API (`microsoft/onnxruntime`) | None |
| Tesseract (+ pytesseract) | OCR fallback | Apache-2.0 (Tesseract) | GitHub API; pytesseract not re-checked **[unverified]** | None |
| Camelot 2.x (optional, lattice tables) | Bordered text-layer tables | MIT; dependency `playa-pdf` MIT | GitHub API; playa LICENSE + pyproject | None (core) |
| img2table (optional) | Bordered tables on scans | MIT | GitHub API + pyproject | None (core) |
| RapidTable SLANet+ (optional) | Table structure, ONNX | Apache-2.0 (code); SLANet_plus weights apache-2.0 (HF API) | GitHub API + HF API | None |
| NetworkX | Circular-flow observations | BSD-3-Clause (TECHNOLOGY_EVALUATION §3.3) | not re-checked | None |
| *ML path:* Docling + docling-ibm-models + docling-models | Layout, TableFormer | MIT / MIT / CDLA-Permissive-2.0 + Apache-2.0 | GitHub API + HF API | **torch** |
| *ML path:* PaddleOCR / PaddleX / PP-StructureV3 weights | OCR and tables | Apache-2.0 (code and HF weights) | GitHub API + HF API | **paddle** |
| *ML path:* Granite-Docling-258M, PaddleOCR-VL | Hard pages | Apache-2.0 | HF API | torch / paddle |
| Data: AgamiAI Indian-Bank-Statements | Benchmark | Apache-2.0 | HF API + card | — |
| Data: Bankstatemently benchmark | Challenge set | MIT | GitHub API | — |
| Data: SynFinTabs | Table tests | MIT | HF API | — |

---

## 10. Open questions

1. **Memory budget.** Does RapidOCR + ONNX Runtime + pdfplumber fit under 512 MB RSS on a 30-page scanned statement? Measure p95 RSS and seconds per page.
2. **ReBIT v2.0.0 deltas.** Did v2.0.0 change Transaction `mode`/`type` enums or numeric types? The documentation app could not be read. Fetch the XSD from a FIP sandbox or Sahamati.
3. **Real-format coverage.** Which 12 banks' current layouts (net-banking, app, branch, corporate) does MindDoc need first? Profiles need consented, redacted samples. This research found no public header specifications beyond HDFC (snippets).
4. **NEFT UTR and UPI RRN.** Is there an authoritative length or structure? The NPCI circular was unreachable (HTTP 403). Until then, typed candidates only.
5. **Ghostscript.** Confirm its licence and whether any planned path needs it (OCRmyPDF, pdf2image/Poppler are GPL-family). The working assumption is to keep both out of the image.
6. **Docling `models-onnxruntime`.** Does this extra run the layout model or TableFormer without torch? If yes, Docling could return to the slim path. It is not documented on the install page.
7. **Passbooks and cooperative banks.** No public samples or specifications. Decide whether they are in scope for v1 or "review-only".
8. **Synthetic-data realism.** AgamiAI uses real-looking company names and real IFSC prefixes. Confirm acceptable use, or regenerate with fictitious codes in MindDoc's own generator.
9. **Reconciliation tolerance.** Do any target banks print rounded balances (for example on interest rows) that would need a documented ±1-paise profile tolerance?
10. **AA cross-check UX.** When AA data and a PDF disagree for the same period, how does the review UI present it without implying a fraud verdict?

