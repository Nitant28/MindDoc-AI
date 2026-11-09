# MindDoc AI: Benchmark Datasets and a Synthetic Investigation Benchmark

*Research date: 2026-11-10. Companion files: [RESEARCH_PAPERS.md](RESEARCH_PAPERS.md) and [RESEARCH_GAPS.md](RESEARCH_GAPS.md).*

**This is not legal advice.** License fields record what the dataset's official page, repository or dataset card states. Where that could not be confirmed this session, the field says **unverified**. Before any commercial demo, read the license file shipped with the data and check the terms of the underlying documents. Several datasets wrap third-party content (Wikipedia, news, tobacco-litigation archives, crawled charts) that carries its own terms.

## MindDoc layers used below

| Code | Layer |
|---|---|
| **L1** | Multimodal document understanding: parsing, OCR, layout, tables, key-information extraction (KIE), classification, charts |
| **L2** | Evidence-backed temporal KG: extraction, entity resolution (ER), temporal facts, confidence |
| **L3** | Retrieval: hybrid BM25+dense, RRF, graph expansion, reranking |
| **L4** | ML anomaly discovery |
| **L5** | Agentic investigation: answers, numeric reasoning, citations, contradictions, robustness |
| **L6** | Human review: calibration and prioritization |

Commercial or demo use is shown as **Yes** (permissive, attribution required), **Yes-SA** (allowed, but share-alike or copyleft obligations apply), **No** (non-commercial only), or **Unverified**.

---

## 1. Requested datasets

### 1.1 Overview

| Dataset | What it measures | Size | License (as stated) | Commercial / demo | Layer | Metric to report |
|---|---|---|---|---|---|---|
| **DocVQA** (Mathew, Karatzas, Jawahar, WACV 2021) | Extractive QA on document images | 50,000 Q / 12,767 images. Train 39,463 Q / 10,194 img; val 5,349 / 1,286; test 5,188 / 1,287 | Terms are on the RRC challenge portal (login required). **Unverified.** HF mirrors tag MIT, but that is the mirror's own claim. Images come from the UCSF Industry Documents Library. | **Unverified.** Treat as research-only. | L1, L5 | ANLS [K] |
| **FUNSD** (Jaume, Ekenel, Thiran, ICDAR-OST 2019) | Form entity labeling (header, question, answer, other) and entity linking | 199 forms; 9,707 entities; 5,304 relations; 31,485 words | "Use of the FUNSD Dataset is solely for non-commercial, research and educational purposes" (EPFL-LTS5 license page) | **No** | L1, L2 (key–value links) | Entity-labeling F1; linking F1 [K] |
| **CORD** (Park et al., NeurIPS 2019 Document Intelligence workshop) | Receipt parsing / KIE | 1,000 public receipts (800 / 100 / 100) out of a larger internal collection | CC BY 4.0 (repository and HF card) | **Yes** | L1 | Field-level F1; tree-edit-distance accuracy as in Donut [K] |
| **SROIE** (Huang et al., ICDAR 2019) | Receipt text localization, OCR and KIE (company, address, date, total) | 1,000 receipt images. The commonly used 626 train / 347 test split could not be verified (it does not sum to 1,000). | **No data license found.** The CC BY 4.0 seen applies to the arXiv paper, not the data. | **Unverified** | L1 | Task 3 field precision, recall and F1 [K] |
| **RVL-CDIP** (Harley, Ufkes, Derpanis, ICDAR 2015) | Document image classification (16 classes) | 400,000 images (320k / 40k / 40k); 38.8 GB | "Other". Subset of IIT-CDIP from the Legacy Tobacco Document Library. The HF card points to that library's copyright terms. | **Unverified** (third-party litigation documents) | L1 | Accuracy, plus an OOD test [K] |
| **FinQA** (Chen et al., EMNLP 2021) | Numerical reasoning programs over earnings-report text and tables | 8,281 QA pairs [K] | MIT (repository, covering code and data). Built on FinTabNet (CDLA-Permissive). | **Yes** | L5, B comparator | Execution accuracy; program accuracy |
| **TAT-QA** (Zhu et al., ACL 2021) | Hybrid table+text financial QA, including scale and units | 16,552 Q over 2,757 hybrid contexts | Data CC BY 4.0; repository MIT | **Yes** | L5, B comparator | EM and numeracy-aware F1 [K] |
| **CUAD** (Hendrycks et al., NeurIPS 2021 Datasets & Benchmarks) [K] | Contract clause extraction (41 clause types) | 510 contracts; 13,000+ labels | CC BY 4.0 | **Yes** | L1, L2 (contract facts into the KG), L5 | AUPR; precision at 80% recall [K] |
| **DocLayNet** (Pfitzmann et al., KDD 2022) [K] | Page layout segmentation | 80,863 pages; 11 classes; 6 categories (financial reports, scientific articles, laws and regulations, government tenders, manuals, patents) | CDLA-Permissive-1.0 | **Yes** | L1 | COCO mAP@[0.5:0.95] [K] |
| **PubTables-1M** (Smock, Pesala, Abraham, CVPR 2022) [K] | Table detection and table structure recognition | 947,642 cropped tables (structure); 575,305 pages (detection); 117 GB | CDLA-Permissive-2.0 | **Yes** | L1 | GriTS (structure); AP (detection) [K] |
| **MultiHop-RAG** (Tang, Yang, COLM 2024) | Multi-document RAG over news: inference, comparison, temporal and null queries | 2,556 queries; evidence spans 2–4 documents | ODC-BY | **Yes**. ODC-BY covers the database. Check copyright on the news text. | L3, L5, E | Retrieval MRR@k, MAP@k, Hits@k; answer accuracy [K] |
| **HotpotQA** (Yang et al., EMNLP 2018) [K] | Multi-hop QA with supporting facts | About 113k questions [K]; distractor and fullwiki settings | CC BY-SA 4.0 | **Yes-SA** | L3, L5, E | Answer EM/F1; supporting-fact EM/F1; joint EM/F1 |
| **2WikiMultihopQA** (Ho et al., COLING 2020) | Multi-hop QA with evidence triples (the reasoning path) | About 192k questions [K]; 402 MB | Apache-2.0 (HF card; GitHub LICENSE not checked) | **Yes** | L2, L3, E | EM/F1; evidence F1 [K] |
| **FEVEROUS** (Aly et al., NeurIPS 2021 Datasets & Benchmarks) | Claim verification with sentence **and table-cell** evidence | 87,026 claims | Data CC BY-SA 3.0 (per Wikipedia terms); code Apache-2.0 | **Yes-SA** | B, L5 | FEVEROUS score (correct label plus complete evidence); label accuracy; evidence recall [K] |
| **TabFact** (Chen et al., ICLR 2020) [K] | Table-based fact verification (entailed vs refuted) | 118k statements over 16k Wikipedia tables | CC BY 4.0 (HF card) | **Yes** | B | Accuracy, overall and on simple and complex subsets [K] |
| **ChartQA** (Masry et al., Findings ACL 2022) | Chart QA with visual and logical reasoning | 9.6k human-written + 23.1k generated questions | Repository GPL-3.0. No separate data license is stated. Charts were crawled from third-party sites. | **Yes-SA / caution.** GPL is copyleft, and chart sources keep their own terms. | L1 (charts), B | Relaxed accuracy, 5% numeric tolerance [K] |

### 1.2 Access and caveats

| Dataset | Access | Caveats |
|---|---|---|
| DocVQA | RRC portal (Single Document VQA → Download tab). A DocVQA2026 version is on HF. | Test answers are withheld, so evaluate through the portal. Answers are extractive spans only. Old industry documents. HF mirror license tags are unreliable. |
| FUNSD | Author site | Tiny (149 train / 50 test [K]). Noisy scans. Revised variants (FUNSD+, by Konfuzio) have their own gated license. **Do not ship in a commercial demo.** |
| CORD | HF `naver-clova-ix/cord-v2` | Indonesian restaurant receipts only. v2 corrected labels and removed some classes. Use v2. |
| SROIE | ICDAR 2019 RRC portal | Known annotation errors, and many unofficial "fixed" copies exist. State which copy you used. |
| RVL-CDIP | HF `aharley/rvl_cdip` | Larson et al. (EACL 2023) estimate **8.1% label noise**, report **train/test overlap**, and found **PII including US SSNs**. Use only as a secondary classification check, never as the headline. |
| FinQA | GitHub `czyssrs/FinQA` | The leaderboard uses a private test set. The DSL programs constrain answers. S&P 500 reports only. |
| TAT-QA | GitHub `NExTplusplus/TAT-QA` | Test ground truth was released in January 2024, so expect contamination in recent LLMs. |
| CUAD | atticusprojectai.org/cuad; HF `theatticusproject/cuad` | Contracts are long. The span-QA framing differs from KG triples, so map clause types to KG predicates explicitly. |
| DocLayNet | HF `ds4sd/DocLayNet` | Layout only, with no reading order or relations. The financial-report category is directly relevant. |
| PubTables-1M | HF `bsmock/pubtables-1m` | Scientific articles only, so expect a domain gap on invoices and financial statements. Pair with FinTabNet. |
| MultiHop-RAG | GitHub `yixuantt/MultiHop-RAG` | Queries are generated by an LLM [K]. Good for retrieval and E-direction tests because evidence lists are explicit. |
| HotpotQA | hotpotqa.github.io | Many questions can be solved by shortcuts without multi-hop reasoning [K]. Heavily contaminated. Share-alike applies to redistributed derivatives. |
| 2WikiMultihopQA | GitHub `Alab-NII/2wikimultihop`; HF | Questions are templated. The evidence triples are directly usable as KG gold for L2 and E. |
| FEVEROUS | fever.ai; HF `fever/feverous` | Wikipedia only. Large Wikipedia dump needed. Share-alike applies. |
| TabFact | GitHub `wenhuchen/Table-Fact-Checking`; HF | Wikipedia tables. Statement annotation artifacts [K]. |
| ChartQA | GitHub `vis-nlp/ChartQA`; HF mirrors | Mixed sources (Pew charts were manually annotated). Check source terms before a public demo. |

### 1.3 Additional financial-document sets

| Dataset | Measures | Size | License | Commercial / demo | Layer | Notes |
|---|---|---|---|---|---|---|
| **FinanceBench** (Islam et al., 2023, Patronus AI) | Open-book QA over 10-K/10-Q filings with evidence strings | 10,231 Q about 40 companies. **150-question open sample.** | Open sample CC BY-NC 4.0 (HF card). Full set must be licensed from Patronus. | **No** | L5 | Too small to rank systems. Use for qualitative demos only under NC terms. |
| **FinTabNet** (IBM) | Table structure in S&P 500 annual reports | Large [K] | CDLA-Permissive. The version is ambiguous: the original says "CDLA-Permissive", and the HF fork `FinTabNet.c` is tagged 2.0. | **Yes** (check LICENSE.txt) | L1 (financial tables) | Best in-domain complement to PubTables-1M. Report GriTS or TEDS [K]. |
| **ConvFinQA** (Chen et al., EMNLP 2022) | Conversational chains of numerical reasoning | 3,892 conversations, 14,115 Q (secondary listing) | MIT per a secondary listing. **Unverified**, so check `czyssrs/ConvFinQA`. | Unverified | L5 | Multi-turn numeric reasoning. |
| **FinDVer** (Zhao et al., EMNLP 2024) | Claim verification over long hybrid financial documents | 2,400 (arXiv v1) or 4,000 (ACL version) | **Unverified** | Unverified | B, L5 | Closest public set to B's financial setting. |
| **VRDU** (Wang et al., KDD 2023) | KIE on registration forms (FARA) and ad-buy forms (FCC), including nested line items | Not checked | "Creative Commons" per Google's blog. **Variant unverified.** | Unverified | L1 | Tests template generalization and repeated fields, which matter for invoice line items. |
| **FATURA** (Limam, Dhiaf et al., 2023) | KIE on synthetic invoice images | 10,000 invoices; 50 layouts; 24 classes | CC BY-NC-SA 4.0 per a secondary listing. **Check Zenodo.** | Likely **No** | L1 | Synthetic templates. Useful for invoice KIE dev, but not for headline results. |
| SEC EDGAR filings (raw source) | — | — | US-government-hosted public filings. Reuse terms **not checked** this session. | Likely yes, check | L1–L5 case studies | Natural copying between filings and press releases, which is useful for Direction A. |

### 1.4 Entity-resolution sets and generators

| Dataset / tool | Measures | License | Commercial / demo | Layer | Notes |
|---|---|---|---|---|---|---|
| Magellan / DeepMatcher benchmark (Abt-Buy, Amazon-Google, DBLP-ACM, DBLP-Scholar, Walmart-Amazon, iTunes-Amazon, Beer, Fodors-Zagat) [K] | Pairwise entity matching | Varies, often unstated [K] | Unverified, so research use | L2 | Standard comparison with Ditto. Report pairwise F1 with the published splits. |
| **WDC Products** (Peeters, Der, Bizer, EDBT 2024) | EM varying corner cases, unseen entities and training size (27 variants) | **Not found** | Unverified | L2 | Best test of generalization to *unseen* entities. |
| **Febrl** data generator (Christen) | Synthetic person and address records with corruption (nicknames, misspellings) | Distributed with Febrl. Exact license not checked [K]. | Unverified | L2, synthetic benchmark | Use as a design reference for name-variant injection. |
| **GeCo** (Christen & Vatsalan, CIKM 2013) | Flexible generation and corruption of personal data | Not checked | Unverified | Synthetic benchmark | Corruption models for realistic duplicates. |
| **Splink** | Fellegi–Sunter baseline with demo datasets | MIT [K] | Yes [K] | L2 baseline | Unsupervised. Runs on DuckDB on CPU. |

### 1.5 Anomaly-detection sets

| Dataset | Measures | Size | License | Commercial / demo | Layer | Notes |
|---|---|---|---|---|---|---|
| **IBM AMLworld** (Altman et al., NeurIPS 2023 Datasets & Benchmarks) | Synthetic AML transactions with complete labels | HI/LI × Small/Medium/Large. LI-Large is about 176M transactions, HI-Large about 180M. | Data **CDLA-Sharing-1.0**; repository Apache-2.0 | **Yes-SA** | L4 | Report minority-class F1 and AUPRC. Laundering is rare (about 1 in 1,750 in LI-Large). Start with the Small variants on CPU. |
| **ADBench** (Han et al., NeurIPS 2022 Datasets & Benchmarks) | 57 tabular AD datasets, 30 algorithms | — | Original licenses per dataset (not checked) | Unverified | L4 | Sanity-check the IF/LOF/PyOD baselines. |
| **GADBench** (Tang et al., NeurIPS 2023 Datasets & Benchmarks) | Supervised graph anomaly detection, 10 datasets | Up to about 6M nodes | Not checked | Unverified | L4 (graph) | XGB-Graph is the baseline to beat. |
| ULB credit-card fraud, Elliptic, PaySim [K] | Transaction fraud | — | **Not checked** this session | Unverified | L4 | Widely used, but verify the Kaggle terms first. |

### 1.6 Research-direction sets (licenses mostly unverified)

| Direction | Sets | License status |
|---|---|---|
| A | Text2KGBench (CC BY 4.0 on Zenodo, per search [P]); CONFLICTS (`google-research-datasets/rag_conflicts`); RAMDocs (`HanNight/RAMDocs`) | CONFLICTS and RAMDocs unverified |
| B | SciTab, ChartCheck, MOCHEG (data CC BY 4.0, code Apache-2.0 [V]), MMIR, PRISMM-Bench, ContraDoc, QuanTemp | All except MOCHEG unverified |
| C | MATRES, OmniTemp, TimeQA, ToT (HF `baharef/ToT`), LongMemEval, SemEval-2015 TimeLine | Unverified |
| D | QuestBench (`google-deepmind/questbench`), MediQ | Unverified |
| E | ALCE (built on ASQA, QAMPARI, ELI5), AttributionBench, AIS data, CUE-R and EviScope protocols | Unverified |

---

## 2. Evaluation map by layer

| Layer | First-line datasets | Metrics | Main comparison |
|---|---|---|---|
| L1 | DocLayNet, PubTables-1M + FinTabNet, CORD, DocVQA (research only), ChartQA, CUAD | mAP; GriTS/TEDS; field F1; ANLS; relaxed accuracy | MindDoc CV pipeline vs off-the-shelf parsers (report parser versions) |
| L2 | CUAD (clause→fact), Text2KGBench, 2Wiki evidence triples, WDC Products / DeepMatcher, MATRES, synthetic benchmark | Triple P/R/F1; ER pairwise and B³ F1; temporal relation F1; **ECE/Brier** of fact confidence | GraphRAG and KGGen extraction; Splink and Ditto for ER |
| L3 | MultiHop-RAG, HotpotQA, 2WikiMultihopQA, synthetic benchmark | Recall@k, nDCG@10, MRR; evidence-set recall | BM25, dense, hybrid+RRF, +contextual chunks, +rerank, GraphRAG, LightRAG, HippoRAG (split by question type) |
| L4 | AMLworld (Small), ADBench subset, GADBench, synthetic benchmark | AUPRC, P@k, Recall@k at an analyst budget | IF, LOF, PyOD defaults, XGB-Graph |
| L5 | TAT-QA, FinQA, FEVEROUS, TabFact, FinDVer, synthetic benchmark | EM/F1, execution accuracy, FEVEROUS score, **citation P/R**, **unsupported-claim rate**, finding P/R, pass^k, $ per task | Plain RAG, GraphRAG, single-agent ReAct without the KG |
| L6 | Synthetic benchmark (gold truth known) | ECE, Brier, errors caught @k reviews | Uniform vs confidence-sorted vs fragility-sorted review queues |

---

## 3. Protocol: synthetic "investigation" benchmark (working name *InvestBench*)

### 3.1 Goals

- Provide **complete, machine-generated ground truth** for every layer at once: entities, facts with validity intervals, documents, locators, injected issues, investigation questions, gold findings and their support sets. This makes contradiction P/R, ER F1, citation correctness, unsupported-claim rate, fragility (E) and acquisition value (D) all computable without manual labeling.
- Make the benchmark **regenerable bit-for-bit** from a seed and a versioned generator, and also **ship the rendered artifacts**, because rasterization and LLM prose are not perfectly deterministic across platforms.
- Contain **no real personal or company data**.

### 3.2 Generation method

1. **World sampler** (seeded). Each *universe* contains:
   - 10–40 companies (legal name, registration ID, VAT ID, addresses, directors, bank accounts),
   - 20–80 persons,
   - relationships: ownership, directorship, employment, vendor-of, customer-of.
2. **Business-process simulator.** A discrete-event simulation over 12–24 months at daily granularity. It emits a canonical **event log** with valid-time intervals covering:
   - contract signed, amended, renewed or terminated,
   - purchase order, delivery, invoice, credit note,
   - payment (full, partial or split),
   - registry change (address, director),
   - email or memo.

   This log is the single source of truth.
3. **Document renderers.** Each event maps to 0..n documents across modalities:
   - Born-digital PDF from templates, at least 5 layout families per document type.
   - Scanned image: rasterized at 150–300 dpi, then augmented with rotation up to ±3°, blur, JPEG compression, noise, stamps and signatures.
   - Spreadsheet ledgers (CSV/XLSX).
   - Charts: matplotlib PNG of monthly spend or revenue, with the data table kept as gold.
   - Structured registry records (JSON/CSV).
   - Narrative text: templates, or LLM-written prose that is **cached and shipped**.

   Every rendered value carries a **locator**: page and bounding box, character span, table cell, or chart mark.
4. **Source model.** Each document has a source (vendor portal, bank, registry, internal ERP, email). Each source has an accuracy parameter. A `derived_from` link records copying, for example a memo that restates an invoice *including its error*.

### 3.3 Injection catalogue (all logged with IDs)

| Family | Injection | Gold label | Difficulty knobs |
|---|---|---|---|
| Contradictions | Invoice total ≠ sum of line items; invoice amount ≠ contract rate × quantity; payment ≠ invoice; registry address ≠ letterhead address; chart bar ≠ ledger value; stamped date on a scan ≠ typed date | Pair of locators, type, true value | Relative size of the difference (0.5–50%), modality pair, document distance, OCR degradation |
| **Benign variations** (negatives) | Contract amendment changes the rate; partial payments summing to the invoice; credit note; FX conversion at the dated rate; rounding; "in thousands" scale | `explained_by` link to the explaining document | Same frequency as the true contradictions, so FP rate is measurable |
| Duplicate entities | Name variants ("Ltd"/"Limited", typos, token reorder, transliteration, abbreviations); shared address, phone or bank account; **hard negatives** (similar names, different entities) | Gold entity clusters | Corruption rate per field; share of hard negatives |
| Timeline breaks | Payment before contract start; invoice after termination; director appointed after signing; backdated document (DCT < described event); missing expected monthly invoice | Minimal conflicting set of facts | Date granularity (day, month, quarter); number of hops |
| Anomalies (L4) | Split payments under an approval threshold; round-tripping between related parties; duplicate invoice numbers; vendor shares an address or bank account with an employee; off-cycle payments | Anomalous transactions and subgraphs | Prevalence (0.1–2%); camouflage |
| Dependence (A) | Copied or paraphrased restatements of one source, including copied errors | `derived_from` graph | Copy rate 0–80%; paraphrase strength |
| Withheld evidence (D) | A fraction of documents is hidden and keyed to a typed acquisition action with a cost | Action → document map, cost | Hidden fraction; cost spread |

### 3.4 Ground-truth labeling

- **Automatic labels.** All labels are derived from the event log and the injection log. No manual labeling is needed. Files (JSONL, with a schema version in each record):
  - `entities.jsonl`: gold clusters and mention IDs.
  - `facts.jsonl`: canonical facts with validity intervals.
  - `documents.jsonl`: ID, modality, source, `derived_from`, render parameters, SHA-256.
  - `mentions.jsonl`: mention to locator.
  - `injections.jsonl`: type, involved mentions, explanation, `explained_by`.
  - `questions.jsonl`: investigation tasks with gold findings, gold support sets and gold minimal deletion sets for E.
  - `acquisitions.jsonl`: for D.
- **Recoverability check.** After rendering, run a reference OCR/parse. Mark an injection **unrecoverable** if its evidence is illegible (for example, the OCR misses the value entirely). Report metrics on recoverable items, and report the unrecoverable rate separately.
- **Human audit.** Two annotators independently check a stratified 5% sample (at least 200 items): is the evidence visible, is the label right, is the "benign" variation really benign? Report Cohen's κ and fix the generator rather than the labels.
- **Artifact audit.** Train a shallow classifier on surface features (template ID, file size, font, position) to predict "contains an injection". If AUROC is above 0.6, randomize placement and templates until the injections cannot be detected from surface features.

### 3.5 Metrics

| Metric | Definition |
|---|---|
| **Contradiction P/R/F1** | A predicted pair is a TP if both locators overlap the gold locators (bounding-box IoU ≥ 0.5, character-span overlap ≥ 50%, or the same table cell) and the type matches. Report micro and macro averages per modality pair, plus P@k and R@k for k ∈ {10, 25, 50}. |
| **FP rate on benign variations** | Fraction of benign-variation pairs flagged as contradictions. This is the usability metric. |
| **Entity-resolution F1** | Pairwise P/R/F1 and B³ F1 over mention clusters. Report the hard-negative subset separately. |
| **Timeline** | Endpoint MAE in days, interval coverage vs width, and timeline-break P/R (overlap with the gold minimal set). |
| **Anomaly** | AUPRC; P@k and Recall@k at the analyst budget. |
| **Citation correctness** | *Citation precision*: fraction of citations whose cited locator overlaps a gold support locator **and** entails the claim (NLI or LLM judge validated against humans). *Citation recall*: fraction of claims with at least one correct citation. This is ALCE-style but anchored to generator gold, so it is stricter. |
| **Unsupported-claim rate** | Split the final report into atomic claims (FActScore-style). A claim is supported only if a cited locator entails it **and** it agrees with `facts.jsonl`. Rate = unsupported / total. Also report the hallucinated-entity rate (entities not in gold). |
| **Finding P/R** | A predicted finding matches gold on finding type, entity cluster and time window. |
| **Reliability and cost** | pass^k over at least 3 runs; tokens, $ and wall time per investigation. |
| **Calibration** | ECE and Brier for fact and finding confidence. |
| **E / D specific** | Fragility estimation metrics (RESEARCH_GAPS.md §5f) and decision accuracy vs cost (§4f). |

### 3.6 Reproducibility and versioning

1. **Seeds.**
   - One master seed per release. Derive per-universe and per-module streams with `numpy.random.SeedSequence(master).spawn(n)`.
   - Seed `Faker` per instance and Python `random` explicitly.
   - Ban unseeded global RNG calls with a lint check.
2. **Pinned environment.**
   - Lockfile for Python packages.
   - Fonts bundled in the repository (no system fonts).
   - Renderer library versions recorded in the manifest.
3. **Manifest.** `manifest.json` lists generator version (semver), config hash, master seed, and per-file SHA-256. CI regenerates a small tier and diffs the hashes for the deterministic files.
4. **Ship artifacts, not only code.** Rasterized images and any LLM-written prose are released as files, with model ID and generation date for the prose. Regeneration is a check, not a requirement.
5. **Versioning.**
   - `vMAJOR.MINOR.PATCH`. MAJOR means label semantics changed, MINOR means new universes or injection types, PATCH means bug fixes.
   - Never overwrite a released version. Host on Git LFS, DVC or the HF Hub, with a datasheet and dataset card.
6. **Splits.**
   - Dev and test are split by universe seed.
   - **Template holdout**: some layout families appear only in test.
   - A frozen, private-seed test tier is kept for final numbers. Metric definitions and baselines are pre-registered before it is touched.
7. **Tiers.**
   - S: 5 universes, for CI smoke tests.
   - M: 50 universes, about 2–4k documents, for dev and test.
   - L: 200 universes, for scaling curves.

   Each tier is also released at difficulty levels (easy, medium, hard), set by the knobs in §3.3.
8. **Privacy and safety.**
   - Use Faker names, then filter against a list of well-known real company names.
   - Use clearly fictitious bank codes and registration-number formats.
   - State in the card that any resemblance to real entities is coincidental.
9. **Benchmark license.** The owner chooses. A suggested choice is CC BY 4.0 for data and Apache-2.0 or MIT for the generator, which avoids the NC and SA constraints found in §1.

### 3.7 Threats to validity

- **Synthetic-to-real gap.** Pair every headline result with at least one real-document study, for example CUAD, FinQA or TAT-QA, or EDGAR case studies.
- **Generator artifacts.** These are addressed by the artifact audit (§3.4), the template holdout and equal-frequency benign variations.
- **LLM-written prose leaking labels.** Keep injections in structured fields and templates. Use LLM prose only for narrative context, and audit it.
- **Judge circularity.** The judge model must differ from the system model, and it must be human-validated (see RESEARCH_GAPS.md §8).

---

## Sources

- DocVQA: https://arxiv.org/abs/2007.00398 · https://site.docvqa.org/datasets/docvqa · https://www.docvqa.org/
- FUNSD: https://guillaumejaume.github.io/FUNSD/ · https://guillaumejaume.github.io/FUNSD/work/ · https://arxiv.org/abs/1905.13538
- CORD: https://github.com/clovaai/cord · https://huggingface.co/datasets/naver-clova-ix/cord-v2
- SROIE: https://arxiv.org/abs/2103.10213 · https://github.com/zzzDavid/ICDAR-2019-SROIE
- RVL-CDIP: https://huggingface.co/datasets/aharley/rvl_cdip · https://aclanthology.org/2023.eacl-main.195
- FinQA: https://github.com/czyssrs/FinQA · https://arxiv.org/abs/2109.00122
- TAT-QA: https://github.com/NExTplusplus/TAT-QA
- CUAD: https://www.atticusprojectai.org/cuad · https://huggingface.co/datasets/theatticusproject/cuad
- DocLayNet: https://huggingface.co/datasets/ds4sd/DocLayNet
- PubTables-1M: https://huggingface.co/datasets/bsmock/pubtables-1m
- MultiHop-RAG: https://github.com/yixuantt/MultiHop-RAG · https://arxiv.org/abs/2401.15391
- HotpotQA: https://hotpotqa.github.io/
- 2WikiMultihopQA: https://huggingface.co/datasets/xanhho/2WikiMultihopQA · https://aclanthology.org/2020.coling-main.580
- FEVEROUS: https://arxiv.org/abs/2106.05707 · https://huggingface.co/datasets/fever/feverous
- TabFact: https://huggingface.co/datasets/wenhu/tab_fact
- ChartQA: https://github.com/vis-nlp/ChartQA · https://aclanthology.org/2022.findings-acl.177/
- FinanceBench: https://huggingface.co/datasets/PatronusAI/financebench · https://arxiv.org/abs/2311.11944 · https://docs.patronus.ai/docs/research_and_differentiators/financebench
- FinTabNet: https://developer.ibm.com/exchanges/data/all/fintabnet · https://huggingface.co/datasets/bsmock/FinTabNet.c
- ConvFinQA: https://aclanthology.org/2022.emnlp-main.421 · https://paperswithcode2.com/dataset/6848
- FinDVer: https://aclanthology.org/2024.emnlp-main.818
- VRDU: https://arxiv.org/abs/2211.15421 · https://research.google/blog/advances-in-document-understanding/
- FATURA: https://arxiv.org/abs/2311.11856 · https://zenodo.org/records/10371464
- WDC Products: https://arxiv.org/abs/2301.09521
- Febrl / GeCo: https://users.cecs.anu.edu.au/~Peter.Christen/Febrl/febrl-0.3/febrldoc-0.3/node70.html · https://users.cecs.anu.edu.au/~christen/publications/christen2013cikm.pdf
- Splink: https://ijpds.org/article/view/1794
- IBM AMLworld: https://arxiv.org/abs/2306.16424 · https://github.com/IBM/AML-Data
- ADBench: https://arxiv.org/abs/2206.09426 · GADBench: https://arxiv.org/abs/2306.12251
- MOCHEG license: https://github.com/VT-NLP/Mocheg · Text2KGBench: https://arxiv.org/abs/2308.02357
- Evaluation methodology referenced: https://arxiv.org/abs/2305.14627 (ALCE) · https://arxiv.org/abs/2406.12045 (τ-bench pass^k) · https://arxiv.org/abs/2407.01502 (cost reporting)
