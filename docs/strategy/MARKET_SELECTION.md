# MindDoc AI — Market Selection

*Version 1.0 · 2026-11-10 · Companion to [`COMPETITIVE_ANALYSIS.md`](COMPETITIVE_ANALYSIS.md)*

**Conventions**

- `[S#]` refers to the Sources table at the end. **P** = primary source; **S** = secondary source.
- **Hypothesis** marks anything that is a judgement or a number to be tested. It is not a finding.
- No market sizes are given, because no credible India-specific size for these niches was found. Regulator and
  industry data are used as **evidence of pain**, not as addressable-market figures.
- The time and cost of today's manual workflows were **not found in any credible source** for any of the six
  markets. Measuring them is the first job of the validation plan (§10).

---

## 0. Recommendation in one screen

| | |
|---|---|
| **Primary wedge (score 4.05 / 5)** | **Forensic review of borrower fund diversion and related parties.** The buyer is the mid-size Indian CA/forensic firm that lenders hire for forensic audits of red-flagged accounts, and that insolvency professionals hire for avoidance-transaction audits. The segment sits inside market (1), financial audit and forensic accounting. |
| **Fallback (score 3.70 / 5)** | **Vendor and invoice integrity review in the procure-to-pay cycle** (duplicate and look-alike vendors, invoice–PO–GRN–contract mismatches, undisclosed related-party vendors). Buyers are internal-audit heads at mid-market Indian companies and the CA firms they outsource internal audit to. It reuses about 80% of the primary build (*estimate*). |
| **Why this wedge** | (a) Large, regulator-documented pain. Advances (loan) frauds were 8,640 cases and ₹40,774 crore in FY26 [S2]. Avoidance-transaction applications under the IBC cover about ₹3.9 lakh crore, of which about ₹7,930 crore had been clawed back [S8]. (b) A legal tailwind for *evidence-cited* reports: borrowers must ordinarily get the forensic report and the material relied upon [S5][S6][S7]. (c) The incumbents analyse ledgers, not multimodal Indian documents (see COMPETITIVE_ANALYSIS §4). (d) The work exercises every MindDoc differentiator. (e) The buyers are a small, identifiable professional group a solo founder can reach. |
| **First measurable workflow** | *Loan end-use and related-party fund-trail review for one borrower.* Inputs: bank statements, sanction letter, Tally ledgers, invoices, GST returns, stock statements, MCA director data. Output: an evidence-cited findings register, a fund-flow graph and a draft report. **KPIs:** cut the time to reach partner-reviewed draft findings by ≥ 50% against the firm's own baseline; recall ≥ 90% of the firm's final-report findings on a retrospective case; 100% of accepted findings with resolvable page-level citations. |
| **Most dangerous competitors** | Caseware IDEA, Perfios, MindBridge (+ Genpact). Day-one substitute: Excel + IDEA + a general LLM. |
| **Note on the roadmap** | This **revises** `docs/ROADMAP.md` §2, which recommended a KYC/compliance pack. KYC is the most crowded market in this analysis (Perfios, IDfy, Signzy) and the hardest for a solo founder to sell into. The underlying engine work in the roadmap (cross-document contradictions, entity resolution, review queue, governed actions) carries over unchanged. |

---

## 1. Method and scoring rubric

### 1.1 Criteria, weights and what each score means

| Criterion | Weight | 1 = | 3 = | 5 = |
|---|---|---|---|---|
| **Pain severity**: regulator/industry evidence of losses, deadlines, consequences | 20% | Inconvenience | Recurring cost, moderate consequences | Large documented losses plus regulatory or legal consequences |
| **Willingness to pay** (as far as it can be inferred) | 20% | Buyer's tools cost ₹ thousands/yr | Departmental budgets, ROI must be argued | Budget exists, value per case is high, buyer already pays for tools or services |
| **Competitive intensity** (inverted: 5 = most room) | 15% | Many funded, focused competitors with distribution | Incumbents with clear gaps | Little focused competition |
| **Data accessibility for a demo** | 15% | Only real sensitive data would be credible | Synthetic data possible with effort | Public datasets plus easy synthetic generation |
| **Solo-founder feasibility**: reach, sales cycle, procurement, security review | 15% | Enterprise or regulated procurement, 9–18 month cycles | Professional-firm buyers, pilots possible | Self-serve or very short cycles |
| **Technical showcase value**: cross-document contradictions, entity resolution, graph, temporal reasoning, visual grounding | 15% | Uses 1–2 differentiators | Uses 3–4 | Uses all 5 deeply |

Scores are integers from 1 to 5. They are the author's judgement from the evidence in §2 and are open to challenge.
§3.2 shows how much the ranking moves when the weights change.

---

## 2. Market-by-market assessment

### 2.1 Financial audit and forensic accounting (CA firms, internal audit, Big 4 forensic)

| Dimension | Assessment |
|---|---|
| **Who feels the pain** | Forensic partners and managers at CA firms on bank or IBA forensic panels [S11]; insolvency professionals (RPs/liquidators) and the transaction auditors they hire; bank fraud-risk management groups; internal auditors; Big 4 forensic teams. |
| **Current workflow** | Collect bank statements (often scanned), books (Tally exports or PDFs), invoices, GST returns, stock statements and loan files. Re-key and reconcile transactions in Excel or IDEA. Identify counterparties by hand and look up directors in MCA data. Trace end-use of loan disbursements. Test for round-tripping and undisclosed related parties. Draft findings with annexures. Under RBI's 2024 directions, banks must decide on a red-flagged account within 180 days, often using external audits [S3][S4]. Under the IBC, auditors test transactions for preferential, undervalued, fraudulent and extortionate character (sections 43, 45, 49, 50, 66). **Time per engagement: not verified.** |
| **Evidence of pain** | Banks reported 10,114 frauds worth ₹48,021 crore in FY26 [S1]. Advances frauds were 8,640 cases and ₹40,774 crore, about 85% of the value [S2]. Caveat: FY26 includes 314 older cases (₹30,199 crore) re-reported after the Supreme Court's 2023 ruling [S1]. IBC avoidance applications: 1,442 covering about ₹3,89,964 crore filed; 379 cases (₹66,919 crore) disposed; about ₹7,930 crore clawed back (DFS Secretary, IBBI Annual Day, 1 Oct 2025) [S8]. By Sep 2024 the figure was 338 settled with about ₹7,516 crore clawed back [S9]. Globally, the ACFE estimates organisations lose about 5% of revenue to occupational fraud [S15]. Public Indian case example: SEBI's interim order on Gensol Engineering (Apr 2025) described loan funds routed through a vehicle supplier back to promoter-linked entities, and a forensic audit was ordered [S75] (secondary report; read the order on sebi.gov.in). |
| **Competitors** | Caseware IDEA, MindBridge (+ Genpact), Diligent/ACL, EY DATA and other Big 4 in-house tools, Nuix, Indian CA-AI tools (CORAA, AssureAI, Irame.ai, AuditCue). See COMPETITIVE_ANALYSIS §2.1. |
| **Regulatory / data constraints** | ICAI Forensic Accounting and Investigation Standards (FAIS), mandatory for ICAI members since 1 Jul 2023 [S10]. RBI Master Directions on Fraud Risk Management, 2024 (early-warning signals, red-flagged accounts, 180-day timeline) [S3][S4]. *SBI v. Rajesh Agarwal* (27 Mar 2023) read natural justice into fraud classification [S5]. *SBI v. Amit Iron* (reported Apr 2026): no personal hearing is required, but borrowers must ordinarily get the audit reports and material relied upon [S6][S7]. Courts are checking forensic reports against statutory standards and auditor qualifications [S78]. Data is confidential to the bank and borrower under engagement letters. DPDP applies to personal data in statements (promoters, employees); the firm is the data fiduciary and MindDoc the processor; substantive DPDP duties are phased in to about May 2027 [S65][S66]. |
| **Demo data without customer data** | Good. Synthetic generation of bank statements, Tally-style ledgers, invoices, GST summaries and stock statements with **seeded schemes** modelled on public typologies (SEBI/IBBI orders, SEC AAERs). Public layouts for invoices (DocILE [S76]). The Enron email corpus can be used if email evidence is added later (not re-verified here). |
| **Buyer and willingness to pay** | The forensic partner pays out of engagement margin. Banks pay the forensic fee; the IBA panel has separate categories for accounts up to and above ₹50 crore [S11]. **Fee levels per engagement: not verified.** Probably the main WTP risk. |
| **Sales cycle for a solo founder** | Moderate. About 4.23 lakh ICAI members [S12] and about 99k firms [S13], but the forensic sub-segment is small and identifiable (panel lists, ICAI forensic CPE events, IBBI's public register of insolvency professionals). The firms are partner-led, so decisions are quick once there is trust. Confidentiality is the main brake. Mid-size CA firms are expected to adopt AI by partnering with platforms rather than building [S14]. |
| **Differentiator fit** | **5/5.** Cross-document contradictions (stock statement vs GST turnover vs bank credits); entity resolution (vendors sharing directors, addresses, accounts); graph (fund trails, cycles); temporal (disbursement → outflow within N days, back-dating); visual grounding (page-level citations demanded by the Amit Iron disclosure standard). |
| **Global relevance** | High. The same fund-trail and avoidance-transaction pattern applies to litigation support and insolvency practitioners elsewhere; ACFE data is global [S15]. |
| **Scores** | Pain 5 · WTP 4 · Competition 3 · Data 4 · Solo 3 · Showcase 5 → **4.05** |

### 2.2 GST / tax notice and compliance handling

| Dimension | Assessment |
|---|---|
| **Who feels the pain** | MSME owners and finance staff; CA practices that handle notices for many clients; in-house tax teams at enterprises. |
| **Current workflow** | Download the notice from the GST portal; reconcile GSTR-1/3B/2B and books; collect invoices and e-way bills; draft a reply with legal citations; track deadlines across GSTINs. **Time per notice: not verified.** |
| **Evidence of pain** | FY25: 25,009 fake firms detected, which passed about ₹61,545 crore of fraudulent ITC (PTI report of official data) [S20]. Q1 FY26: ₹15,851 crore of fraudulent ITC and 3,558 fake firms [S21]. One practitioner site claims about 1.14 lakh ASMT-10 scrutiny notices in FY24 [S22] (**unverified, no official source found**). The most common trigger is GSTR-3B vs 2B ITC mismatch (practitioner sources). |
| **Competitors** | Clear, Enterslice, GST Reply AI, TaxTMI, AI Accountant, FnShift, Trackase, ICAI-listed NoticeAI, Vyapar TaxOne (bookkeeping) [S23]–[S29]. Very crowded. |
| **Regulatory / data constraints** | CGST Act and Rules. Replies are filed by the taxpayer or professional, and wrong citations carry penalty risk. Automating portal access means handling taxpayer credentials and OTPs, which is a security and liability burden. |
| **Demo data** | Good. Notice formats and statutes are public; GSTR data can be generated synthetically. |
| **Buyer and willingness to pay** | Low per unit. Tools for CA practices sell at about ₹7,000/yr [S28]; Clear's GST health check is free [S23]. |
| **Sales cycle** | Short (CA practices, SMEs). |
| **Differentiator fit** | 2/5. Mostly tabular reconciliation plus LLM drafting, which is a commodity. Little use for the graph or for visual grounding. |
| **Global relevance** | Low (India-specific; VAT analogues elsewhere). |
| **Scores** | Pain 4 · WTP 2 · Competition 1 · Data 4 · Solo 4 · Showcase 2 → **2.85** |

### 2.3 Insurance claims investigation (health / motor fraud)

| Dimension | Assessment |
|---|---|
| **Who feels the pain** | Claims investigators and fraud-monitoring units at insurers; TPAs; the special investigation agencies insurers hire. |
| **Current workflow** | Review discharge summaries, bills, prescriptions, lab reports and police/FIR or surveyor reports; field verification; check hospital and network patterns. **Time per claim: not verified.** |
| **Evidence of pain** | BCG–Medi Assist estimate: ₹8,000–10,000 crore a year of health-insurance leakage from fraud, waste and abuse, with risk concentrated in claims below ₹2.5 lakh [S30] (industry estimate co-authored by an interested party). IRDAI's Insurance Fraud Monitoring Framework Guidelines 2025 apply from 1 Apr 2026. They require a fraud monitoring committee and unit, red-flag indicators, and participation in the Insurance Information Bureau's technology framework [S31][S32]. |
| **Competitors** | Medi Assist MAtrix (adopted by Star Health), MediBuddy Sherlock, Consint.AI, in-house insurer AI, the IIB platform [S33]–[S35]. |
| **Regulatory / data constraints** | Health data is highly sensitive. IRDAI outsourcing and records rules apply (not verified here). DPDP. Insurer infosec reviews. |
| **Demo data** | Weak for India. Synthea is US-centric and Kaggle motor-fraud data is tabular (neither re-verified here). Realistic Indian hospital bills would have to be synthesised from scratch. |
| **Buyer and willingness to pay** | Insurers and TPAs have budgets, and the regulatory mandate creates urgency. |
| **Sales cycle** | Long, enterprise-scale and regulated. Hard for a student founder. |
| **Differentiator fit** | 4/5. Contradictions between bill, discharge summary and prescription; provider networks; forgery cues. |
| **Global relevance** | High (insurance fraud is global). |
| **Scores** | Pain 5 · WTP 4 · Competition 3 · Data 2 · Solo 2 · Showcase 4 → **3.45** |

### 2.4 Legal investigation and contract intelligence

| Dimension | Assessment |
|---|---|
| **Who feels the pain** | Law-firm associates (due diligence, disputes), in-house counsel, investigators. |
| **Current workflow** | Manual review of contracts and discovery sets; issue lists; chronologies. **Time: not verified.** |
| **Evidence of pain** | Real but not regulator-quantified in India. Strong investor demand: Harvey (reported USD 11B valuation, India office) [S36][S37]; Luminance USD 75M [S38]; SpotDraft USD 54M + 8M [S39][S40]; Indian start-ups raising seed rounds [S41]. |
| **Competitors** | Harvey, Luminance, Kira/Litera, SpotDraft, Relativity, Nuix, Indian legal AI start-ups. |
| **Regulatory / data constraints** | Privilege and client confidentiality; Bar Council rules on practice (software is fine, legal advice is not). |
| **Demo data** | Excellent. CUAD (510 contracts, 41 clause categories, CC BY 4.0) [S77]; SEC EDGAR exhibits; Indian judgments. |
| **Buyer and willingness to pay** | High at top firms globally; moderate in India. |
| **Sales cycle** | Slow, conservative and relationship-driven, against heavily funded competitors. |
| **Differentiator fit** | 3/5. |
| **Global relevance** | High, but saturated. |
| **Scores** | Pain 3 · WTP 3 · Competition 1 · Data 5 · Solo 2 · Showcase 3 → **2.85** |

### 2.5 Procurement / vendor and third-party risk

| Dimension | Assessment |
|---|---|
| **Who feels the pain** | Internal-audit heads, CFO/controllers, AP managers at mid-market companies; CA firms doing outsourced internal audit. |
| **Current workflow** | Sample-based P2P audits: vendor-master review, three-way match on samples, duplicate-payment queries in ERP or Excel, vendor due diligence on MCA/GST portals. **Time: not verified.** |
| **Evidence of pain** | APQC benchmarks put duplicate or erroneous disbursements at about 0.8% of annual disbursements for top performers [S17][S18], with a reported median of about 1.5% and bottom performers at about 2.0% (APQC 2024 via a vendor blog) [S19]. ACFE 2024: billing schemes were 22% of occupational-fraud cases with a median loss of USD 100,000 [S16]. |
| **Competitors** | AppZen (USD 180M Series D, Sep 2025) [S68], Oversight, Rossum (duplicate detection, master-data matching) [S56], Docsumo (cross-document validations) [S57], EY DATA (vendor authentication) [S70]. |
| **Regulatory / data constraints** | Mostly business data owned by the client company, so consent is simpler than in forensic or insurance work. ERP access and integration needed. DPDP applies to sole-proprietor vendors and employee data. |
| **Demo data** | Good. Synthetic P2P generator; DocILE invoice layouts [S76]; seeded duplicate rates from APQC ranges. |
| **Buyer and willingness to pay** | Good. ROI can be stated in recovered cash. |
| **Sales cycle** | Moderate. Mid-market companies, with IT/ERP gatekeepers. |
| **Differentiator fit** | 4/5. Entity resolution of vendors (name, PAN, GSTIN, bank account), invoice–PO–GRN–contract contradictions, temporal patterns, invoice visual grounding. A fund-flow graph matters less. |
| **Global relevance** | High (AppZen and Oversight show a global category). |
| **Scores** | Pain 4 · WTP 4 · Competition 3 · Data 4 · Solo 3 · Showcase 4 → **3.70** |

### 2.6 Bank/NBFC credit underwriting and KYC document verification

| Dimension | Assessment |
|---|---|
| **Who feels the pain** | Credit operations, underwriting and onboarding teams at banks, NBFCs and fintech lending service providers. |
| **Current workflow** | Document collection; bank-statement analysis; KYC/video KYC; tamper checks; credit decisioning. Mostly automated through vendors already. |
| **Evidence of pain** | Advances frauds make up about 85% of bank fraud value in FY26 [S2]. RBI Digital Lending Directions (8 May 2025) and KYC amendments in 2025 add obligations [S63][S64]. |
| **Competitors** | Perfios, IDfy (more than 60M verifications/month, company-reported), Signzy, HyperVerge, Ocrolus (US) [S52][S59]–[S62]. Entrenched. |
| **Regulatory / data constraints** | RBI KYC Master Direction; Digital Lending Directions; RBI IT outsourcing expectations and data-localisation rules (not verified here); Aadhaar handling restrictions. **Generating realistic replicas of Indian government IDs for demos is legally risky and should be avoided.** |
| **Demo data** | Medium. Synthetic bank statements are fine; ID documents are problematic. |
| **Buyer and willingness to pay** | High aggregate budgets, but pricing is per API call against scaled vendors. |
| **Sales cycle** | Very hard. Bank procurement, infosec, regulator-aligned audits. |
| **Differentiator fit** | 3/5. Tamper detection and consistency checks; little graph or temporal depth at onboarding. |
| **Global relevance** | High, but saturated. |
| **Scores** | Pain 4 · WTP 5 · Competition 1 · Data 3 · Solo 1 · Showcase 3 → **3.00** |

---

## 3. Scoring

### 3.1 Base weights

| Market | Pain (20%) | WTP (20%) | Room vs competition (15%) | Demo data (15%) | Solo feasibility (15%) | Showcase (15%) | **Weighted** | Rank |
|---|---|---|---|---|---|---|---|---|
| (1) Forensic accounting: borrower fund-diversion focus | 5 | 4 | 3 | 4 | 3 | 5 | **4.05** | **1** |
| (5) Procurement / vendor & invoice integrity | 4 | 4 | 3 | 4 | 3 | 4 | **3.70** | **2** |
| (3) Insurance claims investigation | 5 | 4 | 3 | 2 | 2 | 4 | 3.45 | 3 |
| (6) Credit underwriting / KYC | 4 | 5 | 1 | 3 | 1 | 3 | 3.00 | 4 |
| (2) GST notice handling | 4 | 2 | 1 | 4 | 4 | 2 | 2.85 | 5 (tie) |
| (4) Legal investigation / contracts | 3 | 3 | 1 | 5 | 2 | 3 | 2.85 | 5 (tie) |

### 3.2 Sensitivity: does the ranking survive different weights?

| Weighting scheme | Forensic | Procurement | Insurance | Credit/KYC | GST | Legal |
|---|---|---|---|---|---|---|
| Base (above) | **4.05** | 3.70 | 3.45 | 3.00 | 2.85 | 2.85 |
| Equal weights (1/6 each) | **4.00** | 3.67 | 3.33 | 2.83 | 2.83 | 2.83 |
| Commercial only (Pain 25, WTP 25, Competition 20, Data 10, Solo 20; showcase 0) | **3.85** | 3.60 | 3.45 | 2.95 | 2.90 | 2.60 |
| Solo-heavy (Solo 30%, others 14% each) | **3.84** | 3.56 | 3.12 | 2.54 | 3.02 | 2.70 |

The top two hold under every scheme. The gap between them (about 0.3) rests on two judgement calls: pain (5 vs 4)
and showcase value (5 vs 4). **If interviews show that forensic engagements are rare, or that fees are tightly
capped, or that firms will not share case data, procurement takes first place.** This is written into the kill
criteria in §10.4.

---

## 4. Recommendation

**Primary wedge: forensic review of borrower fund diversion and related parties, for Indian CA/forensic firms.**

1. **The pain is regulator-documented and growing in value.** Advances frauds were about ₹40,774 crore in FY26 [S2].
   IBC avoidance claims are about ₹3.9 lakh crore filed, but only about ₹7,930 crore has been clawed back [S8]. That
   gap points to the evidentiary difficulty of these cases.
2. **The law now rewards exactly what MindDoc is built for.** Fraud classification needs natural justice [S5], and
   borrowers must ordinarily see the material relied upon [S6][S7]. A report where every finding links to a page
   region and a recomputed number is easier to defend.
3. **There is a gap between the incumbents.** GL analytics (IDEA, MindBridge) do not read Indian documents as
   evidence. Lender tools (Perfios) serve credit, not forensic narrative. Big 4 tools are not sold to mid-size firms.
4. **A solo founder can reach the buyers.** It is a professional community with public panels, CPE events and an
   IBBI register, partner-led decisions, and pilots that can run on closed cases.
5. **It is the strongest portfolio story.** Multimodal extraction, entity resolution, graph and temporal reasoning,
   verification with abstention, human-in-the-loop review, and rigorous evaluation on seeded synthetic cases.

**Fallback: vendor and invoice integrity review in procure-to-pay**, for internal audit at mid-market companies.
The client owns the data, so access is easier, and ROI is stated in recovered cash. The engine overlaps heavily:
the same ingestion, entity resolution, contradiction detectors and evidence viewer. Only the detectors and report
templates change.

**Explicitly not now:** KYC/credit (too crowded, hardest procurement), GST notices (commodity, low WTP), legal (funded
incumbents), insurance (good market, wrong stage: enterprise sales and sensitive data). Insurance should be revisited
after two paying forensic customers.

---

## 5. Ideal customer profile (ICP)

| Attribute | ICP (primary wedge) |
|---|---|
| Firm type | Indian CA / forensic advisory firm, about 10–150 professionals, with a named forensic or investigation practice |
| Qualifier (at least one) | On the IBA forensic-auditor panel or bank-specific forensic panels [S11]; partners who are IBBI-registered insolvency professionals or regular transaction auditors for RPs; regular lender-mandated end-use or stock audits |
| Volume | At least 4 forensic or transaction-audit engagements a year (**hypothesis to validate**) |
| Current tooling | Excel, Tally, possibly IDEA; bank-statement converters; general LLM chat; no in-house data-science team |
| Geography | Mumbai, Delhi NCR, Bengaluru, Chennai, Kolkata, Ahmedabad, Hyderabad, Pune |
| Willingness | A partner who will run one closed case's documents through MindDoc in the firm's own environment and record baseline effort |
| Disqualifiers | Big 4 and large networks (learning interviews only); firms doing only statutory or tax work; firms that cannot let any software touch engagement data |

---

## 6. Personas

| | **P1: Forensic Partner ("Meera")**, economic buyer | **P2: Forensic Manager ("Arjun")**, daily user | **P3: Report consumer ("Mr. Rao")**, bank fraud-risk officer or resolution professional |
|---|---|---|---|
| Role | FCA, often FAFD/DISA-qualified (*typical; verify*), 15+ years, owns bank and RP relationships, signs reports | CA with 3–8 years' experience, runs fieldwork with 2–4 article assistants | Bank fraud-risk or credit-monitoring officer deciding on red-flagged accounts; or an RP deciding whether to file avoidance applications |
| Goals | Deliver within the bank's timeline (180-day red-flag window [S3][S4]); take on more engagements without more staff; reports that survive challenge | Stop re-keying statements; find connected parties quickly; keep working papers tidy | Clear, defensible findings mapped to RBI EWS/RFA criteria or IBC sections; evidence that holds up when the borrower reviews it [S6] |
| Pains | Thin margins on fixed fees (*hypothesis*); staff turnover; reputational risk if a report is overturned [S78] | Weeks of reconciliation (*hypothesis to measure*); scanned statements; missing documents | Generic reports; findings without traceable evidence; litigation risk |
| Fears about AI | Hallucinated findings; data leakage; ICAI/FAIS non-compliance | Being blamed for tool errors; learning curve | An AI-made claim in a fraud classification |
| What wins them | A time saving proven on their own closed case; citations on every finding; on-prem option; per-engagement price | Statement extraction that reconciles running balances; one-click annexures | An evidence-bundle export; plain-language findings with sources |

---

## 7. The first workflow: loan end-use and related-party fund-trail review

### 7.1 Inputs (one borrower case)

| # | Document | Typical format |
|---|---|---|
| 1 | Borrower bank statements, 12–36 months, all accounts | PDF (digital or scanned), XLSX |
| 2 | Sanction letter(s), disbursement advices (end-use conditions, limits) | PDF |
| 3 | Books: ledger and trial balance | Tally XML/Excel export or PDF |
| 4 | Purchase and sales invoices for the top-N counterparties | PDF or images |
| 5 | GST returns: GSTR-1, GSTR-3B, GSTR-2B summaries | PDF, JSON, XLSX |
| 6 | Stock and book-debt statements submitted to the bank | PDF or XLSX |
| 7 | Company and director master data for the borrower and key counterparties (from MCA public records, entered by the user) | CSV or PDF |
| 8 | Audited financial statements, including related-party disclosures | PDF |

### 7.2 Processing (maps to `docs/architecture/INVESTIGATION_ENGINE.md`)

1. **Ingest and extract** with page and bounding-box provenance. Validate bank statements with running-balance
   reconciliation per page.
2. **Resolve entities** across all documents: PAN, GSTIN, account + IFSC, CIN/DIN, names, addresses, phones, emails.
   Every merge carries a reason; the reviewer can merge or split.
3. **Build the graph**: entities, accounts, transactions, documents, time.
4. **Run deterministic detectors**:
   - **D1, end-use leakage**: disbursement followed within N days by outflows to non-purpose or connected counterparties.
   - **D2, round-tripping**: cycles that return to the borrower or promoter group.
   - **D3, undisclosed related parties**: shared directors, addresses or accounts not in the related-party disclosures.
   - **D4, turnover contradictions**: stock statement vs GSTR-1 turnover vs bank credits vs books.
   - **D5, invoice integrity**: invoice without a GST counterpart; duplicate or split invoices.
   - **D6, temporal anomalies**: payment before invoice, back-dating, period-end spikes.
   - **D7, document-integrity cues** for human review only (fonts, metadata).
5. **Verify** with the verifier from the investigation engine: evidence completeness, recomputation,
   counter-evidence search, leave-one-source-out fragility check.
6. **Human review**: accept, reject or "needs info", with a reason. Immutable audit log.

### 7.3 Outputs

- **Findings register.** Each finding has: type, amount, period, counterparties, mapping to RBI EWS/RFA indicators or a
  candidate IBC section, confidence, evidence links (page + region), counter-evidence, a fragility flag and the
  reviewer's decision.
- **Fund-flow graph** (interactive, with a PNG export for annexures).
- **Draft report (DOCX/PDF)** with scope, procedures, findings and annexures (transaction schedules). It includes a
  **"material relied upon" bundle** to support disclosure to the borrower [S6].
- The tool **never** labels an account "fraud". Findings support the professional's judgement, consistent with FAIS [S10].

### 7.4 Measurable outcome (pilot KPIs)

| KPI | Definition | Target |
|---|---|---|
| **Time to reviewed draft findings** | Hours from "documents received" to "partner-reviewed findings list", compared with the firm's recorded baseline for a comparable past case | **≥ 50% reduction** |
| Recall vs final report | Share of findings in the firm's final report (retrospective case) that MindDoc surfaces | ≥ 90% |
| Precision of top flags | Share of MindDoc's top-25 flags the partner rates "include" or "worth investigating" | ≥ 70% |
| Traceability | Share of accepted findings with a resolvable page-region citation | 100% |
| Numeric integrity | Findings whose numbers fail recomputation | 0 |
| Extraction QA | Bank-statement pages that pass running-balance reconciliation | ≥ 99% |

---

## 8. MVP scope (about 8–10 weeks for a solo builder; *estimate*)

**In scope**

1. Ingestion of PDF (text and scanned, with OCR boxes), XLSX/CSV and Tally XML. A bank-statement parser with
   reconciliation checks, tested on **synthetic** statements modelled on common Indian layouts.
2. Entity resolution with Indian identifier validation, a human merge/split UI and "why linked" explanations.
3. Graph store plus detectors D1–D7.
4. Evidence viewer with pixel-level highlights (extending the v2.1 PDF highlights to OCR pages, per the ROADMAP P0 item).
5. Findings register, review queue, immutable audit log, DOCX/PDF report export and evidence bundle.
6. Deployment: single-tenant Docker on a firm laptop or server, or India-region cloud. Local-LLM mode. No training on
   client data. Encryption at rest. Case deletion on close. A DPDP processor-terms template (*to draft with a lawyer*).
7. **Evaluation harness**: a synthetic case generator with 8+ seeded schemes and 20+ benign look-alikes (to measure
   false positives), plus a scorecard. Publish the scorecard (portfolio asset).

**Out of scope (for now)**: integrations with core banking or loan-origination systems; real-time EWS monitoring;
email/eDiscovery; automated MCA or GST-portal login and scraping (it needs credentials and adds liability); non-English
OCR; multi-tenant SaaS; any automated "fraud" verdict.

**Demo case**: an entirely fictional borrower group with about 24 months of statements across 3 banks, about 400
invoices, GST summaries, stock statements and about 30 entities with director links. Seeded schemes are modelled on
*public* typologies (e.g., supplier pass-through and return of loan funds, as described in reporting on the SEBI
Gensol order [S75]). Use no real company names or real personal identifiers.

---

## 9. Pricing hypotheses (all to be tested; none validated)

| Offer | Hypothesis | Rationale / anchor |
|---|---|---|
| Design-partner pilot | Free for 1–2 **retrospective** cases, in exchange for baseline timing data, KPI measurement and permission to reference (anonymised) | Builds evidence. Lowers the confidentiality barrier. |
| Per-engagement | **₹25,000–60,000** for a small case (about ≤ 2,000 pages, ≤ 3 bank accounts); **₹75,000–1,50,000** for a medium case (about ≤ 10,000 pages); large cases quoted | Matches how forensic firms bill. Must be a small fraction of the engagement fee, but **fee levels are unknown** (validation Q8). |
| Annual firm plan | **₹3–6 lakh/yr** for up to about 10 cases and 5 seats; on-prem add-on | Sits between CA-tool pricing (Vyapar TaxOne about ₹7,000/yr [S28]) and enterprise tools (Rossum from USD 18,000/yr [S56]; Diligent per-user estimates, unverified [S49]) |
| Fallback (P2P review) | Fixed fee per review cycle (e.g., ₹1.5–4 lakh per company per year), with an optional **share of recovered duplicate payments** for corporate buyers | APQC duplicate-rate ranges [S17]–[S19]. **Check ICAI Code of Ethics limits on contingent fees before offering recovery-share pricing through CA-firm partners.** |

Price-test method: the Van Westendorp questions in interviews plus a real ask at pilot close ("₹X for your next live
engagement — yes or no?").

---

## 10. Customer-validation plan

### 10.1 Who to interview (target n = 25 in 6 weeks)

| Segment | n | Where to find them |
|---|---|---|
| Forensic partners and managers at mid-size firms (ICP) | 10 | Firms on bank/IBA forensic panels (banks publish empanelment notices [S11]); ICAI regional council forensic CPE seminars; FAFD course alumni; LinkedIn ("forensic audit" + "IBA panel") |
| Insolvency professionals / transaction auditors | 5 | IBBI public register of IPs; IIIPI (ICAI's insolvency-professional agency) events |
| Bank fraud-risk or credit-monitoring officers (PSU and private) | 4 | Alumni networks; bank-staff training colleges' guest sessions; warm intros via interviewees |
| Internal-audit heads at mid-market companies (fallback) | 3 | IIA India chapter events; LinkedIn |
| Big 4 / boutique forensic professionals (learning only) | 3 | LinkedIn; alumni |

### 10.2 Ten interview questions

These ask about past behaviour and avoid leading the interviewee. Do not pitch until question 10.

1. Walk me through the last forensic or transaction audit you closed, from mandate to final report. Where did the
   hours actually go?
2. How many such engagements did your firm handle in the last 12 months, and roughly how many statements, ledgers and
   invoices did a typical one involve?
3. On the last case, who extracted and reconciled the bank statements, and how long did it take?
4. How do you identify connected or related counterparties that the borrower did not disclose? What data and tools do
   you use?
5. Tell me about a finding you missed or found late. What would have surfaced it earlier?
6. Since *Rajesh Agarwal* and *Amit Iron*, has the way you document "material relied upon" changed? Has a borrower or
   their counsel ever challenged one of your reports?
7. What software or data do you pay for today (IDEA, bank-statement converters, company-data services, LLM
   subscriptions), and what does it cost a year?
8. How is your fee set for these engagements (bank schedule, negotiated, by account size), and what turnaround is
   expected?
9. What would stop you from putting engagement documents into a tool (engagement-letter clauses, bank rules, ICAI
   ethics, client consent)? What deployment would be acceptable?
10. If a tool halved your time to draft findings and linked every finding to its source page, what would that be worth
    per engagement, and who in the firm would approve paying for it?

**Commitment test** (close every ICP interview with it): "Can we run MindDoc on a closed case's documents inside your
environment next month and measure the result against your actual report?"

### 10.3 Pilot design and success criteria

| Item | Criterion |
|---|---|
| Design partners | ≥ 3 firms agree to a pilot within 10 weeks of the first interview |
| Retrospective runs | ≥ 2 firms complete a closed-case run with the baseline recorded **before** MindDoc output is shown |
| KPIs | §7.4 targets met on ≥ 2 cases (time −50%, recall ≥ 90%, precision ≥ 70%, 100% traceability, 0 numeric mismatches) |
| Commercial signal | ≥ 1 paid engagement (any amount) or a signed LOI for the next live engagement at a stated price |
| Reference | ≥ 1 partner willing to be an (anonymised) reference or co-present a case study at an ICAI or IIIPI event |

### 10.4 Kill / pivot criteria (decide at week 10)

- Fewer than 3 of 10 ICP firms do 4 or more forensic or transaction audits a year, **or**
- No firm will run even a closed case in its own environment, **or**
- Engagement fees make ≥ ₹25,000 per case implausible.

→ **Pivot to the fallback** (P2P vendor and invoice integrity). The client owns the data there and ROI is stated in
cash. Re-score using the interview data.

---

## 11. Honest reasons this could fail

| # | Risk | Why it is real | Mitigation / early signal |
|---|---|---|---|
| 1 | **No access to data** | Engagement documents belong to banks and borrowers and are covered by confidentiality clauses. A student founder's tool is a perceived risk. | On-prem/local mode; retrospective cases; security note; incorporate a company and sign NDAs. *Signal*: commitment-test refusals. |
| 2 | **Niche too small or fees capped** | The number of engagements and the fee levels are **unverified**. Bank fee schedules may leave no room for software. | Kill criteria; fallback ready; extend to IBC transaction audits and lender stock/end-use audits. |
| 3 | **Liability and defensibility** | Fraud classification has severe civil consequences [S5]. Courts check forensic reports [S78]. One bad AI-sourced claim could end the product. | No verdicts; mandatory review; recomputation; fragility flags; publish error rates. |
| 4 | **Incumbents bundle "good-enough" AI** | Caseware is adding agentic AI [S46]. MindBridge is in Genpact's engagements [S44]. Perfios sits with lenders [S59]. | Go deep on Indian multimodal evidence and the RBI/IBC output formats incumbents lack. Move fast with design partners. |
| 5 | **General LLMs as substitutes** | Small firms may just upload PDFs to a chatbot. | Show measured recall, precision and traceability against a chatbot baseline on the same synthetic case. |
| 6 | **Technical difficulty** | Many bank layouts, poor scans, inconsistent Tally exports. A false entity merge creates a false related-party claim. | Reconciliation-based extraction QA; high-precision ER thresholds; human merge confirmation. |
| 7 | **Sales capacity** | Solo founder with limited time; partner trust takes many meetings. | Go through ICAI/IIIPI CPE talks (content-led trust); one city first. |
| 8 | **Regulatory change** | DPDP substantive duties phased in to about May 2027 [S65][S66]; possible tightening of forensic-auditor eligibility (reported, unverified); stricter sectoral rules can apply [S67]. | Processor terms, retention limits and breach runbooks from day one. |
| 9 | **Portfolio vs business tension** | Temptation to over-build impressive features (graph visuals, agents) instead of the KPIs. | Every feature must move a §7.4 KPI. Publish the evaluation scorecard. |
| 10 | **Credibility gap** | Buyers may hesitate to rely on software from an unaffiliated student. | Partner with a practising forensic CA as an adviser or co-author of the case study. |

---

## 12. What could not be verified (open questions)

- The time and cost of manual workflows in any of the six markets.
- Forensic engagement fees in India; the size of the IBA panel; the number of forensic engagements a year.
- Official national counts of GST scrutiny and demand notices for FY25 and FY26.
- Indian customers of Quantexa and MindBridge; the Indian installed base of Caseware IDEA.
- India deployments of global insurance-fraud vendors.
- Exact dates and texts of the 2026 Supreme Court ruling (*Amit Iron*). This document relies on secondary summaries
  [S6][S7]; read the judgment on sci.gov.in before quoting it.
- Licences for the datasets listed in [S79] (not re-verified this session).

---

## Sources

Retrieval date: 2026-11-10 unless noted. P = primary, S = secondary.

| ID | Title / description | Publisher | Date | Type | URL |
|---|---|---|---|---|---|
| S1 | Bank frauds down 57% to 10,114 cases but up 46% to ₹48,021 Cr in FY26 (RBI Annual Report 2025-26 data) | Outlook Business | May 2026 | S | https://www.outlookbusiness.com/news/financial-institutions-report-over-10000-cases-of-fraud-involving-48000-cr-in-fy26-rbi-data |
| S2 | Number of bank frauds fall 57% but amount rises 46% to Rs 48,021 crore in FY26 | Deccan Chronicle | May 2026 | S | https://deccanchronicle.com/nation/number-of-bank-frauds-fall-57-but-amount-rises-46-to-rs-48021-crore-in-fy26-1959980 |
| S3 | Master Directions on Fraud Risk Management (Commercial Banks & AIFIs) | Reserve Bank of India | 15 Jul 2024 | P | https://rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=12702 |
| S4 | RBI Master Directions on Fraud Risk Management (summary, incl. 180-day RFA timeline) | Grant Thornton Bharat | 2024 | S | https://www.grantthornton.in/globalassets/1.-member-firms/india/assets/pdfs/services/rbi-master-directions-on-fraud-risk-management.pdf |
| S5 | State Bank of India v. Rajesh Agarwal, judgment | Supreme Court of India | 27 Mar 2023 | P | https://api.sci.gov.in/supremecourt/2021/1710/1710_2021_1_1501_43127_Judgement_27-Mar-2023.pdf |
| S6 | Fraud classification after SBI v. Amit Iron | Trilegal | 2026 | S | https://trilegal.com/knowledge_repository/trilegal-analysis-fraud-classification-after-sbi-v-amit-iron-procedural-clarity-unresolved-consequences/ |
| S7 | Borrowers don't have right to personal hearing before banks classify accounts as fraud | Bar & Bench | Apr 2026 | S | https://www.barandbench.com/news/litigation/borrowers-dont-have-right-to-personal-hearing-before-banks-classify-accounts-as-fraud-supreme-court |
| S8 | Address by the DFS Secretary at IBBI's 9th Annual Day (avoidance applications: 1,442 / ~₹3,89,964 cr; 379 disposed; ~₹7,930 cr clawback) | Insolvency and Bankruptcy Board of India | 1 Oct 2025 | P | https://ibbi.gov.in/uploads/resources/b66e4245b3595b937ae925b1aad0a390.pdf |
| S9 | "Avoidance Transactions: Protecting Creditors' Interest under IBC" (Chairperson's Desk; 338 settled, ~₹7,516 cr clawback to Sep 2024) | IBBI, Insolvency and Bankruptcy News | late 2024 | P | https://ibbi.gov.in/uploads/resources/c69368fedcb3143b68aa21a95bbc86f1.pdf |
| S10 | DAAB announcement: FAIS mandatory from 1 July 2023 | ICAI | Jul 2023 | P | https://www.icai.org/post/daab270723 |
| S11 | IBA empanelment of forensic auditors (borrowal accounts up to / above ₹50 crore), 2025–27 cycle | ICAI Professional Development portal (IBA notice) | May 2025 | P | https://pdicai.org/rfpdetails.aspx?id=34048 |
| S12 | India has around 4.23 lakh active CAs (ICAI annual report data) | Juris Hour | 2025 | S | https://www.jurishour.in/columns/india-has-around-4-23-lakh-active-ca/ |
| S13 | Statistics of ICAI members, students, firms (till 28 Feb 2025) | TaxConcept | Mar 2025 | S | https://taxconcept.net/icai/statistics-of-icai-members-students-firms-till-28th-february-2025/ |
| S14 | How can mid-sized CA firms adopt AI | The Finance Story | Apr 2026 | S | https://thefinancestory.com/modus-fundraise-how-can-mid-sized-ca-firms-adopt-ai |
| S15 | Occupational Fraud 2026: A Report to the Nations | ACFE | 2026 | P | https://www.acfe.com/rttn |
| S16 | Occupational Fraud 2024: A Report to the Nations (PDF) | ACFE (hosted by Ivey Business School) | Mar 2024 | P | https://www.ivey.uwo.ca/media/kjljj5cy/2024-report-to-the-nations.pdf |
| S17 | Percentage of duplicate disbursements processed (benchmark) | APQC | n.d. | P | https://www.apqc.org/resource-library/resource-listing/percentage-duplicate-disbursements-processed |
| S18 | Metric of the month: detect and prevent duplicate or erroneous payments | CFO.com (APQC data) | 2020 | S | https://www.cfo.com/news/metric-of-the-month-detect-and-prevent-duplicate-or-erroneous-payments/656852/ |
| S19 | Duplicate payment detection (cites APQC 2024 ranges) | Corpay (vendor blog) | 2025–26 | S | https://www.corpay.com/en-NZ/resources/blog/duplicate-payment-detection |
| S20 | Central, state GST officers detect 25,009 fake firms fraudulently passing ₹61,545 crore ITC in FY25 | Deccan Herald (PTI) | 2025 | S | https://deccanherald.com/india/central-state-gst-officers-detect-25009-fake-firms-fraudulently-passing-rs-61545-crore-itc-in-fy25-3502634 |
| S21 | GST officers detect ₹15,851 cr fraudulent ITC claims in April–June, 3,558 fake firms | Daily Excelsior (PTI) | 2025 | S | https://www.dailyexcelsior.com/?p=2028244 |
| S22 | GST notice guide (claims 1.14 lakh ASMT-10 in FY24; unverified) | CleartaxAdvisors | 2025–26 | S | https://www.cleartaxadvisors.in/gst-notice-how-to-reply-guide |
| S23 | GST notice management at scale / GST Health Check | Clear | accessed 2026-11-10 | P | https://cleartax.in/s/gst-notice-management-at-scale |
| S24 | GST notice management software | Enterslice | n.d. | P | https://enterslice.com/gst-notice-management-software |
| S25 | GST Reply AI listing | Product Hunt | n.d. | P | https://www.producthunt.com/p/gst-reply-ai/gst-reply-ai |
| S26 | NoticeAI use case | ICAI AI portal | n.d. | P | https://ai.icai.org/usecases_details.php?id=320 |
| S27 | Litigation Shift | FnShift Solutions | n.d. | P | https://fnshiftsolutions.com/litigation-shift/ |
| S28 | Vyapar TaxOne (formerly Suvit) pricing | Vyapar | accessed 2026-11-10 | P | https://taxone.vyapar.com/pricing |
| S29 | Vyapar acquires Suvit | The Tribune | Nov 2025 | S | https://www.tribuneindia.com/news/business/vyapar-acquires-suvit-to-transform-indias-msme-and-tax-professional-ecosystem |
| S30 | Health insurers lose ₹10K crore annually due to fraud, abuse (BCG–Medi Assist) | Deccan Chronicle | Nov 2025 | S | https://deccanchronicle.com/business/health-insurers-lose-10k-crore-annually-due-to-fraud-abuse-report-1919279 |
| S31 | JSA Prism – Insurance: IRDAI Fraud Monitoring Framework | JSA Advocates & Solicitors | Oct 2025 | S | https://www.jsalaw.com/wp-content/uploads/2025/10/JSA-Prism-Insurance-October-2025-Fraud-Monitoring-Framework.Final_.pdf |
| S32 | IRDAI (Insurance Fraud Monitoring Framework) Guidelines, 2025 | IRDAI, hosted by Simpliance | 9 Oct 2025 | P (third-party host) | https://simpliance.in/India/FCC/govt_notification/Central/guidelines-regarding-insurance-regulatory-and-development-authority-of-india-insurance-fraud-monitoring-framework-guidelines-2025-7580 |
| S33 | Star Health enters agreement with Medi Assist for AI-based claims platform | Healthcare & Protection | 2025 | S | https://healthcareandprotection.com/ready-star-health-enters-agreement-with-medi-assist-for-ai-based-claims-platform/amp/ |
| S34 | MediBuddy unveils AI-powered "Sherlock" | BioSpectrum India | n.d. | S | https://biospectrumindia.com/news/100/25016/medibuddy-unveils-ai-powered-sherlock-to-combat-healthcare-fraud-.html |
| S35 | Consint.AI bags ₹22 Cr | Inc42 | 2025 | S | https://inc42.com/?p=567394 |
| S36 | Legal AI startup Harvey raises funds at $11 billion valuation | Bloomberg Law | 2026 | S | https://news.bloomberglaw.com/bloomberg-government-news/legal-ai-startup-harvey-raises-funds-at-11-billion-valuation |
| S37 | Harvey AI opened India office with tailored legal models | NewsBytes | Nov 2025 | S | https://www.newsbytesapp.com/news/business/harvey-ai-opened-india-office-with-tailored-legal-models/tldr |
| S38 | Luminance raises $75M Series C | Luminance | 18 Feb 2025 | P | https://www.luminance.com/news/press/20250218_luminance_raises.html |
| S39 | SpotDraft secures $54 million | SpotDraft | Feb 2025 | P | https://spotdraft.com/blog/spotdraft-secures-54-million-to-lead-ai-contract-lifecycle-management |
| S40 | SpotDraft raises $8M from Qualcomm Ventures | YourStory | Jan 2026 | S | https://yourstory.com/2026/01/spotdraft-funding-qualcomm-ventures-extended-series-b-round-on-device-ai-legal-workflows |
| S41 | Jurisphere.ai raises $2.2m | DealStreetAsia | 2026 | S | https://dealstreetasia.com/stories/jurisphere-ai-infoedge-antler-481303 |
| S44 | MindBridge announces global partnership with Genpact | MindBridge | 17 Feb 2026 | P | https://www.mindbridge.ai/news/mindbridge-announces-global-partnership-with-genpact-to-elevate-audit-analytics-and-risk-consulting/ |
| S46 | From AiDA to agentic: how Caseware's AI has evolved | Caseware | 2025–26 | P | https://www.caseware.com/resources/blog/from-aida-to-agentic-how-casewares-ai-has-evolved |
| S49 | Galvanize (Diligent) pricing estimates (unverified) | VendorBenchmark | 2026 | S | https://vendorbenchmark.com/vendors/galvanize-diligent-pricing |
| S52 | Ocrolus product / pricing page | Ocrolus | accessed 2026-11-10 | P | https://www.ocrolus.com/pricing/ |
| S56 | Rossum pricing | Rossum | accessed 2026-11-10 | P | https://rossum.ai/pricing/ |
| S57 | Docsumo pricing | Docsumo | accessed 2026-11-10 | P | https://www.docsumo.com/pricing |
| S59 | Perfios clients and funding (profiles) | PrivateCircle; multiples.vc | Jul 2025 | S | https://blog.privatecircle.co/?p=58199169 ; https://multiples.vc/private-comps/perfios-software-solutions |
| S60 | IDfy secures ~$52M round | Mobile ID World | n.d. | S | https://www.mobileidworld.com/idfy-secures-52m-round-to-grow-kyc-and-digital-trust-services-in-india/ |
| S61 | How IDfy has grown from a BGV provider… | YourStory | Aug 2025 | S | https://yourstory.com/2025/08/idfy-from-kyc-provider-to-verification-fraud-prevention-firm |
| S62 | Signzy raises $26 million | Signzy | 2022 | P | https://www.signzy.com/blogs/no-code-ai-platform-signzy-raises-26-million |
| S63 | The Digital Lending Directions (RBI, 8 May 2025) | K&S Partners | 2025 | S | https://ksandk.com/banking/digital-lending-directions-in-fintech-ecosystem/ |
| S64 | RBI's revised KYC Directions 2025 | K&S Partners | 2025 | S | https://ksandk.com/newsletter/rbis-revised-kyc-directions-2025/ |
| S65 | DPDP Rules 2025 explanatory document | PIB, Government of India | Nov 2025 | P | https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc20251117695301.pdf |
| S66 | Digital Personal Data Protection Rules 2025 notified (phased 12/18 months) | Mondaq | Nov 2025 | S | https://www.mondaq.com/india/data-protection/1708164/digital-personal-data-protection-rules-2025-notified |
| S67 | From localisation debates to a negative list: cross-border transfers under the DPDP Act | Mondaq | 2026 | S | https://www.mondaq.com/india/data-protection/1764976/from-localisation-debates-to-a-negative-list-making-cross-border-data-transfers-work-under-indias-dpdp-act |
| S68 | AppZen profile (Series D Sep 2025; Oversight as competitor) | Sacra | 2025–26 | S | https://sacra.com/c/appzen/ |
| S70 | EY Document Anomaly & Transaction Analytics | EY India | n.d. | P | https://www.ey.com/en_in/services/forensic-integrity-services/document-anomaly-transaction-analytics |
| S75 | SEBI issues interim order against Gensol on suspicion of diversion of funds | YourStory | Apr 2025 | S | https://yourstory.com/2025/04/sebi-interim-order-gensol-diversion-funds-anmol-jaggi-blusmart |
| S76 | DocILE benchmark (ICDAR 2023 / CLEF 2023) | Rossum / DocILE authors | 2023 | P | https://docile.rossum.ai/ |
| S77 | CUAD: An Expert-Annotated NLP Dataset for Legal Contract Review | Hendrycks et al., arXiv / NeurIPS 2021 | 2021 | P | https://arxiv.org/abs/2103.06268 |
| S78 | Forensic audit reports must meet statutory standards | SupremeToday | Jun 2026 | S | https://supremetoday.ai/forensic-audit-reports-must-meet-statutory-standards-20260630019 |
| S79 | Public datasets referenced but **not re-verified this session** (check licence before use): SEC Accounting & Auditing Enforcement Releases; Enron email corpus (CMU); FUNSD; SROIE; Synthea | SEC; CMU; dataset authors | n/a | P (to verify) | https://www.sec.gov/enforcement-litigation/accounting-auditing-enforcement-releases ; https://www.cs.cmu.edu/~enron/ ; https://guillaumejaume.github.io/FUNSD/ ; https://rrc.cvc.uab.es/?ch=13 ; https://synthetichealth.github.io/synthea/ |
