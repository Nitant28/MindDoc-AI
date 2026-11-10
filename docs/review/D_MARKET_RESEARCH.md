# D — Market Research: Re-checking ADR-0008 (Lender Forensics, India)

*Deliverable D of the project review · Prepared 2026-11-10 · Status: complete (desk research; no interviews yet)*

**Scope.** This report re-checks and extends `docs/strategy/MARKET_SELECTION.md`, `docs/strategy/COMPETITIVE_ANALYSIS.md`
and `docs/strategy/PRODUCT_DIFFERENTIATION.md`, which support ADR-0008 (primary market: forensic review of borrower
fund flows for lenders in India).

**Conventions**

- **[verified]** = the author read the cited source (or its downloaded text) during this session, and the source is
  primary (regulator, court, standard-setter) or the vendor's own page about itself. Vendor claims stay claims.
- **[unverified]** = secondary source (press, law-firm note, aggregator, a third-party copy of a document), a
  search-result snippet only, or uncertain. Where a secondary page was read in full, this is said.
- **Fact** = what a source says. **Inference** = our reasoning from facts. **Recommendation** = what we propose.
- "Not found" means a focused search did not surface a credible source. Sources that exist but could not be opened
  are listed in the Appendix and tagged [unverified] where used.
- All sources accessed 2026-11-10 unless stated.

---

## 0. Verdict

**The evidence is inconclusive and, on commercial grounds, weakens ADR-0008.** The *problem* is now better supported
than the strategy docs claimed. RBI's 2026 directions keep a 180-day, notice-and-reasoned-order process for every
red-flagged account. The 2024 wilful-defaulter direction defines diversion and siphoning and tells lenders to consider
forensic audits. The Supreme Court in *Amit Iron* (7 Apr 2026) made giving the forensic report to the borrower
mandatory, which raises the value of traceable, recomputed findings. The *business* is weaker on three counts. First,
RBI allows an "external audit or internal audit". It does not require an outside forensic firm, so the volume reaching
the ICP is unproven. Second, the only published fee schedule found caps a forensic audit of an account up to ₹50 crore
at ₹80,000. The planned ₹25,000–60,000 per-case price would then be 31–75% of the fee. Third, the competitive gap is
smaller than claimed. IDfy, Cygnet, iAcuity and others already flag round-tripping and related-party flows, and ICAI's own
AI portal showcases a CA's forensic statement review published as a general-LLM (claude.ai) artifact. AA does not remove the need to read PDFs for
forensic work, but MindDoc cannot win on parsing. **Riskiest assumption: that forensic firms (or the banks behind
them) will pay a meaningful price per engagement out of fees that the one published schedule caps at ₹80,000 for
accounts up to ₹50 crore.** Rescoring with this evidence brings forensic (3.70–3.85) level with the procurement
fallback (3.70). The 25 interviews in §7 should decide it.

### Five findings that matter most

| # | Finding | Tag |
|---|---|---|
| 1 | RBI requires an external **or internal** audit of red-flagged accounts, with a 180-day target. The word "forensic" is not in the operative text (2024 and 2026 bank directions). | [verified] §1.1 |
| 2 | *Amit Iron* (2026 INSC 323): no personal hearing, but the forensic report must be given to the borrower; only third-party parts may be withheld. | [verified] §1.2 |
| 3 | The wilful-defaulter direction (30 Jul 2024) defines diversion and siphoning, sets end-use monitoring duties and says lenders "shall consider" a forensic audit. | [verified] §1.3 |
| 4 | Lender tools already do much of the planned analysis: IDfy TIP (round-tripping, hidden related parties) and Cygnet Finalyze (related-party flows, GST/ITR checks, audit trail). | [verified] §3.1 |
| 5 | Published forensic fees are low: ₹80,000 cap up to ₹50 crore, ₹5 lakh above ₹1,000 crore (J&K Bank 2022, via TaxGuru). | [unverified] §5.1 |

### Contradictions with the existing strategy docs

- COMPETITIVE_ANALYSIS §0 says no one offers cross-document fund-trail and related-party investigation. IDfy TIP,
  Cygnet Finalyze, iAcuity Fund Trail and CypherSOL cover large parts of it (§3).
- MARKET_SELECTION §2.1 implies red-flagging leads to outside forensic audits. RBI allows internal audit (§1.1).
- MARKET_SELECTION §9 prices small cases at ₹25,000–60,000. The only published fee cap is ₹80,000 (§5).
- The strategy docs cite the 2024 directions. For commercial banks these were consolidated into 2026 directions on
  31 Jul 2026 (§1.1).

## 1. Regulation that creates or shapes the work

### 1.1 RBI fraud-risk directions: what they actually require

**Facts.**

| Item | What the source says | Tag |
|---|---|---|
| Versions | Master Directions on Fraud Risk Management for commercial banks and AIFIs, 15 Jul 2024 (RBI/DOS/2024-25/118) ([RBI MD id 12702](https://rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=12702)). For commercial banks these are now consolidated into the *RBI (Commercial Banks – Fraud Risk Management) Directions, 2026*, 31 Jul 2026 (RBI/DoS/2026-27/412) ([RBI MD id 13641](https://rbi.org.in/SCRIPTS/BS_ViewMasDirections.aspx?id=13641)). Both read in full text, accessed 2026-11-10. The rules below appear in both; paragraph numbers are from 2024. | [verified] |
| Red flags | A red-flagged account (RFA) is one where one or more early-warning-signal (EWS) indicators raise a suspicion of fraud (3.1.1). Banks must run a "Data Analytics and MI Unit" (3.3.2). An RFA above the CRILC threshold is reported to RBI within 7 days (3.3.4). | [verified] |
| Who investigates | The bank "shall use an external audit or an internal audit" under its Board-approved policy (4.1; 2026 para 26). The policy covers auditors' due diligence, competency and track record. Contracts fix a report deadline. Loan agreements must allow the audit (4.1.1–4.1.2). External auditors must be "qualified to conduct audit under relevant statutes" (footnote 14). If the report is inconclusive or delayed by the borrower, the bank decides on "the material available on their record" (4.1.2). | [verified] |
| Timeline | Classification, or removal of the red flag, should "ordinarily be completed within 180 days" of the first CRILC report (4.1.5; 2026 para 31). | [verified] |
| Natural justice | A detailed show-cause notice with "complete details of transactions", at least 21 days to reply, and a reasoned order (2.1.1.1–2.1.1.4). The 2026 text spells out that the persons who can be served include "third party service providers and professionals", naming chartered accountants. It cites *Rajesh Agarwal*. A text search found no reference to *Amit Iron*. | [verified] |
| The word "forensic" | Absent from the operative text of both versions. In 2024 it appears only in the list of repealed circulars ("Conduct of Forensic Audit for investigation of accounts from fraud angle", 11 May 2021). | [verified] |
| NBFC directions | A separate *RBI (NBFC – Fraud Risk Management) Directions, 2026* (RBI/DoS/2026-27/463, 31 Jul 2026) is reproduced on TaxGuru. It covers Upper- and Middle-Layer NBFCs and Base-Layer NBFCs with assets of ₹500 crore or more. It uses the same "external or internal audit" wording and the 21-day notice. The EWS framework applies to Upper and Middle Layer only. ([TaxGuru reproduction](https://taxguru.in/?p=1064784), accessed 2026-11-10). The RBI original was not opened. | [unverified] |

**Inferences.**

1. The regulation creates an *investigation step* on every red-flagged account. It does **not** mandate a forensic audit by an outside CA firm. A bank may use its own internal audit. How much work reaches outside forensic firms depends on each bank's Board policy. Our strategy docs assume the work goes outside. That assumption is still untested.
2. The 180-day clock and the 21-day notice set the turnaround. The forensic report has to land well inside 180 days so that the notice, the reply and the order can follow.
3. The 2026 text names chartered accountants among the "professionals" who can get a show-cause notice. That raises the personal risk for a CA who signs a weak report. This is a reason for firms to want traceable working papers, and also a reason for caution about any tool that could be blamed.

### 1.2 The courts: *Rajesh Agarwal* (2023) and *Amit Iron* (2026)

| Case | Holding relevant to MindDoc | Tag |
|---|---|---|
| *SBI v. Rajesh Agarwal*, Supreme Court, 27 Mar 2023 | Natural justice must be read into the fraud directions. Para 81(vi): borrowers must get a notice and a chance "to explain the conclusions of the forensic audit report". Classification must be by reasoned order. No hearing is needed before an FIR (81(i)). ([judgment PDF, sci.gov.in](https://api.sci.gov.in/supremecourt/2021/1710/1710_2021_1_1501_43127_Judgement_27-Mar-2023.pdf), downloaded and text-searched 2026-11-10) | [verified] |
| *SBI v. Amit Iron Pvt Ltd*, Supreme Court, 7 Apr 2026, 2026 INSC 323 | Para 126: there is no right to a personal hearing. The 2024 procedure (notice, reply, reasoned order) is enough. Wherever audit reports, including forensic audit reports, exist and the bank treats them as relevant, giving them to the borrower is "mandatory". A digital copy counts. Parts may be withheld only to protect third-party privacy, with reasons recorded (126(e)). Para 121: the borrower has a right to disclosure of "the material relevant to the proceeding". ([judgment PDF via LiveLaw](https://www.livelaw.in/pdf_upload/2026/04/07/3487720252026-04-07-666217.pdf), downloaded and text-searched 2026-11-10) | [verified] |

**What this implies for the evidence a borrower sees (inference).** The borrower's counsel will now read the full forensic report and argue against it. Every finding must therefore stand up to an adversarial reader. For MindDoc this supports three features that are in the plan already: page-level citations, recomputed numbers and an exportable evidence bundle. It also adds one new need: **redacting third-party data**. Under *Amit Iron* a bank may withhold only those parts that affect third parties. A tool that tags third-party personal data, and can produce a redacted copy with recorded reasons, fits that rule exactly. This feature is not in the current scope (see §8).

The strategy docs called *Amit Iron* "reported" and said to read it before quoting. It has now been read, and the docs' summary holds.

### 1.3 End-use monitoring and diversion of funds

| Item | What the source says | Tag |
|---|---|---|
| Source | RBI *Master Direction on Treatment of Wilful Defaulters and Large Defaulters*, 30 Jul 2024 (RBI/DoR/2024-25/122). It is addressed to commercial banks, co-operative banks, AIFIs, NBFCs including HFCs, and ARCs. ([RBI MD id 12713](https://rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=12713), accessed 2026-11-10) | [verified] |
| Definitions | "Diversion of funds" includes using short-term working capital for long-term purposes, creating assets other than those financed, and moving loan funds to subsidiaries or group companies without lender approval. "Siphoning" means using loan funds for purposes unrelated to the borrower's operations. (same source, para 3) | [verified] |
| End-use monitoring | Lenders must "closely monitor the end-use of funds" and take end-use certificates from borrowers. Measures that can go in the loan policy include scrutiny of quarterly reports and balance sheets, scrutiny of the books and of "no-lien" accounts with other lenders, and stock audits. Lenders must not just depend on CA certificates. (same source, para 17) | [verified] |
| Forensic mandate | A lender may give the borrower's auditors a separate mandate to certify diversion or siphoning, or engage its own auditors. The lender "shall consider commissioning a forensic audit" for accounts above a threshold its Board sets (para 18(4)–(6)). (same source) | [verified] |
| Wilful-default threshold | Reported as ₹25 lakh outstanding and above (secondary summary in search results). | [unverified] |

**Inference.** This direction, more than the fraud directions, is the regulatory anchor for "loan end-use and related-party fund-trail review". It names the exact tests MindDoc's detectors D1–D3 aim at: diversion to group companies, routing through other lenders, and siphoning. It also creates a second trigger for outside work (wilful-default review), separate from red-flagging. The strategy docs do not cite it.

### 1.4 ICAI Forensic Accounting and Investigation Standards (FAIS)

- FAIS apply to forensic accounting and investigation engagements carried out "on or after 01st July 2023". The announcement points to a Compendium and an Implementation Guide. ([ICAI DAAB announcement](https://www.icai.org/post/daab270723), accessed 2026-11-10) **[verified]**
- FAIS 510 (Reporting Results) calls for a written report with the findings and the evidence relied on, "in a structured manner". This comes from a TaxGuru summary of a 2023 draft guidance note. ([TaxGuru](https://taxguru.in/chartered-accountant/draft-guidance-note-fais-510-reporting-results.html)) **[unverified]**
- FAIS 320 covers evidence and documentation, per the Implementation Guide's contents page seen in search results. The text itself could not be downloaded (the file was truncated). **[unverified]**
- **Not verified:** the exact FAIS wording on evidence sufficiency, documentation and the use of technology or experts. The Compendium (publication.icai.org/publication/1159) is behind ICAI's publication portal and was not read.

**Inference.** FAIS makes the forensic report the CA's professional product, signed by the member. A tool can prepare working papers and drafts. It cannot sign or form the conclusion. This matches ADR-0008's "never label fraud" rule. It also means the buyer will judge MindDoc by whether its output files cleanly into FAIS working papers. Check that in interviews.

### 1.5 Data protection (DPDP) and data location

| Item | What the source says | Tag |
|---|---|---|
| DPDP phasing | Rules notified 13 Nov 2025. Data Protection Board provisions applied at once. Consent-manager provisions apply after 12 months (about 12–13 Nov 2026, i.e. this week). The substantive duties apply after 18 months (about 12–13 May 2027): notice, consent, security safeguards, breach notification and cross-border transfer rules. ([AZB & Partners](https://www.azbpartners.com/?p=87799), accessed 2026-11-10) | [unverified] (law-firm summary; Gazette not read) |
| Processor | The Government's explanatory note defines a Data Processor as an entity that processes personal data on behalf of a Data Fiduciary. ([PIB explanatory note](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc20251117695301.pdf), text extracted 2026-11-10) | [verified] |
| Loan-default exemption | Section 17(1)(f) is reported to disapply most of the consent and notice duties when personal data is processed to find out the financial information, assets and liabilities of a person who has defaulted on a loan from a financial institution. The security duty in section 8(5) still applies. ([Sansa Legal](https://www.sansalegal.com/post/how-to-rely-on-the-loan-default-exemption-under-section-17-1-f-of-the-dpdp-act); [dpdpa.com text](https://dpdpa.com/dpdpa2023/chapter-4/section17.html)) | [unverified] |
| Bank vendors and data location | RBI's IT-outsourcing direction (10 Apr 2023, in force 1 Oct 2023) requires outsourcing contracts to provide for "storage of data (as applicable to the concerned REs) only in India as per extant regulatory requirements", and for the vendor to disclose what data it captures, processes and stores. ([RBI MD id 12486](https://rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=12486), accessed 2026-11-10) | [verified] |

**Inferences.**

1. Bank statements in a forensic file hold personal data about promoters, guarantors, employees and third-party payees. The bank is the most likely data fiduciary. The forensic firm acts for the bank, and MindDoc would be a processor or sub-processor. The full duties start in May 2027. The section 17(1)(f) exemption may cover processing on defaulted accounts, but not on standard accounts that are only red-flagged. That needs a lawyer's view.
2. The security duty applies either way. So MindDoc needs encryption, access logs and a breach runbook. That is already on the roadmap.
3. The forensic firm is not itself an RBI-regulated entity. But the bank's engagement letter is likely to pass the "India-only storage" clause down to the firm and its tools (inference; check against real engagement letters). India-region hosting or on-premises deployment is a must-have, not a nice-to-have.

### 1.6 Insolvency (IBC) avoidance reviews

| Item | What the source says | Tag |
|---|---|---|
| Scale | As of the DFS Secretary's speech at IBBI's Annual Day (1 Oct 2025): 1,442 avoidance applications covering about ₹3,89,964 crore filed; 379 cases (₹66,919 crore) disposed; about ₹7,930.77 crore clawed back. 8,608 CIRPs had been started up to 31 Aug 2025. ([IBBI PDF](https://ibbi.gov.in/uploads/resources/b66e4245b3595b937ae925b1aad0a390.pdf), text extracted 2026-11-10) | [verified] |
| Look-back change | The same speech says the IBC amendment Bill would count the look-back period from the date of filing, not the insolvency commencement date, which widens the window. (same source) | [verified] |
| Recent flow | Oct–Dec 2025: 163 CIRP admissions; 1,879 ongoing at 31 Dec 2025 (IBBI newsletter Vol. 37, via a secondary summary). Up to June 2026: 9,166 admitted. ([KNA LLP summary](https://knallp.com/?p=11955); search snippet of an IBBI publication) | [unverified] |
| Deadlines (CIRP Regulation 35A) | The resolution professional (RP) must form an opinion on preferential, undervalued, fraudulent and extortionate transactions (IBC ss. 43, 45, 49/50, 66) by about day 75, make a determination and inform IBBI by day 115, and apply to the tribunal by day 135. Whether these deadlines bind is disputed before tribunals. (search snippets of IBBI orders, e.g. [IBBI order](https://ibbi.gov.in/uploads/order/e2bbcb21f7efbbd24f95e824c539b6d5.pdf)) | [unverified] |
| Is a "transaction audit" mandatory? | Not found. No source seen requires the RP to hire an outside transaction auditor. In practice RPs commonly appoint one. That is an inference and must be tested. | not found |

**Inference.** IBC avoidance review is a real and recurring step. Every CIRP needs an opinion on avoidance transactions. The one recent data point is 163 admissions in Oct–Dec 2025 (unverified), or roughly 650 a year if that rate holds (assumption). The spend is paid from CIRP costs, which the committee of creditors approves. That makes it a second buyer for the same workflow. Volume is not the issue. Fees and procurement are: RPs pick auditors through quotes, and the committee of creditors sees the cost.

## 2. Account Aggregator and what it means for PDF parsing

### 2.1 How lenders get bank statements today

| Fact | Source | Tag |
|---|---|---|
| As of 31 Mar 2026: 179 institutions live as data providers (FIPs), 989 as data users (FIUs), more than 2.88 billion accounts enabled, 284.6 million accounts linked. RBI has registered 17 Account Aggregators. FIPs include banks, NBFCs, depositories, insurers and **GSTN**. FIUs must be entities "registered with and regulated by" a financial-sector regulator. | [DFS, Ministry of Finance](https://financialservices.gov.in/account-aggregator-framework), accessed 2026-11-10 | [verified] |
| As of 30 Sep 2026: 352.19 million accounts linked and 595.11 million consents fulfilled (both cumulative). In Sep 2026 alone, 14.16 million accounts were linked and 28.85 million consents fulfilled. | [Sahamati ecosystem dashboard](https://sahamati.org.in/?p=2028), accessed 2026-11-10 | [verified] |
| AA-enabled loans were reported at 8.4% of retail and MSME lending by value (11.8% by volume) in H2 FY26, and ₹3.82 lakh crore of lending in FY26. | [IANS report](https://ianslive.in/indias-account-aggregator-ecosystem-drives-rs-382-lakh-crore-loans-in-fy26--20260827133606) (search snippet only) | [unverified] |
| Each consent fixes a date range. Typical history is said to be 12–36 months. Lenders commonly ask for 6 or 12 months. | [Dealplexus explainer](https://www.dealplexus.com/blog/account-aggregator-consent-explained) (search snippet) | [unverified] |
| Whether company current accounts (non-individual) are shared over AA at scale | Not found | not found |
| Lender tools still take PDFs and scans. Cygnet Finalyze accepts "digital and scanned bank statements, passbooks, smartphone images" as well as AA JSON. Perfios says its analyser covers 4,000+ formats from 1,000+ banks, including scanned documents and net-banking pulls. | [Cygnet](https://cygnet.one/products/cygnet-finalyze/bank-statement-analysis); [Perfios](https://perfios.ai/ph/products/bank-statement-analyser), accessed 2026-11-10 | [verified] (vendor pages) |

### 2.2 Does AA remove the need for PDF parsing? (inference)

**For fresh retail and MSME underwriting: increasingly yes.** AA gives lenders structured, source-signed data for recent months, with the borrower's consent. In that segment, building another PDF parser is a weak bet. Perfios, FinBox and Cygnet already cover it.

**For forensic work on a red-flagged or defaulted borrower: mostly no.** Five reasons:

1. **Consent.** AA runs on the account holder's consent. A borrower under fraud review has little reason to give it. A promoter-linked counterparty has none.
2. **Who may receive data.** FIUs must be regulated by a financial-sector regulator (DFS, above). A CA or forensic firm is not. An RP is regulated by IBBI, which is not a financial-sector regulator in the AA sense (inference; check). So the forensic firm cannot pull AA data itself.
3. **History.** Forensic and IBC reviews look back years. IBC look-back windows run up to two years for related-party transactions (IBC s. 43; text not re-read here, [unverified]). The one bank RFQ found covered more than 11 years (§5.1). AA history depth depends on each FIP and is not guaranteed (unverified).
4. **Coverage.** The case file mixes the lender's own core-banking export, PDFs from other banks, closed accounts, co-operative bank passbooks and scans. AA covers 179 FIPs. That is not every bank or co-operative bank in India (inference from the FIP count).
5. **Evidence form.** The report must cite what the bank relied on. Under *Amit Iron* that material may go to the borrower (§1.2). A page in a statement the borrower produced, or an export certified by the bank, is easier to cite than an API payload. This still needs testing in interviews.

**What this means for product scope (recommendation).**

- Treat the **lender's own core-banking export (Excel/CSV)** and **digital PDFs from other banks** as the main inputs. Scanned statements and passbooks come second. Interviews must measure the actual mix (§7.2, Q4).
- Accept **AA JSON** as a third input. When a bank does hold AA data for the borrower (taken at onboarding or monitoring), it is the cleanest source.
- Do not compete on parser coverage. Perfios claims 4,000+ formats. MindDoc's edge has to be the **reconciliation check, the cross-document link and the citation**, not the number of layouts it can read.

## 3. Competition, verified

"Evidence-grade" below means the output is a set of findings, each tied to the source transactions or pages, that a
professional can review and sign. "Score" means the output is a risk score or flag list meant to feed a credit
decision. All vendor claims are the vendor's own words, not tested.

### 3.1 Indian lender tools (bank-statement analysis)

| Vendor / product | What it offers for statements and fund flows | Buyer | Evidence-grade or score? | Source | Tag |
|---|---|---|---|---|---|
| **Perfios** Bank Statement Analyser | ePDF, scanned and net-banking inputs. 4,000+ formats from 1,000+ banks. Built-in checks for "unauthorised ePDF manipulations". Multi-account analysis. Reports for credit managers. No mention of circular or related-party analysis on this page. | Banks and lenders ("over 1,000 institutions") | Score / credit report | [Perfios](https://perfios.ai/ph/products/bank-statement-analyser), accessed 2026-11-10 | [verified] |
| **Karza** | Acquired by Perfios in early 2022, reported at about ₹597 crore (~USD 80M) | — | — | [Inc42](https://inc42.com/buzz/exclusive-perfios-acquires-risk-management-startup-karza-for-80-mn); [PYMNTS](https://www.pymnts.com/acquisitions/2022/indian-b2b-credit-platform-perfios-adds-fintech-karza/) (search results) | [unverified] |
| **FinBox** BankConnect | Statement fraud checks: "over 150 built-in rule checks", PDF metadata and tampering checks, AA, upload and net-banking ingestion. A "cluster transaction intelligence" launch (body not read). | Digital lenders, onboarding | Score / fraud flags at onboarding | [FinBox fraud page](https://www.finbox.in/lp/bankstatementanalyser/fraud); [FinBox docs](https://docs.finbox.in/bank-connect/fraud) (search results; main product page returned 404) | [unverified] |
| **Cygnet Finalyze** | Digital, scanned, passbook, phone-image and AA JSON inputs. Flags circular transactions and tampering. Identifies "inter-account, related-party and duplicate transaction flows". Reconciles against bureau, GST and ITR data. Risk flags come "with the transactions behind each signal". Audit trail of extraction and review. Excel/JSON/XML outputs. | Banks, NBFCs, digital lenders, corporates | **Closest to evidence-grade** of the lender tools, but built for underwriting | [Cygnet](https://cygnet.one/products/cygnet-finalyze/bank-statement-analysis), accessed 2026-11-10 | [verified] |
| **IDfy** Transaction Intelligence Platform (TIP) | Blog of 15 Oct 2025: parses raw bank statements with LLMs, layers registry data, GST filings, sanctions lists and promoter networks. Detects round-tripping, hidden related parties (including via relatives), and name-variant shells (entity resolution). | Banks and NBFCs doing corporate or high-ticket lending | Investigation-style, aimed at lender due diligence | [IDfy blog](https://idfy.com/blog/this-business-isnt-paying-suppliers-its-paying-itself-lets-take-a-round-trip-of-its-ledgers), accessed 2026-11-10 | [verified] (blog, not product sheet) |
| **Novel Patterns** CART and HawkEye | CART: bank-statement analyser, fraud and anomaly detection including round-tripping flags, AA integration. HawkEye: early stress signals, cash-flow monitoring, SMA reporting. No forensic or fund-trail product named. | Banks, NBFCs, digital lenders | Score / monitoring | [novel-patterns.pages.dev](https://novel-patterns.pages.dev/) (official status unclear: no address or registration shown) | [unverified] |
| **ScoreMe** | Bank-statement, GSTR, ITR and financial-statement analysis for lenders. GST counterparty analysis fetched from GSTN (vendor blog). | Lenders | Score / underwriting | [ScoreMe blog](https://scoremesolutions.blogspot.com/2023/02/bank-statement-analyzer-revolutionizing.html) (search results) | [unverified] |
| **Signzy** | Bank-statement parsing (PDF, image, digital) inside an onboarding, AML and fraud-screening suite | Banks, NBFCs | Score / onboarding | [Signzy glossary](https://www.signzy.com/general-glossary/bank-statement-analysis) (search results) | [unverified] |
| **Lentra** | No bank-statement or forensic product page found | — | — | — | not found |
| **CRIF High Mark, Experian India, Equifax India** | No bank-statement analyser product found. They are credit bureaus. | — | — | search, 2026-11-10 | not found |

### 3.2 Indian fund-trail and investigation tools (missing from COMPETITIVE_ANALYSIS.md)

| Vendor / product | What it offers | Buyer | Source | Tag |
|---|---|---|---|---|
| **iAcuity Fintech — Fund Trail** | Described as a "hyper-automated forensic audit tool". Traces fund flows across multiple accounts from bank statements and ledgers. Pattern engine flags anomalies. Users named include law enforcement, banks (to monitor corporate loan fund use), forensic auditors and auditors. Interview dated 12 May 2023. | Police, banks, forensic auditors | [Voice&Data](https://www.voicendata.com/iacuity-helps-investigators-trace-the-flow-of-funds-across-multiple-accounts), read in full 2026-11-10 | [unverified] (press interview with the CEO) |
| **CypherSOL — CypherIQ / CypherTrace** | Listed as a forensic accounting and investigation platform for auditors, compliance teams and law enforcement. Windows desktop app. A "fund trail analyzer". | Auditors, police | [SaaSworthy listing](https://www.saasworthy.com/product/cypheriq) | [unverified] (aggregator) |
| **Terra Insight — TransactIQ** | Lender page mentions fund flow across months and related-party transactions, with AML and investigation teams as users | Lenders | [Terra Insight](https://www.terra-insight.com/bank-statement-analyzer/bandhan/) (search snippet) | [unverified] |
| **ICAI AI portal use case: "Forensic Audit Analysis – Bank Statements"** | A CA shows circular-flow detection, fund-trail mapping and red-flag lists across four accounts. The charts are published as a public claude.ai artifact, so a general LLM did at least the presentation. No vendor named. | CA practitioners | [ICAI AI portal](https://ai.icai.org/usecases_details.php?id=137), accessed 2026-11-10 | [verified] |

### 3.3 Global forensic and investigation tools

| Product | Relevant capability | Buyer | Evidence-grade? | Source | Tag |
|---|---|---|---|---|---|
| **Caseware IDEA** | Imports Excel, CSV, PDFs and "50+ accounting systems". SmartAnalyzer has 100+ tests (Benford, fuzzy duplicates). A separate Excel add-in, Extractly, extracts from PDFs. | Audit, internal audit, forensic teams | Workpaper-grade analytics on tables. No cross-document reasoning found. | [Caseware IDEA](https://caseware.com/products/idea) (search snippet); [reseller listing](https://platform.softwareone.com/product/caseware-idea/PCP-2313-6592) | [unverified] |
| **MindBridge** | "Continuous insight across 100% of financial transactions". Genpact partnership (17 Feb 2026) for full-population risk scoring, fraud detection, AI-led internal audit. No mention of documents, bank statements or India. | Audit firms, finance teams; Genpact clients | Scores | [MindBridge release](https://www.mindbridge.ai/news/mindbridge-announces-global-partnership-with-genpact-to-elevate-audit-analytics-and-risk-consulting/), accessed 2026-11-10 | [verified] |
| **i2 Analyst's Notebook** | Link and timeline analysis. Imports spreadsheets and text through import specifications. IBM support documents how to import financial transactions so links show counts and summed values. The 2022 user help is copyright N. Harris Computer Corporation. | Police, intelligence, bank FIU teams | Charts for analysts; evidence comes from the analyst | [i2 docs](https://docs.i2group.com/anb/10.1.1/anb_get_started.html); [IBM support](https://www.ibm.com/support/pages/node/716175) (search results) | [unverified] |
| **Valid8 Financial** (US) | Extracts and verifies bank statements, cheque images and deposit slips. Fund-flow visuals. "Every transaction is linked back to the sources uploaded." Markets "courtroom-ready" reports. | US government agencies, law enforcement, forensic accountants, attorneys | **Evidence-grade by design.** The closest global analogue to MindDoc. | [Valid8](https://valid8financial.com/state-agencies), accessed 2026-11-10 | [verified] (vendor page) |
| **Quantexa, Palantir, Nuix, Relativity** | Bank-scale entity-resolution and data platforms (Quantexa, Palantir); eDiscovery and investigation processing (Nuix, Relativity). Per COMPETITIVE_ANALYSIS.md. | Large banks, government, law firms | Platforms, not reports | Not re-checked this session | [unverified] |

### 3.4 Where the real gap is (inference)

The existing analysis says no one offers "an evidence-cited, cross-document fund-trail and related-party
investigation" for this buyer. **That claim is now weaker.**

- **Lender tools are moving into the space.** IDfy TIP (round-tripping, related parties, entity resolution with GST and registry data) and Cygnet Finalyze (related-party flows, GST/ITR reconciliation, flags with their transactions, audit trail) cover much of detectors D1–D3 and the cross-document idea. Their buyer is the lender, which is the party that pays for forensic work.
- **Indian fund-trail tools exist.** iAcuity Fund Trail names forensic auditors and banks as users. CypherSOL targets auditors. Neither was in the strategy docs.
- **Practitioners already use general LLMs.** The ICAI portal example shows a CA's forensic bank-statement review published as a general-LLM artifact. That is the substitute, and ICAI itself showcases it.
- **Globally, Valid8 has the evidence-grade, source-linked positioning** MindDoc wants, for US agencies.

**What still looks open (small).** No source found combines all of the following for the Indian forensic or RP buyer:
(a) a report deliverable shaped to the RBI process (show-cause notice, borrower disclosure under *Amit Iron*,
third-party redaction); (b) per-finding page-level citations with recomputed numbers; (c) running-balance
reconciliation as extraction QA; (d) on-premises deployment; (e) per-engagement pricing for a mid-size CA firm.
Each piece exists somewhere. The combination, aimed at this buyer, was not found. **The gap is small and closing.**
The defensible part is the *deliverable*, the forensic report and evidence bundle, not the analytics. Lender vendors
could add it if banks ask.

## 4. Who buys and why

### 4.1 Buyer and user map

**Bold** cells are sourced facts (tags in §1 and below). Plain cells are inference.

| Buyer / user | Trigger that forces the work | Who pays | Deliverable they must produce | Typical turnaround | Tools today |
|---|---|---|---|---|---|
| **PSU and private banks** (fraud-risk group, credit monitoring) | **EWS alert → red flag → external or internal audit** (§1.1). **Wilful-default review and end-use monitoring; "shall consider" a forensic audit above a Board-set threshold** (§1.3). | The bank | **Show-cause notice with complete transaction details, a reasoned order, and the audit report, which now goes to the borrower** (§1.1–1.2) | **Decision ordinarily within 180 days of CRILC reporting; at least 21 days for the borrower's reply.** Audit duration: not found. | **EWS integrated with core banking; a Data Analytics and MI Unit are required** (§1.1). Vendor EWS tools: not researched. |
| **NBFCs** (Upper and Middle Layer; Base Layer ≥ ₹500 crore) | Same pattern under the 2026 NBFC directions (unverified, §1.1). Wilful-default directions apply to NBFCs (verified, §1.3). | The NBFC | As for banks | Not found | Lender tools (Perfios, FinBox, Novel Patterns HawkEye) |
| **ARCs** | Acquire stressed loans. **The wilful-defaulter directions are addressed to ARCs** (§1.3). Their use of forensic audits: not found. | The ARC | Recovery and wilful-default case files | Not found | Not found |
| **CA and forensic-audit firms** (the ICP) | A bank or IBA mandate. **IBA panel categories split at ₹50 crore exposure** (unverified, §5). **About 800 agencies, CAs among them, are on the 2025–28 Agencies for Specialised Monitoring list** ([CAalley](https://caalley.com/news-updates/indian-news/banks-told-to-have-stricter-norms-for-eligibility-of-forensic-auditors), 25 Aug 2026, [unverified]) | The bank, at a capped fee (§5) | **A FAIS-compliant forensic report** (§1.4). Scope in one published bank RFQ: money trail and end-use, diversion, siphoning, related-party dealings, chain-of-transaction review, perpetrators, loss, "court evidence" (§5) | Set by the bank's contract (**required by RBI**, §1.1). Actual weeks: not found. | Excel, IDEA, statement converters, general LLMs (inference). **The ICAI AI portal shows a CA's version of this work published as a claude.ai artifact** (§3.2). |
| **Insolvency professionals** (RPs and liquidators) | **CIRP admission.** The RP must form an opinion on avoidance transactions (ss. 43, 45, 49/50, 66) by about day 75 and apply to the tribunal by about day 135 (unverified, §1.6) | CIRP costs, approved by the committee of creditors (inference) | An avoidance application backed by a transaction-audit report | **75 / 115 / 135-day marks** (unverified) | Transaction auditors hired by the RP (inference; not found as a rule) |
| **Statutory auditors** (every company audit) | CARO 2020 clause 3(ix)(c)–(d): report whether term loans were used for their purpose and whether short-term funds went to long-term uses ([KPMG CARO note](https://assets.kpmg.com/content/dam/kpmg/in/pdf/2022/03/caro-2020-enhanced-reporting.pdf), search snippet, [unverified]) | The company | A CARO clause in the audit report | Audit cycle | Audit software, Excel |
| **Internal audit** (fallback market) | Annual audit plan; procure-to-pay reviews | The company | Internal audit report | Audit cycle | Not re-researched here |
| **Credit and underwriting teams** | Loan application; renewal | The lender | A credit appraisal or score, not findings | Minutes to days | **AA plus Perfios, FinBox, Cygnet, ScoreMe** (§2–3) |

### 4.2 What this changes (inference)

1. **The bank is the economic buyer. The CA firm is the user and sub-buyer.** The bank sets the scope, the fee and the
   deadline. Software cost comes out of the firm's capped fee, unless the bank buys the tool for its fraud-risk group.
2. **There is a second payer: the RP.** IBC transaction audits recur with every CIRP and have hard day-marks. The
   strategy docs list RPs, but as a secondary target. They may be easier to sell to: one RP, one decision, costs
   approved by creditors. Test this in interviews (§7).
3. **There is a third, much larger and cheaper trigger: CARO 3(ix).** Every statutory audit has to say whether loan
   funds were used for their purpose. That is high volume and low price, closer to the fallback market's economics.
   It is a possible route to volume, not a forensic market.
4. **The decision on fraud is the bank's, through its committees.** The forensic report is evidence for that decision,
   and the 2026 text says a CA can be served a show-cause notice (§1.1). That favours tools that make the CA's work *defensible*
   over tools that make it *faster*.

## 5. Willingness to pay and pricing signals

Only published figures are given. Where a figure is ours, it is labelled **assumption**.

### 5.1 Published fees for forensic audits

| Signal | Figure | Source | Tag |
|---|---|---|---|
| J&K Bank e-RFQ for a forensic audit (ref. JKB/S&C/Forensic-Audit/2022-391, 26 Aug 2022). Maximum fee payable by exposure: | Up to ₹50 crore: up to **₹80,000**; ₹50–100 crore: ₹1,50,000; ₹100–250 crore: ₹2,50,000; ₹250–500 crore: ₹3,50,000; ₹500–1,000 crore: ₹4,00,000; above ₹1,000 crore: **₹5,00,000** | [TaxGuru reproduction](https://taxguru.in/chartered-accountant/empanelment-forensic-auditor-jammu-kashmir-bank.html), read in full 2026-11-10 | [unverified] (bank original not opened) |
| Same RFQ: period under review | 01 Jan 2002 to 31 Mar 2013, i.e. **more than 11 years** of transactions for one borrower group | same | [unverified] |
| Same RFQ: scope list (21 items) | Includes money trail and end-use, diversion, siphoning, related-party dealings, chain-of-transaction review, asset tracing, quantifying loss, "gathering court evidence" | same | [unverified] |
| IBA forensic-auditor empanelment | Separate categories for accounts up to and above ₹50 crore. Empanelment fee reported as ₹25,000 + 18% GST (₹29,500). | [pdicai.org notice](https://pdicai.org/rfpdetails.aspx?id=34048) (search snippet; page returned 404 when fetched) | [unverified] |
| SBI, high-value accounts (≥ ₹100 crore) | Fee is negotiated between bank and auditor, by complexity, time and resources | [ICMAI-hosted SBI notice, 2017](https://icmai.in/upload/pd/SBI-LHO-10012017.pdf) (search snippet; page returned 404) | [unverified] |
| PNB 2016–17 empanelment | Has a fee schedule; travel and lodging capped at 15% of the audit fee. Figures not seen. | [abcaus](https://abcaus.in/empanelment/pnb-forensic-auditor-ca-firms-empanelment-fy-201617.html/amp) (search snippet; 404 when fetched) | [unverified] |
| A 2024–26 bank forensic fee schedule | Not found | — | not found |
| IBC transaction-audit fees | Not found | — | not found |

### 5.2 Published prices for adjacent tools

| Product | Price | Source | Tag |
|---|---|---|---|
| Precisa (bank-statement analysis) | ₹100 per bank account (up to 12 statements), usage-based; a prepaid plan of ₹14,000/yr for up to 200 accounts | [Capterra listing](https://www.capterra.com/p/10038294/Precisa/) (search snippet) | [unverified] |
| Vyapar TaxOne (formerly Suvit) | ₹7,000/yr | COMPETITIVE_ANALYSIS.md [S28] (verified there, not re-checked) | [unverified] here |
| Perfios, FinBox, Cygnet, IDfy, Novel Patterns, ScoreMe, iAcuity, CypherSOL, Valid8 | Not public | vendor pages | not found |

### 5.3 What the signals mean (inference and assumptions)

- **The one published fee schedule caps a small-account forensic audit at ₹80,000.** It is a 2022 schedule from one
  bank. It may not be typical. But it is the only hard number found, and it is low.
- MARKET_SELECTION §9 proposes **₹25,000–60,000 per small case**. Against an ₹80,000 cap that is **31–75% of the whole
  fee**. That looks unaffordable (inference). The kill criterion in §10.4 ("fees make ≥ ₹25,000 per case implausible") is
  **close to triggered for accounts under ₹50 crore**, on this evidence.
- For large accounts (above ₹500 crore, fee up to ₹4–5 lakh in that schedule, or negotiated at SBI), a tool price of
  ₹25,000–50,000 is 5–12% of the fee. That is plausible if the tool saves real staff time. **Assumption:** firms
  will spend up to about 10% of an engagement fee on a tool that cuts the work by a third or more. Test it.
- Statement converters sell at about ₹100 per account (Precisa, unverified). MindDoc cannot charge for extraction.
  It can charge only for the findings and the report.
- **Recommendation.** Replace the flat per-case price with a **percentage-of-fee or exposure-band price**, and lead
  with accounts above ₹100 crore and with IBC transaction audits. Ask every interviewee for the fee on their last
  three engagements (§7).

## 6. Risks and kill criteria

### 6.1 Risks

| # | Risk | Evidence | Severity | Early signal |
|---|---|---|---|---|
| R1 | **Fees are capped too low to fund software** | The one published schedule caps a small-account forensic audit at ₹80,000 (§5.1) | **High** | Interviewees quote fees under ₹2 lakh for most engagements |
| R2 | **Banks keep the work in-house** | RBI allows "external audit or internal audit" (§1.1). Banks must run a Data Analytics and MI Unit. | High | Bank interviewees say most red-flag reviews go to internal audit |
| R3 | **Lender vendors add the forensic layer** | IDfy TIP and Cygnet Finalyze already do round-tripping, related parties and GST/ITR reconciliation for lenders (§3.1). Perfios is reported to serve most large lenders (COMPETITIVE_ANALYSIS [S59], secondary). | High | A vendor launches a "forensic report" or "fraud classification pack" for banks |
| R4 | **General LLMs are good enough** | The ICAI AI portal showcases a CA's forensic statement analysis whose output is a public claude.ai artifact (§3.2) | Medium–High | Interviewees say "we already do this in ChatGPT/Claude" and do not raise accuracy or confidentiality concerns |
| R5 | **Procurement and empanelment** | Firms are empanelled, not tools. If a bank buys the tool, RBI's IT-outsourcing direction applies, including India-only storage clauses (§1.5). The government has told banks to tighten auditor eligibility (CAalley, 25 Aug 2026, unverified). | Medium (sell via firms); High (sell to banks) | A bank's vendor-onboarding questionnaire |
| R6 | **Data access and confidentiality** | Engagement data belongs to the bank and borrower. DPDP duties start May 2027. India-only storage is likely to be passed down (§1.5). | High | Refusals at the commitment test (§7.2) |
| R7 | **Liability** | The 2026 directions name chartered accountants among those who can get a show-cause notice (§1.1). Two audit firms were reportedly removed from the ASM list after Enforcement Directorate observations (CAalley, unverified). A false related-party link from the tool could harm the signing CA. | High | Partners ask who carries liability for tool errors |
| R8 | **"No automated fraud verdict"** | The fraud decision is the bank's, by reasoned order, after notice (§1.1–1.2). FAIS places conclusions on the member (§1.4). | Constraint, not a risk, if respected | Any demand to output "fraud: yes/no". Refuse it. |
| R9 | **Long sales cycle** | Partner trust takes many meetings (MARKET_SELECTION §11). Bank procurement is slower still. | Medium | No pilot within 10 weeks of first interview |
| R10 | **Input mix differs from plan** | The J&K RFQ covered 11+ years for one group (§5.1). Long histories mean older, scanned, multi-bank data. AA covers recent data only (§2). | Medium | Interviewees report mostly scanned or physical records |

### 6.2 Kill criteria (proposed revision of MARKET_SELECTION §10.4)

Decide at week 10, after at least 20 of the 25 interviews and one retrospective run. **Switch to the fallback**
(procure-to-pay integrity for internal audit) if **any two** of these hold:

| # | Kill criterion | Measured by |
|---|---|---|
| K1 | Fewer than 4 of the 8 interviewed CA firms did **4 or more** lender forensic or IBC transaction audits in the last 12 months | Interview Q2 |
| K2 | The median reported fee for the last three engagements is **below ₹2 lakh**, **and** no firm names a tool budget of at least ₹25,000 per engagement | Q9–Q10 |
| K3 | At least 3 of the 5 bank interviewees say **most** red-flag reviews go to internal audit, not outside firms | Q-B2 |
| K4 | **No** firm will run a closed case in its own environment, even redacted | Commitment test |
| K5 | On the retrospective run, MindDoc does **not** beat a general-LLM baseline on recall or traceability by at least 20 percentage points | Pilot (§7.4) |

**Evidence that would make us switch immediately (any one):** a lender vendor launches a forensic-report product for
bank fraud-risk groups; three or more firms say engagement letters forbid any third-party software; or RBI or IBA
moves forensic audits to a centralised agency model that excludes tools chosen by the firm.

**Evidence that would strengthen ADR-0008:** IBC transaction audits turn out to pay ₹3 lakh or more on average; RPs
say they choose tools themselves; a bank fraud-risk head asks for an evidence bundle in the *Amit Iron* disclosure
format.

## 7. Customer-discovery plan (25 interviews + retrospective pilot)

### 7.1 Who to interview (n = 25, in 6 weeks)

| Segment | n | Exact roles | How to reach them |
|---|---|---|---|
| CA / forensic firms, 10–150 staff (ICP) | 8 | Forensic partner (signs reports) ×5; forensic manager (runs fieldwork) ×3 | IBA forensic panel and ASM empanelment lists that banks publish; ICAI regional-council FAIS and forensic CPE sessions; FAFD course alumni; LinkedIn ("forensic audit" + "IBA panel") |
| Insolvency professionals and transaction auditors | 5 | RP running a live CIRP ×3; CA firm that does RP-mandated transaction audits ×2 | IBBI public register of IPs; IIIPI (ICAI's IP agency) events; NCLT-bar contacts |
| Bank and NBFC side | 5 | PSU bank fraud-risk (FRMC) or Fraud Identification Committee officer ×2; credit-monitoring / EWS head ×1; private-bank fraud-risk ×1; NBFC risk head ×1 | Alumni networks; bank staff-college guest sessions; intros from the CA interviewees |
| ARC | 2 | Head of resolution or legal at an ARC | LinkedIn; intros via RPs |
| Internal audit (fallback check) | 2 | Head of internal audit at a mid-market company | IIA India chapter events |
| Learning only | 3 | Big 4 or boutique forensic director ×1; ex-employee of a lender-tool vendor (Perfios / IDfy / Cygnet) ×1; lawyer who has defended a borrower in a fraud classification ×1 | LinkedIn; authors of the *Amit Iron* notes (law-firm knowledge pages) |

Do not pitch before the last question. Record answers in a shared sheet with one row per interviewee and one column per
assumption below.

### 7.2 Question guide (tests the riskiest assumptions)

| Assumption | Question (past behaviour, not opinion) | Pass | Fail |
|---|---|---|---|
| **A1. Frequency** | Q1 "Walk me through the last lender forensic or transaction audit you closed." Q2 "How many did your firm do in the last 12 months? Split them by bank fraud review, wilful-default or end-use mandate, IBC transaction audit, and other." | ≥ 4 of 8 firms did ≥ 4 a year | K1 |
| **A2. Work goes outside** (bank side) | Q-B1 "Of the accounts red-flagged last year, roughly how many went to an outside auditor?" Q-B2 "What decides internal versus external?" | ≥ 3 of 5 say most go outside | K3 |
| **A3. Time sits in statements and trails** | Q3 "On that last case, how many person-hours went into getting, converting and reconciling statements? Into tracing counterparties? Into writing?" Ask for timesheets if they exist. | Statements + tracing ≥ 40% of hours, and ≥ 60 person-hours per case | < 20% or < 25 hours |
| **A4. Input mix** | Q4 "What did the data look like: the bank's own core-banking export, PDFs from other banks, scans, passbooks, AA data? How many years?" | Digital or exportable data in ≥ 60% of cases | Mostly paper or scans (re-scope) |
| **A5. Deliverable and disclosure** | Q5 "Since *Amit Iron*, has a report of yours gone to the borrower? Was any finding challenged? On what grounds?" Q6 "What did the bank's committee ask you to redo last time?" | ≥ 3 of 13 (firms + banks) cite traceability or evidence gaps as a real problem | Nobody has seen a challenge |
| **A6. Data access** | Q7 "What does your engagement letter say about software and storage? Could a tool run on your own laptop or server on a closed case?" | ≥ 3 firms say yes, on-premises | K4 |
| **A7. Who signs and pays** | Q8 "Who in the firm approves a new tool? Has a bank ever paid for, or banned, a tool you used?" | A named budget owner in ≥ 5 firms | No owner; bank must approve every tool |
| **A8. Budget** | Q9 "What was the fee on your last three engagements, and how was it set?" Q10 "What do you pay a year for software and data today?" | Median fee ≥ ₹2 lakh, or tool spend ≥ ₹25,000 per case | K2 |
| **A9. Substitutes** | Q11 "Have you used a general LLM, iAcuity, IDEA or a lender tool on this work? What happened?" | They name accuracy, traceability or confidentiality limits | "The LLM does it fine" from ≥ 4 firms (R4) |
| **A10. Value** (last, after the pitch) | Q12 "If a tool linked every finding to its page and recomputed every number, what would that be worth on your last case? Yes or no at ₹X?" | ≥ 3 firms say yes at the tested price | All say no |

**Commitment test** (close every CA and RP interview with it): "Can we run MindDoc on one closed case, inside your
environment, next month, and compare it with your final report?"

### 7.3 Overall pass / fail

- **Pass (keep ADR-0008):** A1, A3, A6 and A8 pass, **and** ≥ 2 firms accept the commitment test.
- **Re-scope (keep the market, change the buyer or the price):** A1 passes for IBC transaction audits but fails for
  bank forensic audits, or A8 passes only for large accounts. Then target RPs, or accounts above ₹100 crore.
- **Fail (move to the fallback):** any two of K1–K5 (§6.2).

### 7.4 Retrospective pilot on a closed case

| Step | Design |
|---|---|
| Case choice | One forensic or transaction audit closed at least 12 months ago, with a final report the bank or RP accepted. Prefer a case with 3+ bank accounts and related-party findings. |
| Data handling | Option A (preferred): the firm runs MindDoc on its own machine in offline mode with a local LLM. MindDoc's team never sees raw data. Option B: the firm pseudonymises names, account numbers, PAN and GSTIN with a consistent key held only by the firm. Option C: if neither is allowed, build a **synthetic replica** that copies the case's structure (accounts, counterparties, schemes, period) with invented values, and use the firm's final report as the answer key. |
| Baseline first | Before any MindDoc output is shown, record the original effort from timesheets: hours on extraction, reconciliation, tracing and drafting. |
| Runs | (1) MindDoc, operated by a manager who did not work on the case. (2) A general-LLM baseline on the same files, by the same manager, with a fixed prompt and time box. |
| Measures | Recall of the final report's findings (target ≥ 90%); precision of the top 25 flags as rated by the partner (≥ 70%); share of accepted findings with a working page citation (100%); numbers that fail recomputation (0); hours to a partner-reviewed draft against the baseline (≥ 50% less); a **contestability review**, in which a second partner or a lawyer tries to challenge five findings from the evidence bundle alone. |
| Pass | The KPIs above are met, **and** MindDoc beats the LLM baseline by ≥ 20 points on recall or traceability (K5), **and** the partner gives a yes or no at a stated price for the next live case. |
| Safeguards | NDA in place; the firm confirms its engagement letter allows the run; data deleted on close with a certificate; nothing in the pilot is labelled "fraud". |

## 8. Changes recommended to ADR-0008 / MARKET_SELECTION.md

These are proposals only. Neither file has been edited.

**ADR-0008**

1. Keep the status at **Proposed**. Add one line: "Commercially unproven. Pending the 25 interviews and retrospective
   pilot in D_MARKET_RESEARCH §7."
2. Widen the decision to name **two buyers for one workflow**: CA forensic firms on bank mandates, and **RPs and their
   transaction auditors** in IBC cases. Name the **bank fraud-risk group** as the economic buyer behind the CA firm.
3. Add to Consequences: **third-party redaction** in report exports (after *Amit Iron* para 126(e)); **India-only
   storage** by default; **inputs led by core-banking exports, digital PDFs and AA JSON**, with scans second.
4. Replace the "Revisit when" line with the revised kill criteria K1–K5 (§6.2).

**MARKET_SELECTION.md**

5. **§2.1 and §4, regulation.** Say that RBI requires an "external audit or internal audit" of red-flagged accounts,
   not a forensic audit as such. Cite the **2026** directions (RBI MD id 13641 for banks; the NBFC 2026 directions).
   Add the **wilful-defaulter direction of 30 Jul 2024** as the main anchor for end-use and diversion work. Its para 18
   says lenders "shall consider" a forensic audit above a Board threshold.
6. **[S6]/[S7].** Replace the secondary sources with the *Amit Iron* judgment itself (2026 INSC 323, paras 121 and
   126). Remove the "read before quoting" note in §12.
7. **§2.1 WTP score.** Add the J&K Bank fee schedule (₹80,000 cap up to ₹50 crore; ₹5 lakh above ₹1,000 crore). On this
   evidence WTP is **3, not 4**. Rescored, forensic falls from 4.05 to **3.85**. Procurement stays at 3.70. The lead
   is now about 0.15, inside the margin of judgement. Say so.
8. **§2.1 competition score.** Add IDfy TIP, Cygnet Finalyze, iAcuity Fund Trail, CypherSOL and Novel Patterns
   HawkEye. A case can be made for 2, not 3. If both WTP and competition drop by one point, forensic scores **3.70**,
   level with procurement. The ranking then rests on the interviews, which is where it should rest.
9. **§9, pricing.** Drop the flat ₹25,000–60,000 small-case price. Test an **exposure-band or percentage-of-fee price**
   (assumption: up to about 10% of the fee), led by accounts above ₹100 crore and by IBC transaction audits.
10. **§5, ICP.** Add a qualifier: "on a bank's Agencies for Specialised Monitoring list (about 800 agencies for 2025–28,
    unverified)". Add RPs as a second ICP.
11. **§10, interviews.** Replace the 10 questions with the assumption-keyed guide in §7.2. Add an ARC segment and a
    borrower-side lawyer.
12. **§11, risks.** Add R2 (banks keep the work in-house), R3 (lender vendors add the forensic layer) and the CA's own
    exposure to a show-cause notice (R7).
13. **§12, open questions.** Add: the share of red-flag reviews that go outside; current fee schedules from 2024–26
    bank RFQs; the IBC transaction-audit fee range; whether company current accounts are shared over AA; whether
    DPDP s. 17(1)(f) covers red-flagged but not defaulted accounts.
14. **COMPETITIVE_ANALYSIS.md §0.** Replace "No one found in this research offers…" with: "Each part exists (lender
    tools with related-party and round-trip flags; Indian fund-trail tools; a US evidence-grade platform). The
    combination aimed at Indian forensic and RP buyers was not found. The gap is small and closing."

---

## Appendix: items searched for and not found

- A 2024–26 bank fee schedule for forensic audits.
- Fees for IBC transaction audits.
- The share of red-flagged accounts sent to outside auditors.
- The typical time a forensic audit takes.
- A rule requiring RPs to hire an outside transaction auditor.
- Whether company current accounts are shared over AA at scale.
- Bank-statement or forensic products from Lentra, CRIF High Mark, Experian India or Equifax India.
- Published prices for any of the lender or forensic tools named in §3.
- The full text of FAIS 320 and FAIS 510. The ICAI compendium was not reachable.

**Sources not reachable this session:** the pdicai.org IBA notice, the SBI notice and the PNB notice (all 404); the
iAcuity press release on ThePrint (bot check); FinBox's main product page (404); the ICAI FAIS Implementation Guide
(truncated download). Where one of these is used, it is tagged [unverified] with a note that the page could not be
opened.
