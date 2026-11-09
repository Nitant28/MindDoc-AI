# MindDoc AI — Competitive Analysis

*Version 1.0 · 2026-11-10 · Companion to [`MARKET_SELECTION.md`](MARKET_SELECTION.md)*

**How to read this document**

- `[S#]` tags point to the Sources table at the end. Each source is marked **P** (primary: regulator, court, company or
  standard-setter publication) or **S** (secondary: press, law-firm commentary, aggregators, vendor blogs about others).
- **"Not public"** means the vendor publishes no price and none was found from a credible source. **"Unverified"**
  means a figure exists only on a third-party site and could not be checked against the vendor.
- Only what was found in research for this document is stated as fact. Anything else is labelled *inference* or
  *to verify*. No market sizes or customer names were invented.

---

## 0. Summary

| Question | Answer |
|---|---|
| Is there room for MindDoc? | **Yes, in one specific gap.** Two groups of tools exist. Structured-data analytics tools (MindBridge, Caseware IDEA, Diligent/ACL) score ledgers and journals but do not read scanned bank statements, invoices and filings as evidence. Document-AI tools (Rossum, Docsumo, Nanonets, ABBYY, Hyperscience) extract fields but do not investigate across documents. Lender tools (Perfios, Ocrolus) analyse bank statements to make a credit decision, not to build a forensic case. No one found in this research offers an **evidence-cited, cross-document fund-trail and related-party investigation** sold to the mid-size Indian forensic/CA firms that carry out lender and insolvency forensic work. |
| Most crowded markets | KYC/credit document verification (Perfios, Signzy, IDfy, HyperVerge, Ocrolus); GST notice drafting (Clear, Enterslice, GST Reply AI, TaxTMI, FnShift and many tools listed on ICAI's AI portal); legal AI (Harvey with an India office, Luminance, Kira/Litera, SpotDraft and a wave of funded Indian start-ups). |
| Three most dangerous competitors for the recommended wedge (forensic review of borrower fund diversion) | **1. Caseware IDEA** (the analytics tool audit and forensic teams already use, now adding agentic AI) · **2. Perfios** (India-native bank-statement intelligence already used by large lenders) · **3. MindBridge** (AI risk scoring of whole transaction populations, now inside Genpact's risk consulting work). The real day-one competitor is the **status quo**: Excel plus IDEA plus a general LLM chat assistant. |
| What MindDoc must do better | Reason **across** Indian document types (bank statement ↔ Tally ledger ↔ invoice ↔ GST return ↔ stock statement ↔ MCA director data). Resolve entities **explainably** using Indian identifiers. Produce findings a court will accept, each one traceable to the "material relied upon" (see SBI v. Amit Iron, 2026 [S6][S7]). Run on-premises or in an India region. Be priced per engagement for mid-size firms rather than as an enterprise licence. Details are in §5. |

---

## 1. The capability lens

MindDoc's claimed differentiators are: multimodal document understanding with visual grounding; an evidence-backed
knowledge graph; entity resolution; anomaly and contradiction discovery across documents; temporal reasoning; and
investigation reports with human approval and an audit trail. The table maps competitor *categories* (not individual
products) against these, based on what the vendors' own materials say.

| Capability | GL/journal analytics (MindBridge, IDEA, Diligent) | Document AI / extraction (Rossum, Docsumo, Nanonets, ABBYY, Hyperscience) | Lender doc-intelligence (Perfios, Ocrolus) | KYC/identity (Signzy, IDfy) | Entity-resolution / graph platforms (Quantexa, Palantir) | eDiscovery / investigations (Relativity, Nuix) | Legal AI (Harvey, Luminance, Kira, SpotDraft) | **MindDoc target** |
|---|---|---|---|---|---|---|---|---|
| Reads scanned/unstructured docs as evidence | Limited (structured data import) | **Strong** | Strong (bank statements, tax forms) [S52] | Strong (IDs) | Ingests both; focused on structured | Strong (email, files) | Strong (contracts) | Strong + pixel-level citations |
| Cross-document contradictions | No (single-ledger analytics) | Partial: "cross-document validations" (Docsumo Enterprise) [S57]; "multi-document transactions" (Rossum Ultimate) [S56] | Partial ("data inconsistencies") [S52] | Partial (ID vs selfie/data) | Via linked data | Manual review | Clause comparison | **Core** |
| Entity resolution | No | Master-data matching (Rossum Business) [S56] | Not stated | Identity match | **Core** (graph-based ER) [S43] | Limited | Party extraction | Core, with Indian keys (PAN, GSTIN, IFSC, CIN/DIN) |
| Fund-flow / relationship graph | No | No | Cash-flow analytics | No | **Core** | Communication graphs | No | Core |
| Temporal reasoning | Period/time-series anomalies | No | Cash-flow trends | No | Yes | Timelines | Obligation dates | Core (sequence, back-dating, round-trips within N days) |
| Report with human approval and audit trail | Audit workpapers | Human-in-loop validation screens | Underwriting decisioning | Case review | Case management | Review workflows | Drafting | Core: findings register, approve/reject, immutable log |
| India deployment / pricing fit for mid-size firms | Sales-quoted enterprise [S45][S48] | Mostly volume-quoted; Rossum from USD 18,000/yr [S56] | Enterprise lender contracts | Enterprise API | Enterprise | Enterprise | Enterprise | Per-engagement INR pricing; on-prem option |

---

## 2. Competitor tables by candidate market

Threat level is relative **to MindDoc entering that market**: High = would directly block or out-sell a solo entrant;
Medium = overlaps, but there is a gap; Low = adjacent.

### 2.1 Financial audit and forensic accounting (CA firms, internal audit, Big 4 forensic)

| Company / product | What it actually does (per sources) | Buyer | India presence | Pricing (public?) | Overlap with MindDoc | Threat |
|---|---|---|---|---|---|---|
| **Caseware IDEA** (+ AiDA → Verity agents) | Desktop audit-analytics tool, described by the vendor as "industry leader for audit analytics for over 30 years". IDEA 13 is paired with AiDA, a generative-AI assistant that is being succeeded by "Caseware Verity" agentic AI [S46][S47]. No forensic-specific AI features found [S46]. | Audit, internal-audit and forensic teams | Used in India (installed-base size not verified) | **Not public**; sales-led, no self-serve tiers [S48] | Analysis of structured data, sampling, duplicate tests. Does not reason over scanned documents. | **High** (incumbent workflow) |
| **MindBridge** | "AI-powered financial intelligence": risk scoring of the full transaction population, anomaly and fraud detection, AI-led internal audits. Global partnership with **Genpact** (17 Feb 2026) embeds it in Genpact's Enterprise Risk Consulting engagements [S44]. | Audit firms, finance teams with high transaction volumes [S45] | A Mumbai address appears on a listing; no Indian channel deal found (*to verify*) | **Not public**; custom quote, "may be expensive for smaller teams" (aggregator) [S45] | Anomaly scoring on ledgers. No multimodal evidence, no fund-trail graph across bank and GST data. | **High** |
| **Diligent One** (formerly HighBond / ACL / Galvanize) | GRC platform with an audit module: AI-accelerated risk assessment, agentic evidence collection, continuous control monitoring, board reporting (aggregator summary) [S49] | Chief audit executives, GRC teams at enterprises | Not verified | **Not public**. Third-party estimates of USD 1,800–3,200 per full user — **unverified** [S49] | Audit management and analytics. Little document reasoning. | Medium |
| **EY Document Anomaly & Transaction Analytics** (EY India) | AI/ML document verification: OCR, **GST checks**, personal-information verification, **vendor authentication**, flags suspicious dates and claims. Vendor claims "10 lakh documents in less than six hours" [S70]. | Delivered within EY forensic engagements and to EY clients | **Yes** (EY India) | Not public (service-led) | Strong overlap on document anomalies and vendor checks. Shows Big 4 build their own tools. | Medium (competes for large engagements; not sold to mid-size firms as a tool) |
| **Nuix Neo Investigations** | Digital investigations and eDiscovery platform [S51] | Investigators, law enforcement, corporate investigations | Not verified | **Not public** [S51] | Evidence processing at scale. Not accounting-native. | Low–Medium |
| **Indian CA-firm AI tools**: CORAA AI, AssureAI, Irame.ai, AuditCue, tools on ICAI's AI portal (e.g., "Audit Automation Pro") | Ledger scrutiny, invoice vouching via OCR, GSTR-2A reconciliation, SA 530 sampling (self-described) [S73][S74]. Irame.ai: USD 1M seed, Mar 2025 [S71]. AuditCue: USD 1.5M seed (date unclear) [S72]. | Small and mid-size CA firms, internal audit | **Yes** | Mostly not public | Statutory-audit automation, not forensic fund-trail. Could move into forensic. | Medium (signals the CA-tool space is crowding fast) |
| **Status quo**: Excel + IDEA + bank-statement converters + general LLM chat | The default workflow (inference from interviews still to be done; see the validation plan) | Every firm | Universal | Low cost | Good enough for small cases | **High** |

### 2.2 GST / tax notice and compliance handling

| Company / product | What it actually does | Buyer | Pricing | Overlap | Threat |
|---|---|---|---|---|---|
| **Clear (ClearTax)** | The public page reviewed offers a free "GST Health Check": GSTR-1 vs 3B, 3B vs 2A, vendor compliance report. Also lists Clear Compliance Cloud and MaxITC (no details) [S23]. | Enterprises, CAs | Health check free; others by demo [S23] | Reconciliation, vendor compliance | **High** (distribution and brand) |
| **Enterslice** GST notice software | Monitors the GSTN portal, sends alerts (claims detection "within 20 minutes"), AI reply drafting reviewed by CAs, India-hosted servers (vendor claims, unverified) [S24] | SMEs, CAs | Not found | Notice tracking and drafting | High |
| **GST Reply AI** | Per-reply AI drafting with CGST Act citations. Covers 12 notice types including ASMT-10 and DRC-01 [S25]. | CAs, SMEs | Not found | Drafting | Medium |
| **TaxTMI drafter, AI Accountant, FnShift "Litigation Shift", Trackase, ICAI-listed "NoticeAI"** | Reply drafting, notice auto-retrieval across GSTINs, deadline tracking, litigation management [S26][S27] | Tax professionals | Mostly not public | Drafting and workflow | Medium each; **crowded as a group** |
| **Vyapar TaxOne (formerly Suvit)** | Bookkeeping automation for CA practices: unlimited bank statements (incl. scanned PDF), purchase/sales entry, Tally integration, GST reconciliation. Claims "10,000 practicing firms". Vyapar acquired Suvit (reported Nov 2025) [S28][S29]. | CA practices | **INR 7,000/yr** (shown as 50% off INR 14,000), accessed 2026-11-10 [S28] | Bank-statement extraction for CAs | Low for the wedge, but **the key price anchor**: CA-practice tools sell for thousands of rupees a year |

### 2.3 Insurance claims investigation (health / motor)

| Company / product | What it actually does | Buyer | Pricing | Overlap | Threat |
|---|---|---|---|---|---|
| **Medi Assist (TPA) — MAtrix** | AI claims platform. Star Health signed an agreement to use it for fraud and waste reduction [S33]. Medi Assist co-authored the BCG FWA study [S30]. | Insurers | Not public | Claims document AI, FWA detection | **High** (owns claims flow as a TPA) |
| **MediBuddy "Sherlock"** | AI fraud, waste and abuse detection for reimbursement claims [S34] | Corporate health, insurers | Not public | FWA detection | Medium |
| **Consint.AI** | Claims processing, fraud detection, document digitisation; raised INR 22 cr [S35] | Insurers, TPAs | Not public | Direct | Medium–High |
| **Insurance Information Bureau (IIB) industry framework** | IRDAI's 2025 guidelines require insurers to take part in the IIB's fraud-monitoring technology framework [S31][S32] | Mandatory for insurers | n/a | Shared industry fraud intelligence | Shapes the market. A start-up must integrate with it, not replace it. |
| **Global vendors (e.g., Shift Technology, FRISS)** | Insurance-fraud analytics (general knowledge). India deployments **not verified** in this research. | Insurers | Not public | Direct | *To verify* |

### 2.4 Legal investigation and contract intelligence

| Company / product | What it actually does | India presence | Pricing | Threat |
|---|---|---|---|---|
| **Harvey** | Legal AI platform. Reported USD 11B valuation in a 2026 round [S36] (a later, higher valuation is reported only by low-quality sources and is **unverified**). India office opened Nov 2025. Reported early Indian clients: Shardul Amarchand Mangaldas, AZB & Partners, PwC India [S37]. | **Yes** | Not public | **High** |
| **Luminance** | Contract generation, negotiation and post-execution analysis ("Panel of Judges" approach). USD 75M Series C, Feb 2025 [S38]. | Not verified | Not public | High |
| **Kira (Litera)** | Contract review and extraction inside the Litera suite (no Kira-specific data gathered here) | Not verified | Not public | Medium–High |
| **SpotDraft** | CLM headquartered in Bengaluru. USD 54M Series B (Feb 2025) [S39]. USD 8M from Qualcomm Ventures (Jan 2026) for "VerifAI", contract review that runs on the device [S40]. | **Yes** | Not public | High (in-house legal) |
| **Relativity (aiR)** | eDiscovery with AI review and privilege tools. One reseller offers "all-in unlimited" aiR pricing (Oct 2025) because per-document pricing was unpredictable [S50]. | Not verified | Not public (reseller-specific) | Medium |
| **Indian legal AI start-ups**: Jurisphere.ai (USD 2.2M) [S41], others; **CaseMine / SCC Online / Manupatra** (research) | Legal research and drafting | **Yes** | Mostly not public | Crowded. CaseMine/AMICUS was **not verified** in this research. |

### 2.5 Procurement / vendor and third-party risk (duplicate vendors, invoice–PO–contract mismatches)

| Company / product | What it actually does | Pricing | Overlap | Threat |
|---|---|---|---|---|
| **AppZen** | Pre-payment "spend audit" across expenses, cards and invoices, including duplicate spend detection across systems [S69]. USD 180M Series D, Sep 2025 (Sacra) [S68]. | Not public | Duplicate and anomaly detection on AP | High (global enterprise) |
| **Oversight** | AI spend and risk audit, partnerships with ERP vendors (per Sacra) [S68] | Not public | Same | High (global enterprise) |
| **Rossum** | Invoice/document AI. Business tier adds **master data matching and duplicate detection**. Ultimate tier adds multi-document transactions [S56]. | **From USD 18,000/yr** (Starter) [S56] | Extraction + duplicates | Medium |
| **Docsumo** | Document AI. Enterprise tier lists "cross-document validations", "AI-led case management", "master data lookup" [S57]. | Custom quote. Setup fees extra [S57]. | Closest IDP overlap to MindDoc | Medium |
| **Nanonets** | Workflow-block IDP. Data-extraction block USD 0.30 per run. Vendor estimate "under USD 2 per invoice end-to-end" [S58]. | Starter USD 100/month for 100 credits; Growth and Enterprise by quote [S58] | Extraction | Low–Medium |
| **ABBYY Vantage / Hyperscience** | Enterprise IDP platforms | ABBYY: about USD 0.11/page at 100K pages and USD 0.06 at 1M (UK G-Cloud sheet) [S55]; aggregator USD 0.04–0.08/page [S54]. Hyperscience "from USD 50,000/yr" (aggregator, **unverified**) [S53]. | Extraction layer MindDoc could compete with or build on | Low (infrastructure) |
| **EY DATA** (see 2.1) | Includes vendor authentication and GST checks [S70] | Not public | Vendor checks | Medium |

### 2.6 Bank/NBFC credit underwriting and KYC document verification

| Company / product | What it actually does | Scale / funding (as reported) | Pricing | Threat |
|---|---|---|---|---|
| **Perfios** | Bank-statement analysis, document tamper flags, fraud suite ("Protect") for lenders. Reported clients include ICICI, HDFC, Axis, SBI, Bajaj Finserv, Kotak, Aditya Birla Capital [S59]. | Teachers' Venture Growth USD 80M (Mar 2024) per aggregator; IPO preparation reported (unconfirmed) [S59] | Not public | **Very high** |
| **IDfy** | KYC, video KYC, background verification, fraud prevention. More than 60M verifications/month for more than 1,500 clients (company-reported) [S61]. About USD 52–53M round (date unclear) [S60]. | — | Not public | Very high |
| **Signzy** | No-code KYC/onboarding workflows. USD 26M Series B (2022) [S62]. Claims "800+ financial institutions" (self-reported). | — | Not public | Very high |
| **Ocrolus** (US) | AI analysis of bank statements, pay stubs and tax forms for lenders, with fake-document detection [S52] | — | **Not public** [S52] | Low in India / High in US |
| **HyperVerge** and others | Identity and forgery detection (market presence noted, not researched) | — | — | High |

### 2.7 Cross-market platforms named in the brief: relevance check

| Name | Verdict for MindDoc's wedge |
|---|---|
| **Quantexa** | Graph-based entity resolution for AML, KYC and fraud. USD 175M Series F at USD 2.6B (Mar 2025) [S43]. Bank-scale enterprise. **No Indian customers found.** Architecture benchmark, not a wedge competitor. |
| **Palantir** | Enterprise and government data platforms. **Not researched for this report**; listed as an architecture reference only (the ROADMAP already cites its ontology approach). Not a realistic competitor for a mid-size Indian forensic firm. |
| **Hebbia** | "Matrix" document research for finance. USD 130M Series B at USD 700M (Jul 2024) [S42]. Serves asset managers and PE. Overlaps on multi-document Q&A, not forensic investigation. Low threat in India. |
| **Harvey, Kira/Litera, Luminance, Relativity, Nuix, CaseMine, SpotDraft** | Relevant only to the legal market (2.4). Nuix is marginal for forensic. |
| **Ocrolus, Signzy, IDfy, Perfios** | Relevant to credit/KYC (2.6). **Perfios is also relevant to the forensic wedge**, because the bank-statement intelligence already sits with the lender (§4). |
| **Hyperscience, ABBYY, Rossum, Docsumo, Nanonets** | Extraction layer. Possible build-on components (or benchmarks) for MindDoc's ingestion, not substitutes for investigation. |
| **ClearTax/Clear, Suvit (now Vyapar TaxOne)** | GST and bookkeeping (2.2). Price anchors for Indian CA tools. |
| **MindBridge, Caseware IDEA, ACL/Diligent** | Core competitors in forensic and audit (2.1). |

---

## 3. Who wins today, and why (by market)

| Market | Who wins today | Why | Implication for MindDoc |
|---|---|---|---|
| Forensic accounting | Status quo + IDEA; Big 4 own tools | Trust, installed base, professional liability, data confidentiality | Enter through **mid-size firms**, on a narrow, high-value workflow, with defensibility as the selling point |
| GST notices | Clear plus a long tail of cheap drafting tools | Distribution, low price points, CA ecosystem | Avoid. Commodity LLM drafting. |
| Insurance claims | TPAs (Medi Assist), in-house insurer teams, the IIB framework | Owning claims data and the regulatory mandate | Avoid as first wedge. Enterprise sales and sensitive data. |
| Legal | Harvey (India office), Luminance, SpotDraft, Indian start-ups | Capital, brand, law-firm relationships | Avoid |
| Procurement/vendor | AppZen/Oversight (global enterprise); manual reviews in India's mid-market (*inference*) | ERP integration, ROI on recovered cash | **Fallback.** The mid-market gap appears real but is not yet verified. |
| Credit/KYC | Perfios, IDfy, Signzy | API scale, regulator-aligned onboarding, bank integrations | Avoid. Do not build a me-too KYC pack (this revises ROADMAP §2 pack C). |

---

## 4. Deep dive: the three most dangerous competitors for the recommended wedge

The recommended wedge is **forensic review of borrower fund diversion and related parties**, sold to mid-size CA and
forensic firms empanelled by lenders (and to transaction auditors in insolvency cases). See `MARKET_SELECTION.md` §4.

| # | Competitor | Why it is dangerous | Where it is weak (MindDoc's opening) | Signal to watch |
|---|---|---|---|---|
| 1 | **Caseware IDEA** | Forensic and internal-audit staff are already trained on it. It is part of the existing workflow and CPE courses. Caseware is adding agentic AI (AiDA → Verity) [S46][S47]. A good-enough AI layer inside IDEA would cut demand for a new tool. | It is structured-data analytics on imported tables. No source shows it reasoning over scanned bank statements, invoices and GST filings together, or producing evidence-cited, page-linked findings. | IDEA or Verity releases that add document ingestion or forensic agents |
| 2 | **Perfios** | It already parses bank statements for most large Indian lenders [S59] and has a fraud suite. A bank's fraud-risk group could ask Perfios for a "forensic view" instead of hiring a new vendor. | It is built for **credit decisions at onboarding and monitoring**, not for a forensic narrative that links books, GST and MCA related-party data with documented reviewer judgement. Forensic firms are not its buyer. | Perfios launches forensic, end-use or EWS products for bank fraud-risk groups |
| 3 | **MindBridge (+ Genpact)** | AI-native full-population risk scoring with an audit-grade brand. Genpact has a large India delivery base and is embedding MindBridge in risk consulting engagements [S44]. | Enterprise-priced [S45]. Focused on ledgers and journal entries, not multimodal Indian documents. Not tailored to RBI red-flagged-account or IBC avoidance outputs. | MindBridge pricing or packaging for Indian mid-size firms; an Indian channel partner |

Honourable mentions: the **Big 4 in-house tools** (e.g., EY DATA [S70]) are formidable on large engagements, but they are
not sold as tools to mid-size firms. **General LLM assistants** used ad hoc are the default substitute. A MindDoc demo
must beat "upload PDFs to a chatbot" on accuracy, traceability and confidentiality, not just on convenience.

---

## 5. What MindDoc must do better to matter

These are written as testable requirements. Each one closes a specific competitor gap identified above.

| # | Requirement | Gap it closes | How to prove it (measurable) |
|---|---|---|---|
| R1 | **Cross-document fund-trail reasoning**: link each bank-statement line to its ledger entry, invoice, GST return line and counterparty, and flag where they disagree | GL-only tools (IDEA, MindBridge), IDP tools that extract but do not investigate | On a synthetic case with seeded schemes, recall ≥ 90% of seeded contradictions and ≤ 1 false flag per 10 benign look-alikes |
| R2 | **Explainable entity resolution with Indian identifiers** (PAN/GSTIN format and checksum validation, IFSC + account number, CIN/DIN, addresses, phone and email), with a human merge/split UI and a "why linked" explanation | Generic ER (Quantexa is bank-scale), IDP master-data matching | Pairwise ER precision ≥ 0.98 on high-risk merges (a wrong "related party" claim is costly), recall ≥ 0.90; every merge has a stated reason |
| R3 | **"Material relied upon" evidence bundles**: every finding linked to page and region, numbers recomputed by deterministic tools, counter-evidence attached. After SBI v. Amit Iron, borrowers must ordinarily get access to the audit reports and material relied on [S6][S7], and courts are checking forensic reports against statutory standards [S78]. | Chat assistants, most analytics tools | 100% of accepted findings have resolvable citations; 0 numeric mismatches after recomputation; one-click export of the evidence bundle |
| R4 | **Professional-judgement workflow**: findings register, approve/reject with reasons, immutable audit log, working papers that follow ICAI's Forensic Accounting and Investigation Standards (FAIS, mandatory since 1 Jul 2023 [S10]) | Generic AI tools that "decide" | The tool never labels an account "fraud". Every finding has a reviewer decision recorded before export. |
| R5 | **Indian document reality**: scanned and digital bank statements in many bank layouts, Tally exports, GST return data, stock and book-debt statements | Global tools tuned to US/EU documents | Bank-statement extraction checked by running-balance reconciliation (opening + credits − debits = closing) on ≥ 99% of pages in the test set |
| R6 | **Deployable where the data lives**: single-tenant Docker or India-region cloud, a local-LLM mode (already in the v2.1 stack), no training on client data, deletion on case close | Cloud-only SaaS that client confidentiality may rule out | A security note and data-flow diagram that firms can show their bank clients. DPDP processor terms (DPDP Rules phased to about May 2027 [S65][S66]). |
| R7 | **Price for mid-size firms**: per-engagement INR pricing far below enterprise licences | MindBridge, IDEA, Diligent, Hyperscience (enterprise or sales-quoted) | Pilot conversion at the hypothesised price points (`MARKET_SELECTION.md` §9) |
| R8 | **Outputs in the shape the reader needs**: findings mapped to RBI early-warning-signal / red-flagged-account criteria [S3][S4] and to IBC avoidance sections (43/45/49/50/66) | Generic anomaly lists | Partner rates ≥ 70% of top-25 flags "worth including or investigating" |
| R9 | **Published, reproducible evaluation** on synthetic seeded cases plus public benchmarks (DocILE for invoices [S76]) | Vendor claims nobody can check (e.g., "99+% accuracy") | Public scorecard in the repository. Doubles as portfolio evidence. |
| R10 | **Time-to-first-finding under 1 hour** from upload, on a laptop-class machine | Heavy enterprise onboarding (ABBYY implementation costs, Docsumo setup fees [S57]) | Measured during pilots |

**Where MindDoc should not compete**: generic field extraction (buy or benchmark against ABBYY, Rossum or Nanonets),
GST reply drafting, KYC APIs, contract lifecycle management, and legal research.

---

## 6. Pricing anchors found (for `MARKET_SELECTION.md` §9)

| Product | Price | Status |
|---|---|---|
| Vyapar TaxOne (formerly Suvit), CA bookkeeping automation | INR 7,000/yr (50% off INR 14,000) | Verified on vendor page, 2026-11-10 [S28] |
| Nanonets | USD 100/month for 100 credits; extraction block USD 0.30/run | Verified on vendor page [S58] |
| Rossum Starter | From USD 18,000/yr | Verified on vendor page [S56] |
| ABBYY Vantage (core skills) | About USD 0.11/page at 100K pages; about USD 0.06 at 1M | UK government G-Cloud price sheet [S55] |
| Hyperscience | From USD 50,000/yr | Aggregator, **unverified** [S53] |
| Diligent (HighBond) | USD 1,800–3,200 per full user per year | Aggregator, **unverified** [S49] |
| MindBridge, Caseware IDEA, Perfios, IDfy, Signzy, Harvey, Luminance, AppZen, Ocrolus, Docsumo | Not public | — |

---

## 7. Watch list (re-check quarterly)

1. Caseware Verity / IDEA forensic features.
2. Perfios products for lender fraud-risk and end-use monitoring.
3. MindBridge India channel and pricing.
4. Indian CA-AI start-ups (CORAA, AssureAI, Irame.ai, AuditCue) moving from ledger scrutiny into forensic work.
5. IBA forensic-auditor empanelment rules, and reported moves to tighten auditor eligibility in 2026 (seen in search results, not verified).
6. Further Supreme Court and High Court rulings on what makes a forensic report adequate.
7. DPDP Rules milestones (Nov 2026 and May 2027).

---

## Sources

Retrieval date for all sources: 2026-11-10 unless noted. P = primary, S = secondary.

| ID | Title / description | Publisher | Date | Type | URL |
|---|---|---|---|---|---|
| S3 | Master Directions on Fraud Risk Management (Commercial Banks & AIFIs) | Reserve Bank of India | 15 Jul 2024 | P | https://rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=12702 |
| S4 | RBI Master Directions on Fraud Risk Management (summary) | Grant Thornton Bharat | 2024 | S | https://www.grantthornton.in/globalassets/1.-member-firms/india/assets/pdfs/services/rbi-master-directions-on-fraud-risk-management.pdf |
| S6 | Fraud classification after SBI v. Amit Iron | Trilegal | 2026 | S | https://trilegal.com/knowledge_repository/trilegal-analysis-fraud-classification-after-sbi-v-amit-iron-procedural-clarity-unresolved-consequences/ |
| S7 | Borrowers don't have right to personal hearing before banks classify accounts as fraud | Bar & Bench | Apr 2026 | S | https://www.barandbench.com/news/litigation/borrowers-dont-have-right-to-personal-hearing-before-banks-classify-accounts-as-fraud-supreme-court |
| S10 | DAAB announcement: FAIS mandatory from 1 July 2023 | ICAI | Jul 2023 | P | https://www.icai.org/post/daab270723 |
| S23 | GST notice management at scale / GST Health Check | Clear (Defmacro Software) | accessed 2026-11-10 | P | https://cleartax.in/s/gst-notice-management-at-scale |
| S24 | GST notice management software | Enterslice | n.d. | P | https://enterslice.com/gst-notice-management-software |
| S25 | GST Reply AI listing | Product Hunt (vendor listing) | n.d. | P | https://www.producthunt.com/p/gst-reply-ai/gst-reply-ai |
| S26 | NoticeAI use case | ICAI AI portal | n.d. | P | https://ai.icai.org/usecases_details.php?id=320 |
| S27 | Litigation Shift | FnShift Solutions | n.d. | P | https://fnshiftsolutions.com/litigation-shift/ |
| S28 | Vyapar TaxOne (formerly Suvit) pricing | Vyapar | accessed 2026-11-10 | P | https://taxone.vyapar.com/pricing |
| S29 | Vyapar acquires Suvit | The Tribune | Nov 2025 | S | https://www.tribuneindia.com/news/business/vyapar-acquires-suvit-to-transform-indias-msme-and-tax-professional-ecosystem |
| S30 | Health insurers lose ₹10K crore annually due to fraud, abuse (BCG–Medi Assist) | Deccan Chronicle | Nov 2025 | S | https://deccanchronicle.com/business/health-insurers-lose-10k-crore-annually-due-to-fraud-abuse-report-1919279 |
| S31 | JSA Prism – Insurance: IRDAI Fraud Monitoring Framework | JSA Advocates & Solicitors | Oct 2025 | S | https://www.jsalaw.com/wp-content/uploads/2025/10/JSA-Prism-Insurance-October-2025-Fraud-Monitoring-Framework.Final_.pdf |
| S32 | IRDAI (Insurance Fraud Monitoring Framework) Guidelines, 2025 (text) | IRDAI, hosted by Simpliance | 9 Oct 2025 | P (third-party host) | https://simpliance.in/India/FCC/govt_notification/Central/guidelines-regarding-insurance-regulatory-and-development-authority-of-india-insurance-fraud-monitoring-framework-guidelines-2025-7580 |
| S33 | Star Health enters agreement with Medi Assist for AI-based claims platform | Healthcare & Protection | 2025 | S | https://healthcareandprotection.com/ready-star-health-enters-agreement-with-medi-assist-for-ai-based-claims-platform/amp/ |
| S34 | MediBuddy unveils AI-powered "Sherlock" | BioSpectrum India | n.d. | S | https://biospectrumindia.com/news/100/25016/medibuddy-unveils-ai-powered-sherlock-to-combat-healthcare-fraud-.html |
| S35 | Consint.AI bags ₹22 Cr | Inc42 | 2025 | S | https://inc42.com/?p=567394 |
| S36 | Legal AI startup Harvey raises funds at $11 billion valuation | Bloomberg Law | 2026 | S | https://news.bloomberglaw.com/bloomberg-government-news/legal-ai-startup-harvey-raises-funds-at-11-billion-valuation |
| S37 | Harvey AI opened India office with tailored legal models | NewsBytes | Nov 2025 | S | https://www.newsbytesapp.com/news/business/harvey-ai-opened-india-office-with-tailored-legal-models/tldr |
| S38 | Luminance raises $75M Series C | Luminance | 18 Feb 2025 | P | https://www.luminance.com/news/press/20250218_luminance_raises.html |
| S39 | SpotDraft secures $54 million | SpotDraft | Feb 2025 | P | https://spotdraft.com/blog/spotdraft-secures-54-million-to-lead-ai-contract-lifecycle-management |
| S40 | SpotDraft raises $8M from Qualcomm Ventures | YourStory | Jan 2026 | S | https://yourstory.com/2026/01/spotdraft-funding-qualcomm-ventures-extended-series-b-round-on-device-ai-legal-workflows |
| S41 | Jurisphere.ai raises $2.2m | DealStreetAsia | 2026 | S | https://dealstreetasia.com/stories/jurisphere-ai-infoedge-antler-481303 |
| S42 | AI startup Hebbia raised $130M at a $700M valuation | TechCrunch | 9 Jul 2024 | S | https://techcrunch.com/2024/07/09/ai-startup-hebbia-rased-130m-at-a-700m-valuation-on-13-million-of-profitable-revenue |
| S43 | Quantexa completes USD 175M Series F | Quantexa (press release via FinTech Futures) | Mar 2025 | P | https://www.fintechfutures.com/press-releases/quantexa-completes-usd-175-million-series-f-investment-round-led-by-teachers-venture-growth |
| S44 | MindBridge announces global partnership with Genpact | MindBridge | 17 Feb 2026 | P | https://www.mindbridge.ai/news/mindbridge-announces-global-partnership-with-genpact-to-elevate-audit-analytics-and-risk-consulting/ |
| S45 | MindBridge pricing | Toolradar | Sep 2026 | S | https://toolradar.com/tools/mindbridge/pricing |
| S46 | From AiDA to agentic: how Caseware's AI has evolved | Caseware | 2025–26 | P | https://www.caseware.com/resources/blog/from-aida-to-agentic-how-casewares-ai-has-evolved |
| S47 | IDEA brochure | Caseware | 2025 | P | https://insights.caseware.com/hubfs/IDEA%20brochure_Final.pdf |
| S48 | Caseware IDEA pricing | xpay.sh | n.d. | S | https://www.xpay.sh/saas-pricing/caseware-idea/ |
| S49 | Galvanize (Diligent) pricing estimates; Diligent One product summary | VendorBenchmark; ERP Research | 2026 | S | https://vendorbenchmark.com/vendors/galvanize-diligent-pricing ; https://erpresearch.com/erp-add-ons/audit-management/diligent-one-platform |
| S50 | Cimplifi first to market with all-in unlimited Relativity aiR pricing | Cimplifi (press release, syndicated) | 9 Oct 2025 | S | https://business.mammothtimes.com/mammothtimes/article/gnwcq-2025-10-9-cimplifi-first-to-market-with-all-in-unlimited-relativity-air-for-review-and-air-for-privilege-pricing-ushering-in-a-new-era-of-ai-driven-ediscovery |
| S51 | Nuix Neo Investigations pricing | G2 | n.d. | S | https://www.g2.com/products/nuix-neo-investigations/pricing |
| S52 | Ocrolus pricing / product page | Ocrolus | accessed 2026-11-10 | P | https://www.ocrolus.com/pricing/ |
| S53 | Hyperscience pricing | ERP Research | 2026 | S | https://erpresearch.com/erp-add-ons/ocr/hyperscience/pricing |
| S54 | ABBYY Vantage pricing | ERP Research | 2026 | S | https://erpresearch.com/erp-add-ons/ocr/abbyy-vantage/pricing |
| S55 | G-Cloud 15 pricing document (ABBYY Vantage) | UK Digital Marketplace | 28 Jan 2026 | P | https://assets.applytosupply.digitalmarketplace.service.gov.uk/g-cloud-15/documents/720427/153701239400241-pricing-document-2026-01-28-2049.pdf |
| S56 | Rossum pricing | Rossum | accessed 2026-11-10 | P | https://rossum.ai/pricing/ |
| S57 | Docsumo pricing | Docsumo | accessed 2026-11-10 | P | https://www.docsumo.com/pricing |
| S58 | Nanonets pricing | Nanonets | accessed 2026-11-10 | P | https://nanonets.com/pricing |
| S59 | Perfios clients and funding (profile) | PrivateCircle; multiples.vc | Jul 2025 | S | https://blog.privatecircle.co/?p=58199169 ; https://multiples.vc/private-comps/perfios-software-solutions |
| S60 | IDfy secures ~$52M round | Mobile ID World | n.d. | S | https://www.mobileidworld.com/idfy-secures-52m-round-to-grow-kyc-and-digital-trust-services-in-india/ |
| S61 | How IDfy has grown from a BGV provider… | YourStory | Aug 2025 | S | https://yourstory.com/2025/08/idfy-from-kyc-provider-to-verification-fraud-prevention-firm |
| S62 | Signzy raises $26 million | Signzy | 2022 | P | https://www.signzy.com/blogs/no-code-ai-platform-signzy-raises-26-million |
| S65 | DPDP Rules 2025 explanatory document | PIB, Government of India | Nov 2025 | P | https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc20251117695301.pdf |
| S66 | Digital Personal Data Protection Rules 2025 notified | Mondaq | Nov 2025 | S | https://www.mondaq.com/india/data-protection/1708164/digital-personal-data-protection-rules-2025-notified |
| S68 | AppZen profile (Series D, competitors) | Sacra | 2025–26 | S | https://sacra.com/c/appzen/ |
| S69 | AppZen spend audit | AppZen | accessed 2026-11-10 | P | https://www.appzen.com/spend-audit-software |
| S70 | EY Document Anomaly & Transaction Analytics | EY India | n.d. | P | https://www.ey.com/en_in/services/forensic-integrity-services/document-anomaly-transaction-analytics |
| S71 | Irame.ai raises $1 million | Indian Startup News | Mar 2025 | S | https://indianstartupnews.com/funding/irameai-an-ai-powered-enterprise-productivity-and-audit-intelligence-platform-raises-1-million-8889806 |
| S72 | AuditCue raises $1.5M seed led by Kalaari | IBS Intelligence | n.d. | S | https://ibsintelligence.com/ibsi-news/indias-auditcue-raises-1-5m-in-seed-round-led-by-kalaari-capital/ |
| S73 | Audit Automation Pro (use case listing) | ICAI AI portal | n.d. | P | https://ai.icai.org/usecases_details.php?id=174 |
| S74 | CORAA AI profile | village.ai | n.d. | S | https://village.ai/company/coraa-ai |
| S76 | DocILE benchmark (ICDAR 2023 / CLEF 2023) | Rossum / DocILE authors | 2023 | P | https://docile.rossum.ai/ |
| S78 | Forensic audit reports must meet statutory standards | SupremeToday | Jun 2026 | S | https://supremetoday.ai/forensic-audit-reports-must-meet-statutory-standards-20260630019 |
