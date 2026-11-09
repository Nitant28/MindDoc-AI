# MindDoc AI: Prior Work for Five Candidate Research Directions

*Research date: 2026-11-10. Companion files: [RESEARCH_GAPS.md](RESEARCH_GAPS.md) (gap, problem statement, method, experiments, verdict) and [BENCHMARK_DATASETS.md](BENCHMARK_DATASETS.md).*

This file covers items (a) key prior work and (b) open-source implementations for each direction, plus the baselines MindDoc will be compared against. It makes no novelty claims. Each direction ends with the closest prior work; the residual gaps are argued in RESEARCH_GAPS.md.

## Verification legend

| Tag | Meaning |
|---|---|
| **[V]** | Title, authors, year and venue/ID checked against an official or primary page during this session (arXiv, ACL Anthology, PMLR, NeurIPS/ICLR/USENIX/VLDB proceedings, author PDF). |
| **[P]** | Partly verified. The paper exists (arXiv ID or listing seen), but some field (full author list, final venue or a number) came only from a secondary summary. Check it before you cite. |
| **[K]** | Well-established work cited from prior knowledge and not re-fetched this session. Bibliographic details are believed correct, but confirm them before camera-ready. |

**Coverage limits.** The shared web-search budget ran out before these targeted searches were done: (1) benchmarks for reconstructing timelines from contradictory documents, (2) text–table numeric inconsistency detection in financial reports, (3) provenance/lineage tracking for LLM agent pipelines. Close prior work may exist there that is not listed. Run those three searches before committing to a paper (see RESEARCH_GAPS.md §7).

---

## A. Evidence-calibrated knowledge-graph construction

### A.1 Truth discovery, source reliability and source dependence

| Work | Authors | Year / venue | Link | Contribution | Tag |
|---|---|---|---|---|---|
| Truth Discovery with Multiple Conflicting Information Providers on the Web (TruthFinder) | X. Yin, J. Han, P. S. Yu | KDD 2007; extended TKDE 20(6) 2008 | [doi:10.1145/1281192.1281309](https://doi.org/10.1145/1281192.1281309) | Iterative mutual reinforcement: a source is trustworthy if it gives many true facts, and a fact is believable if trustworthy sources give it. | [V] |
| Integrating Conflicting Data: The Role of Source Dependence | X. L. Dong, L. Berti-Equille, D. Srivastava | PVLDB 2(1), 2009 | [pdf](https://lunadong.com/publication/dependence_vldb.pdf), [doi:10.14778/1687627.1687690](https://doi.org/10.14778/1687627.1687690) | Bayesian detection of copying between sources from one snapshot (sharing false values is evidence of copying), plus truth discovery that discounts dependent votes. | [V] |
| Truth Discovery and Copying Detection in a Dynamic World | X. L. Dong, L. Berti-Equille, D. Srivastava | PVLDB 2(1), 2009 | [pdf](https://lunadong.com/publication/lifespan_vldb.pdf), [doi:10.14778/1687627.1687691](https://doi.org/10.14778/1687627.1687691) | Truth that changes over time. Models source coverage, exactness and freshness, and uses an HMM to infer copying and when it happened. | [V] |
| Corroborating Information from Disagreeing Views | A. Galland, S. Abiteboul, A. Marian, P. Senellart | WSDM 2010 | [doi:10.1145/1718487.1718504](https://doi.org/10.1145/1718487.1718504) | Fixpoint algorithms for corroboration that jointly estimate source error rates and fact truth. | [K] |
| Knowing What to Believe (when you already know something) | J. Pasternack, D. Roth | COLING 2010 | [ACL C10-1099](https://aclanthology.org/C10-1099/) | Generalized fact-finders that use prior knowledge and constraints. | [K] |
| A Bayesian Approach to Discovering Truth from Conflicting Sources for Data Integration (LTM) | B. Zhao, B. Rubinstein, J. Gemmell, J. Han | PVLDB 5(6), 2012 | [arXiv:1203.0058](https://arxiv.org/abs/1203.0058) | Latent Truth Model. Separates false-positive and false-negative source quality, and supports multi-valued truths. | [P] |
| Truth Finding on the Deep Web: Is the Problem Solved? | X. Li, X. L. Dong, K. Lyons, W. Meng, D. Srivastava | PVLDB 6(2), 2012 | [arXiv:1503.00303](https://arxiv.org/abs/1503.00303) | Empirical study on Stock and Flight data showing that copying and low-quality sources break naive fusion. | [P] |
| Resolving Conflicts in Heterogeneous Data by Truth Discovery and Source Reliability Estimation (CRH) | Q. Li, Y. Li, J. Gao, B. Zhao, W. Fan, J. Han | SIGMOD 2014 | [doi:10.1145/2588555.2610509](https://doi.org/10.1145/2588555.2610509) | Optimization framework covering mixed data types (categorical and continuous). | [K] |
| Knowledge Vault: A Web-Scale Approach to Probabilistic Knowledge Fusion | X. L. Dong, E. Gabrilovich, G. Heitz, W. Horn, N. Lao, K. Murphy, T. Strohmann, S. Sun, W. Zhang | KDD 2014 | [Google Research](https://research.google/pubs/pub45634/), [doi:10.1145/2623330.2623623](https://doi.org/10.1145/2623330.2623623) | Fuses extractions from text, tables, page structure and annotations with KB-derived priors to give calibrated probabilities of fact correctness. | [V] |
| Knowledge-Based Trust: Estimating the Trustworthiness of Web Sources | X. L. Dong, E. Gabrilovich, K. Murphy, V. Dang, W. Horn, C. Lugaresi, S. Sun, W. Zhang | PVLDB 8(9), 2015 | [arXiv:1502.03519](https://arxiv.org/abs/1502.03519) | Multi-layer model that separates **extraction error** from **source error**. Estimates the trustworthiness of 119M pages from 2.8B extracted facts. | [V] |
| A Survey on Truth Discovery | Y. Li, J. Gao, C. Meng, Q. Li, L. Su, B. Zhao, W. Fan, J. Han | SIGKDD Explorations 17(2), 2015 | [arXiv:1505.02463](https://arxiv.org/abs/1505.02463) | Standard taxonomy: source reliability, dependence, long-tail data, temporal truth. | [V] |

### A.2 KG confidence, uncertainty and calibration

| Work | Authors | Year / venue | Link | Contribution | Tag |
|---|---|---|---|---|---|
| Embedding Uncertain Knowledge Graphs (UKGE) | X. Chen, M. Chen, W. Shi, Y. Sun, C. Zaniolo | AAAI 2019 | [arXiv:1811.10667](https://arxiv.org/abs/1811.10667) | KG embeddings that regress per-triple confidence scores. | [K] |
| Probability Calibration for Knowledge Graph Embedding Models | P. Tabacof, L. Costabello | ICLR 2020 | [arXiv:1912.10000](https://arxiv.org/abs/1912.10000) | KGE scores are miscalibrated. Platt and isotonic calibration work even without ground-truth negatives. | [V] |
| Evaluating the Calibration of Knowledge Graph Embeddings for Trustworthy Link Prediction | T. Safavi, D. Koutra, E. Meij | EMNLP 2020 | [ACL 2020.emnlp-main.667](https://aclanthology.org/2020.emnlp-main.667) | Calibration that works under the closed-world assumption degrades under the open-world one. A human study shows calibrated scores help people complete a KG. | [V] |
| Uncertainty Management in the Construction of Knowledge Graphs: a Survey | L. Jarnac, Y. Chabot, M. Couceiro | arXiv 2024 | [arXiv:2405.16929](https://arxiv.org/abs/2405.16929) | Covers uncertainty across extraction, alignment and fusion. Notes that extraction uncertainty is often ignored in fusion. | [V] |
| Just Ask for Calibration | K. Tian et al. | EMNLP 2023 | [arXiv:2305.14975](https://arxiv.org/abs/2305.14975) | Verbalized confidence from RLHF LLMs can be better calibrated than token probabilities. | [K] |
| Can LLMs Express Their Uncertainty? | M. Xiong et al. | ICLR 2024 | [arXiv:2306.13063](https://arxiv.org/abs/2306.13063) | Benchmarks verbalized, consistency-based and hybrid confidence elicitation. LLMs are overconfident. | [K] |
| Language Models with Conformal Factuality Guarantees | C. Mohri, T. Hashimoto | ICML 2024 | [arXiv:2402.10978](https://arxiv.org/abs/2402.10978) | Conformal back-off of claims to reach a target factuality rate. | [K] |

### A.3 LLM-based KG construction and its quality

| Work | Authors | Year / venue | Link | Contribution | Tag |
|---|---|---|---|---|---|
| Text2KGBench | N. Mihindukulasooriya, S. Tiwari, C. F. Enguix, K. Lata | ISWC 2023 (Resources) | [arXiv:2308.02357](https://arxiv.org/abs/2308.02357) | Ontology-driven text-to-KG benchmark (Wikidata-TekGen, DBpedia-WebNLG). Seven metrics cover fact quality, ontology conformance and hallucination. | [V] |
| Extract, Define, Canonicalize (EDC) | B. Zhang, H. Soh | EMNLP 2024 | [ACL 2024.emnlp-main.548](https://aclanthology.org/2024.emnlp-main.548/) | Open IE, then schema definition, then post-hoc canonicalization. Handles large schemas or no schema. | [V] |
| KGGen: Extracting Knowledge Graphs from Plain Text with Language Models | B. Mo et al. | NeurIPS 2025 | [arXiv:2502.09956](https://arxiv.org/abs/2502.09956) | LLM extraction plus iterative entity and edge clustering. Introduces the MINE benchmark (graph informativeness via downstream QA). | [V] |
| ATOM: Adaptive and Optimized dynamic temporal KG construction using LLMs | Y. Lairgi et al. (full list not verified) | arXiv 2510.22590; reported EACL 2026 Findings | [arXiv:2510.22590](https://arxiv.org/abs/2510.22590) | Atomic-fact decomposition with dual time (observed vs valid). Per the project README, temporal/logical conflict resolution is **not** handled. | [P] |
| EvoKG / EvoReasoner | authors not verified | arXiv 2509.15464 (2025) | [arXiv:2509.15464](https://arxiv.org/abs/2509.15464) | Updates a KG from raw documents, with contradiction resolution for exclusive facts using confidence, source reliability and temporal cues. | [P] |
| Uncertainty-Aware Dynamic Knowledge Graphs for Reliable QA | authors not verified | arXiv 2601.09720 (2026) | [arXiv:2601.09720](https://arxiv.org/abs/2601.09720) | An LLM scores each triple in [0,1]. QA is compared on the full KG vs a high-confidence subgraph (medical domain). | [P] |

### A.4 Knowledge conflicts, source credibility and corroboration in RAG and agents

| Work | Authors | Year / venue | Link | Contribution | Tag |
|---|---|---|---|---|---|
| Knowledge Conflicts for LLMs: A Survey | R. Xu, Z. Qi, Z. Guo, C. Wang, H. Wang, Y. Zhang, W. Xu | EMNLP 2024 | [arXiv:2403.08319](https://arxiv.org/abs/2403.08319) | Taxonomy of context–memory, inter-context and intra-memory conflicts. | [V] |
| Retrieval-Augmented Generation with Conflicting Evidence (RAMDocs, MADAM-RAG) | H. Wang, A. Prasad, E. Stengel-Eskin, M. Bansal | arXiv 2504.13079 (2025) | [arXiv:2504.13079](https://arxiv.org/abs/2504.13079) | Dataset mixing ambiguity, misinformation and noise. Multi-agent debate with one agent per document. | [V] |
| DRAGged into Conflicts (CONFLICTS benchmark) | A. Cattan et al. | arXiv 2506.08500 (2025) | [arXiv:2506.08500](https://arxiv.org/abs/2506.08500) | Taxonomy of conflict types with an expected behaviour for each. 458 expert-annotated instances. The best conflict-type accuracy was about 65%. | [V] |
| Resolving Conflicting Evidence in Automated Fact-Checking (CONFACT) | Z. Ge et al. | IJCAI 2025 | [IJCAI 2025/1073](https://www.ijcai.org/proceedings/2025/1073) | Conflicting evidence from sources of different credibility. Injecting source-credibility information helps RAG fact-checking. | [V] |
| Whose Facts Win? LLM Source Preferences under Knowledge Conflicts | J. Schuster, V. Gautam, K. Markert | arXiv 2601.03746 (2026) | [arXiv:2601.03746](https://arxiv.org/abs/2601.03746) | Models prefer institutional sources, but **repetition** of a low-credibility claim can flip that preference. | [V] |
| **Evidence Laundering: Deep Research Agents Mistake Correlated Sources for Independent Evidence** | R. Zhou, H. Huang, Y. Zheng, J. Luo, Y. Li, Y. Liu, D. Du | EMNLP 2026 (main), pp. 11682–11693 | [ACL 2026.emnlp-main.509](https://aclanthology.org/2026.emnlp-main.509.pdf) | Agents give paraphrased same-origin clusters about as much credence as independent sources. A structural provenance gate that collapses same-origin pages to one effective source reduces the failure. **Closest prior work on the independence part of A.** | [V] |

### A.5 Open-source implementations (A)

| Tool | What it gives you | Link |
|---|---|---|
| Microsoft GraphRAG | LLM entity/relation extraction, community summaries | [github.com/microsoft/graphrag](https://github.com/microsoft/graphrag) |
| KGGen (`pip install kg-gen`) | LLM extraction and clustering-based canonicalization | stair-lab/kg-gen (per [NeurIPS listing](https://mlanthology.org/neurips/2025/mo2025neurips-kggen)) |
| EDC | Extract–define–canonicalize pipeline | [github.com/clear-nus/edc](https://github.com/clear-nus/edc) |
| Text2KGBench | Benchmark and evaluation scripts | [github.com/cenguix/Text2KGBench](https://github.com/cenguix/Text2KGBench) |
| Graphiti (Zep) | Bi-temporal KG engine for agent memory | [github.com/getzep/graphiti](https://github.com/getzep/graphiti) [K] |
| iText2KG / ATOM | Temporal KG construction | [github.com/AuvaLab/itext2kg](https://github.com/AuvaLab/itext2kg) |
| RAMDocs / MADAM-RAG | Conflicting-evidence data and debate baseline | github.com/HanNight/RAMDocs |
| CONFLICTS | Conflict-type benchmark | github.com/google-research-datasets/rag_conflicts |
| Truth-discovery algorithms | No maintained, widely used Python library was found. Classic methods (TruthFinder, ACCU/DEPEN, LTM, CRH) are short enough to reimplement, and comparative studies such as Waguih & Berti-Equille 2014 (arXiv:1409.6428) [K] describe them. | — |

---

## B. Cross-modal contradiction detection

### B.1 Claim verification against tables, charts and multimodal evidence

| Work | Authors | Year / venue | Link | Contribution | Tag |
|---|---|---|---|---|---|
| TabFact | W. Chen et al. | ICLR 2020 | [arXiv:1909.02164](https://arxiv.org/abs/1909.02164) | 118k statements over 16k Wikipedia tables, labeled entailed or refuted. | [K] (data card [V]) |
| INFOTABS | V. Gupta, M. Mehta, P. Nokhiz, V. Srikumar | ACL 2020 | [ACL 2020.acl-main.210](https://aclanthology.org/2020.acl-main.210/) | NLI over semi-structured infobox tables. | [K] |
| FEVEROUS | R. Aly et al. | NeurIPS 2021 Datasets & Benchmarks | [arXiv:2106.05707](https://arxiv.org/abs/2106.05707) | 87,026 claims with evidence from sentences **and** table cells. | [V] |
| SciTab | X. Lu, L. Pan, Q. Liu, P. Nakov, M.-Y. Kan | EMNLP 2023 | [ACL 2023.emnlp-main.483](https://aclanthology.org/2023.emnlp-main.483) | 1.2k expert-verified claims over scientific tables that need compositional reasoning. TAPAS and TAPEX struggle on it. | [V] |
| Reading and Reasoning over Chart Images for Evidence-based Automated Fact-Checking (ChartFC) | M. Akhtar et al. | Findings EACL 2023 | link not verified | Fact-checking claims against chart images. | [K] |
| ChartCheck | M. Akhtar, N. Subedi, V. Gupta, S. Tahmasebi, O. Cocarascu, E. Simperl | Findings ACL 2024 | [ACL 2024.findings-acl.828](https://aclanthology.org/2024.findings-acl.828) | 1.7k real-world charts and 10.5k human-written claims with explanations. | [V] |
| Multimodal Automated Fact-Checking: A Survey | M. Akhtar et al. | Findings EMNLP 2023 | [arXiv:2305.13507](https://arxiv.org/abs/2305.13507) | Pipeline view (claim detection, evidence retrieval, verdict) across text, image, audio and video. Tables and charts are under-covered. | [P] |
| MOCHEG | B. M. Yao, A. Shah, L. Sun, J.-H. Cho, L. Huang | SIGIR 2023 | [arXiv:2205.12487](https://arxiv.org/abs/2205.12487) | End-to-end multimodal fact-checking with explanations. 15,601 claims, 33,880 paragraphs and 12,112 images. | [V] |
| FinDVer | Y. Zhao et al. | EMNLP 2024 | [ACL 2024.emnlp-main.818](https://aclanthology.org/2024.emnlp-main.818) | Explainable claim verification over long, hybrid text+table financial documents. GPT-4o still trails human experts. | [V] |
| QuanTemp | V. Venktesh, A. Anand, A. Anand, V. Setty | arXiv 2403.17169 (2024); venue not verified | [arXiv:2403.17169](https://arxiv.org/abs/2403.17169) | 15,514 real-world **numerical** claims (comparative, statistical, interval, temporal). Best macro-F1 was 58.32. | [P] |

### B.2 Inconsistency and contradiction detection without a given claim

| Work | Authors | Year / venue | Link | Contribution | Tag |
|---|---|---|---|---|---|
| Finding Contradictions in Text | M.-C. de Marneffe, A. Rafferty, C. Manning | ACL 2008 | [ACL P08-1118](https://aclanthology.org/P08-1118/) | Typology of contradictions (antonymy, negation, numeric, factive, structural, world knowledge). | [K] |
| ContraDoc | J. Li, V. Raheja, D. Kumar | NAACL 2024 | [ACL 2024.naacl-long.362](https://aclanthology.org/2024.naacl-long.362) | Self-contradictions within long documents. Numeric and negation contradictions are the easiest, subjective ones the hardest. | [V] |
| MMIR: Multimodal Inconsistency Reasoning | Q. Yan et al. | arXiv 2502.16033 (2025) | [arXiv:2502.16033](https://arxiv.org/abs/2502.16033) | 534 layout-rich artifacts (webpages, slides, posters) with injected inconsistencies, including quantitative chart–text discrepancies. | [V] |
| PRISMM-Bench | L. Selch, Y. Hou, M. J. Mirza, S. Doveh, J. Glass, R. Feris, W. Lin | ICLR 2026 | [arXiv:2510.16505](https://arxiv.org/abs/2510.16505) | 384 reviewer-flagged inconsistencies across text, figures, tables and equations in 353 papers. 21 LMMs score 27.8–53.9%. | [V] |
| Detecting Knowledge Inconsistencies Across Text, Tables, and Knowledge Graphs (Kontrast) | F. Wei, T. Ehrhart, R. Troncy | arXiv 2607.25959 (2026) | [arXiv:2607.25959](https://arxiv.org/abs/2607.25959) | Taxonomy of cross-modal conflicts (granularity, direct conflict, temporal change, KG incompleteness). Compares table answers against Wikidata via Text-to-SPARQL. **Closest prior work on the "no claim given, cross-modal" setting**, but limited to Wikipedia and Wikidata. | [V] |
| Towards Cross-Modal Error Detection with Tables and Images | O. Ovcharenko, S. Schelter | ICML 2025 DataWorld workshop | [arXiv:2510.12383](https://arxiv.org/abs/2510.12383) | Flags table rows that disagree with their paired image. Benchmarks five methods on four e-commerce datasets, and current methods are weak. | [V] |
| DocNLI | W. Yin, D. Radev, C. Xiong | Findings ACL 2021 | [arXiv:2106.09449](https://arxiv.org/abs/2106.09449) | Document-level NLI. | [K] |
| ContractNLI | Y. Koreeda, C. Manning | Findings EMNLP 2021 | [arXiv:2110.01799](https://arxiv.org/abs/2110.01799) | Document-level NLI over NDAs with evidence spans. | [K] |
| AlignScore / MiniCheck | Y. Zha et al. (ACL 2023); L. Tang, P. Laban, G. Durrett (EMNLP 2024) | — | [arXiv:2305.16739](https://arxiv.org/abs/2305.16739), [arXiv:2404.10774](https://arxiv.org/abs/2404.10774) | Cheap factual-consistency checkers usable as NLI components. | [K] |

### B.3 Numerical reasoning over hybrid documents (needed for the comparator)

| Work | Authors | Year / venue | Link | Contribution | Tag |
|---|---|---|---|---|---|
| FinQA | Z. Chen et al. | EMNLP 2021 | [arXiv:2109.00122](https://arxiv.org/abs/2109.00122) | Program-supervised numerical reasoning over earnings-report text and tables. | [K] (repo [V]) |
| TAT-QA | F. Zhu et al. | ACL 2021 | [arXiv:2105.07624](https://arxiv.org/abs/2105.07624) | 16,552 questions over 2,757 hybrid table+text financial contexts. Covers scale and units. | [K] (repo [V]) |
| ConvFinQA | Z. Chen et al. | EMNLP 2022 | [ACL 2022.emnlp-main.421](https://aclanthology.org/2022.emnlp-main.421) | Conversational chains of numerical reasoning. | [V] |
| DePlot | F. Liu et al. | Findings ACL 2023 | [arXiv:2212.10505](https://arxiv.org/abs/2212.10505) | Chart-to-table translation, then an LLM reasons over the table. A practical chart extractor for a contradiction pipeline. | [K] |

### B.4 Open-source implementations (B)

SciTab ([XinyuanLu00/SciTab](https://www.github.com/XinyuanLu00/SciTab)), ChartCheck ([mubasharaak/ChartCheck](https://github.com/mubasharaak/ChartCheck)), MOCHEG ([VT-NLP/Mocheg](https://github.com/VT-NLP/Mocheg)), FinQA ([czyssrs/FinQA](https://github.com/czyssrs/FinQA)), TAT-QA ([NExTplusplus/TAT-QA](https://github.com/NExTplusplus/TAT-QA)), Kontrast (code "on GitHub" per the abstract; repo not checked), DePlot (`google/deplot` on Hugging Face [K]), MiniCheck and AlignScore [K], and DeBERTa-MNLI cross-encoders [K].

---

## C. Temporal knowledge reconstruction from incomplete or contradictory documents

### C.1 Temporal annotation and relation extraction

| Work | Authors | Year / venue | Link | Contribution | Tag |
|---|---|---|---|---|---|
| TimeML / TimeBank | J. Pustejovsky et al. | IWCS-5 2003; Corpus Linguistics 2003 | — | Annotation standard for events, TIMEX3 and TLINKs. | [K] |
| TempEval-1/-2 | M. Verhagen et al. | SemEval 2007 / 2010 | — | First shared tasks on temporal relations. | [K] |
| TempEval-3 | N. UzZaman, H. Llorens, J. Allen, L. Derczynski, M. Verhagen, J. Pustejovsky | *SEM / SemEval 2013 | [ACL S13-2001](https://aclanthology.org/S13-2001/); [arXiv:1206.5333](https://arxiv.org/abs/1206.5333) | End-to-end timex, events and relations, with a "temporal awareness" score. | [V] |
| TimeBank-Dense | T. Cassidy, B. McDowell, N. Chambers, S. Bethard | ACL 2014 | [ACL P14-2082](https://aclanthology.org/P14-2082/) | Dense relation annotation over all pairs in a window. | [K] |
| MATRES: A Multi-Axis Annotation Scheme for Event Temporal Relations | Q. Ning, H. Wu, D. Roth | ACL 2018 | [ACL P18-1122](https://aclanthology.org/P18-1122/) | Start-point-only, multi-axis annotation that raises agreement from the 60s to the 80s (kappa). Verb events only. | [V] |
| Zero-shot Temporal Relation Extraction with ChatGPT | C. Yuan, Q. Xie, S. Ananiadou | BioNLP 2023 | [arXiv:2304.05454](https://arxiv.org/abs/2304.05454) | Zero-shot LLM is far below supervised models and **inconsistent** under transitivity. | [V] (authors [K]) |
| Beyond Pairwise: Global Zero-shot Temporal Graph Generation (OmniTemp) | authors not verified | EMNLP 2025 | [arXiv:2502.11114](https://arxiv.org/abs/2502.11114) | Generates the whole temporal graph at once and gets competitive with supervised models. Argues MATRES and TB-Dense short-distance annotation biases evaluation, and releases an exhaustive dataset. | [P] |
| SemEval-2015 Task 4: TimeLine: Cross-Document Event Ordering | A.-L. Minard et al. | SemEval 2015 | [ACL S15-2132](https://aclanthology.org/S15-2132/) | Builds entity-centric timelines **across** documents, which needs cross-document event coreference. The best F1 from raw text was 7.85. | [V] |
| Maintaining Knowledge about Temporal Intervals | J. F. Allen | CACM 1983 | [doi:10.1145/182.358434](https://doi.org/10.1145/182.358434) | Interval algebra. | [K] |
| Temporal Constraint Networks | R. Dechter, I. Meiri, J. Pearl | AIJ 49, 1991 | [doi:10.1016/0004-3702(91)90006-6](https://doi.org/10.1016/0004-3702(91)90006-6) | Simple Temporal Problems. Inconsistency equals a negative cycle, solvable in polynomial time. | [K] |
| HeidelTime / SUTime | J. Strötgen, M. Gertz (SemEval 2010); A. Chang, C. Manning (LREC 2012) | — | — | Rule-based TIMEX normalization. | [K] |

### C.2 Event-centric and temporal KGs, including agent memory

| Work | Authors | Year / venue | Link | Contribution | Tag |
|---|---|---|---|---|---|
| What is Event Knowledge Graph: A Survey | S. Guan et al. | TKDE 2022 | [arXiv:2112.15280](https://arxiv.org/abs/2112.15280) | Survey of event-centric KGs: schema, acquisition, applications. | [V] |
| EventKG | S. Gottschalk, E. Demidova | ESWC 2018 | [arXiv:1804.04526](https://arxiv.org/abs/1804.04526) | Multilingual event-centric temporal KG. | [K] |
| Zep: A Temporal Knowledge Graph Architecture for Agent Memory (Graphiti) | P. Rasmussen et al. | arXiv 2501.13956 (2025) | [arXiv:2501.13956](https://arxiv.org/abs/2501.13956) | Bi-temporal model (event time vs ingestion time), with episode, entity and community subgraphs. Evaluated on DMR and LongMemEval. | [V] |
| ATOM / EvoKG | see A.3 | 2025–2026 | — | Dual-time construction (ATOM) and contradiction-aware updates (EvoKG). | [P] |
| Truth Discovery and Copying Detection in a Dynamic World | Dong et al. | PVLDB 2009 | see A.1 | Temporal truth discovery: the same data item can have different true values over time. | [V] |

### C.3 Time-aware QA and RAG benchmarks

| Work | Authors | Year / venue | Link | Contribution | Tag |
|---|---|---|---|---|---|
| TimeQA (A Dataset for Answering Time-Sensitive Questions) | W. Chen, X. Wang, W. Y. Wang | NeurIPS 2021 Datasets & Benchmarks | [arXiv:2108.06314](https://arxiv.org/abs/2108.06314) | Time-evolving Wikidata facts aligned to Wikipedia. FiD scored 46% vs 87% for humans. | [V] |
| SituatedQA | M. Zhang, E. Choi | EMNLP 2021 | [arXiv:2109.06157](https://arxiv.org/abs/2109.06157) | Answers depend on temporal and geographic context. | [K] |
| Time-Aware Language Models as Temporal Knowledge Bases (TempLAMA) | B. Dhingra et al. | TACL 2022 | [arXiv:2106.15110](https://arxiv.org/abs/2106.15110) | Time-stamped cloze facts. | [K] |
| TempReason | Q. Tan, H. T. Ng, L. Bing | ACL 2023 | [arXiv:2306.08952](https://arxiv.org/abs/2306.08952) | Three levels of temporal reasoning. | [K] |
| Test of Time (ToT) | B. Fatemi et al. | ICLR 2025 | [arXiv:2406.09170](https://arxiv.org/abs/2406.09170) | Synthetic temporal reasoning that separates semantics from arithmetic. Fact order and graph structure strongly affect accuracy. | [V] |
| LongMemEval | D. Wu, H. Wang, W. Yu, Y. Zhang, K.-W. Chang, D. Yu | ICLR 2025 | [arXiv:2410.10813](https://arxiv.org/abs/2410.10813) | 500 questions covering temporal reasoning and knowledge updates in long chat histories. Accuracy drops about 30% under sustained interaction. | [V] |
| TempRAGEval | authors not verified | arXiv 2412.15540 | [arXiv:2412.15540](https://arxiv.org/abs/2412.15540) | Temporal perturbations of QA sets for diagnosing each RAG component. | [P] |
| ChronoQA | authors not verified | arXiv 2508.12282 (2025) | [arXiv:2508.12282](https://arxiv.org/abs/2508.12282) | 5,176 Chinese news questions with absolute, aggregate and relative time. | [P] |

### C.4 Open-source implementations (C)

Graphiti [K], iText2KG/ATOM ([AuvaLab/itext2kg](https://github.com/AuvaLab/itext2kg)), MATRES data ([qiangning/MATRES](https://www.github.com/qiangning/MATRES)), TimeQA ([wenhuchen/Time-Sensitive-QA](https://github.com/wenhuchen/Time-Sensitive-QA)), ToT (Hugging Face `baharef/ToT`), LongMemEval (`xiaowu0162/LongMemEval`), and HeidelTime, SUTime, `dateparser` and OR-Tools CP-SAT for constraint solving [K].

---

## D. Active evidence acquisition

### D.1 Value of information and active feature acquisition

| Work | Authors | Year / venue | Link | Contribution | Tag |
|---|---|---|---|---|---|
| Information Value Theory | R. A. Howard | IEEE Trans. SSC 1966 | [doi:10.1109/TSSC.1966.300074](https://doi.org/10.1109/TSSC.1966.300074) | Formal value of information. | [K] |
| Near-optimal Nonmyopic Value of Information in Graphical Models | A. Krause, C. Guestrin | UAI 2005 | [arXiv:1207.1394](https://arxiv.org/abs/1207.1394) | Efficient VOI on chains and trees, with hardness results. | [K] |
| Adaptive Submodularity | D. Golovin, A. Krause | JAIR 2011 | [arXiv:1003.3967](https://arxiv.org/abs/1003.3967) | Guarantees for greedy adaptive acquisition policies. | [K] |
| Active Feature-Value Acquisition | M. Saar-Tsechansky, P. Melville, F. Provost | Management Science 2009 | [doi:10.1287/mnsc.1080.0952](https://doi.org/10.1287/mnsc.1080.0952) | Which missing feature values to buy, given costs. | [K] |
| EDDI: Efficient Dynamic Discovery of High-Value Information with Partial VAE | C. Ma, S. Tschiatschek, K. Palla, J. M. Hernández-Lobato, S. Nowozin, C. Zhang | ICML 2019 | [PMLR v97 ma19c](https://proceedings.mlr.press/v97/ma19c.html) | Bayesian experimental design: picks the next variable by expected information gain on the target. | [V] |
| Active Feature Acquisition with Generative Surrogate Models (GSMRL) | Y. Li, J. B. Oliva | ICML 2021 | [arXiv:2010.02433](https://arxiv.org/abs/2010.02433) | RL acquisition policy with surrogate-estimated information-gain rewards. | [V] |
| Towards Cost Sensitive Decision Making (AA-POMDP) | Y. Li, J. B. Oliva | AISTATS 2025 | [PMLR v258 li25h](https://proceedings.mlr.press/v258/li25h.html) | The agent buys features during sequential decisions, trading cost against reward. | [V] |
| Evaluation of Active Feature Acquisition Methods for Time-varying Feature Settings | H. von Kleist et al. | JMLR 2025 (arXiv 2023) | [arXiv:2312.01530](https://arxiv.org/abs/2312.01530) | Off-policy evaluation of acquisition policies. Relevant to evaluating "what to request" without deploying it. | [P] |
| Bayesian Optimal Active Search and Surveying | R. Garnett et al. | ICML 2012 | [arXiv:1206.6406](https://arxiv.org/abs/1206.6406) | Budgeted search for positives, close in spirit to finding fraud with a fixed analyst budget. | [K] |

### D.2 Active and adaptive retrieval

| Work | Authors | Year / venue | Link | Contribution | Tag |
|---|---|---|---|---|---|
| Active Retrieval Augmented Generation (FLARE) | Z. Jiang et al. | EMNLP 2023 | [arXiv:2305.06983](https://arxiv.org/abs/2305.06983) | Retrieves again when an upcoming sentence has low-confidence tokens. | [K] |
| Self-RAG | A. Asai, Z. Wu, Y. Wang, A. Sil, H. Hajishirzi | ICLR 2024 | [arXiv:2310.11511](https://arxiv.org/abs/2310.11511) | Reflection tokens decide when to retrieve and critique support. | [K] |
| Corrective RAG (CRAG) | S.-Q. Yan, J.-C. Gu, Y. Zhu, Z.-H. Ling | arXiv 2401.15884 (2024) | [arXiv:2401.15884](https://arxiv.org/abs/2401.15884) | A retrieval evaluator triggers refine, web-search or combined actions. | [V] |
| Adaptive-RAG | S. Jeong, J. Baek, S. Cho, S. J. Hwang, J. C. Park | NAACL 2024 | [ACL 2024.naacl-long.389](https://aclanthology.org/2024.naacl-long.389) | A complexity classifier routes queries to no, single-step or multi-step retrieval. | [V] |
| DRAGIN | W. Su et al. | ACL 2024 | [arXiv:2403.10081](https://arxiv.org/abs/2403.10081) | Retrieval triggered by information needs during generation. | [K] |
| IRCoT; ReAct | H. Trivedi et al. (ACL 2023); S. Yao et al. (ICLR 2023) | — | [arXiv:2212.10509](https://arxiv.org/abs/2212.10509); [arXiv:2210.03629](https://arxiv.org/abs/2210.03629) | Interleaved retrieval/actions and reasoning. | [K] |
| Search-R1 | B. Jin et al. | arXiv 2503.09516 (2025) | [arXiv:2503.09516](https://arxiv.org/abs/2503.09516) | RL-trained search-calling LLM. | [K] |
| When Knowledge Is Not Free: Cost-Aware Evidence Selection in RAG | M. Wu, H. Yang, O. Ben-Porat, Y. Ziser | arXiv 2606.02245 (2026) | [arXiv:2606.02245](https://arxiv.org/abs/2606.02245) | Evidence has access-cost tiers (MS MARCO v2.1 with friction tiers). No static selector dominates, and LLM controllers are unreliable. **Closest prior work on cost-aware acquisition in RAG.** | [V] |
| FIRE: Fact-checking with Iterative Retrieval and Verification | authors not verified | arXiv 2411.00784; reported NAACL 2025 Findings | [arXiv:2411.00784](https://arxiv.org/abs/2411.00784) | Decides whether to search again from model confidence. Reports about 7.6x lower LLM cost and about 16.5x lower search cost. | [P] |
| SIEVE (Sparse Evidence Can Suffice) | H. Zhao et al. | arXiv 2607.18080 (2026) | [arXiv:2607.18080](https://arxiv.org/abs/2607.18080) | An RL-trained agent collects a compact evidence package before verification (video misinformation). | [V] |

### D.3 Information-seeking agents that ask questions

| Work | Authors | Year / venue | Link | Contribution | Tag |
|---|---|---|---|---|---|
| Uncertainty of Thoughts (UoT) | Z. Hu et al. | NeurIPS 2024 | [arXiv:2402.03271](https://arxiv.org/abs/2402.03271) | Simulates answers to candidate questions and picks by expected information gain. Task success rises 38.1% on average. | [V] |
| MediQ | S. S. Li et al. | NeurIPS 2024 | [arXiv:2406.00922](https://arxiv.org/abs/2406.00922) | Naively asking questions **hurts** accuracy (−11.3% relative). Confidence estimation plus abstention recovers it. | [V] |
| QuestBench | B. Z. Li, B. Kim, Z. Wang | NeurIPS 2025 Datasets & Benchmarks | [arXiv:2503.22674](https://arxiv.org/abs/2503.22674) | Underspecified CSPs with one missing variable. Models reach only 40–50% on Logic-Q and Planning-Q. | [V] |
| BED-LLM | D. Choudhury, S. Williamson, A. Goliński, N. Miao, F. Bickford Smith, et al. | ICLR 2026 | [arXiv:2508.21184](https://arxiv.org/abs/2508.21184) | EIG-maximizing query selection with explicit belief updates rather than only in-context ones. +37.4 pp success. **Closest prior work on the EIG part of D.** | [V] |

### D.4 Open-source implementations (D)

UoT ([zhiyuanhubj/UoT](https://github.com/zhiyuanhubj/UoT)), GSMRL (lupalab/GSMRL), Adaptive-RAG ([starsuzi/Adaptive-RAG](https://github.com/starsuzi/Adaptive-RAG)), CRAG ([HuskyInSalt/CRAG](https://github.com/HuskyInSalt/CRAG)), QuestBench (google-deepmind/questbench), Self-RAG (`AkariAsai/self-rag`) [K], FLARE (`jzbjyb/FLARE`) [K].

---

## E. Investigation robustness and counterfactual sensitivity

### E.1 Attribution and citation evaluation

| Work | Authors | Year / venue | Link | Contribution | Tag |
|---|---|---|---|---|---|
| Measuring Attribution in NLG Models (AIS) | H. Rashkin et al. | Computational Linguistics 49(4), 2023 | [arXiv:2112.12870](https://arxiv.org/abs/2112.12870) | "Attributable to Identified Sources" definition and a two-stage human protocol. | [V] |
| Evaluating Verifiability in Generative Search Engines | N. F. Liu, T. Zhang, P. Liang | Findings EMNLP 2023 | [arXiv:2304.09848](https://arxiv.org/abs/2304.09848) | Citation recall and precision in commercial engines. Many statements are unsupported. | [K] |
| ALCE: Enabling LLMs to Generate Text with Citations | T. Gao, H. Yen, J. Yu, D. Chen | EMNLP 2023 | [arXiv:2305.14627](https://arxiv.org/abs/2305.14627) | Automatic NLI-based citation recall and precision on ASQA, QAMPARI and ELI5. | [V] |
| FActScore | S. Min et al. | EMNLP 2023 | [arXiv:2305.14251](https://arxiv.org/abs/2305.14251) | Decomposes output into atomic facts and checks each. The basis for an "unsupported-claim rate". | [K] |
| AttributionBench | Y. Li, X. Yue, Z. Liao, H. Sun | Findings ACL 2024 | [ACL 2024.findings-acl.886](https://aclanthology.org/2024.findings-acl.886) | Automatic attribution judging is hard: fine-tuned GPT-3.5 reaches about 80% macro-F1. | [V] |
| Correctness is not Faithfulness in RAG Attributions | J. Wallat, M. Heuss, M. de Rijke, A. Anand | ICTIR 2025 | [arXiv:2412.18004](https://arxiv.org/abs/2412.18004) | A citation can be *correct* (it supports the claim) without being *faithful* (actually used). Up to 57% of citations were post-rationalized in their setting. | [V] |
| RAGAS; ARES | S. Es et al. (EACL 2024 demo); J. Saad-Falcon et al. (NAACL 2024) | — | [arXiv:2309.15217](https://arxiv.org/abs/2309.15217); [arXiv:2311.09476](https://arxiv.org/abs/2311.09476) | Reference-free RAG metrics (faithfulness, relevance). | [K] |

### E.2 Context attribution by ablation

| Work | Authors | Year / venue | Link | Contribution | Tag |
|---|---|---|---|---|---|
| ContextCite | B. Cohen-Wang, H. Shah, K. Georgiev, A. Mądry | NeurIPS 2024 | [arXiv:2409.00729](https://arxiv.org/abs/2409.00729) | A linear surrogate fit on random context ablations attributes output to context parts with few extra inference passes. | [V] |
| TracLLM | Y. Wang, W. Zou, R. Geng, J. Jia | USENIX Security 2025 | [arXiv:2506.04202](https://arxiv.org/abs/2506.04202) | Search-based context traceback for long contexts, with score ensembling and denoising. | [V] |
| Source Attribution in Retrieval-Augmented Generation | I. Nematov et al. | ECML PKDD 2025 workshop proceedings (Springer CCIS) | [arXiv:2507.04480](https://arxiv.org/abs/2507.04480) | Exact Shapley vs Kernel SHAP, ContextCite, TMC- and Beta-Shapley vs leave-one-out over retrieved documents. "Synthesis" documents get under-valued. | [P] |
| Understanding Black-box Predictions via Influence Functions | P. W. Koh, P. Liang | ICML 2017 | [arXiv:1703.04730](https://arxiv.org/abs/1703.04730) | Classic training-data attribution, here as background for LOO reasoning. | [K] |

### E.3 Robustness to noisy, counterfactual and adversarial documents

| Work | Authors | Year / venue | Link | Contribution | Tag |
|---|---|---|---|---|---|
| RGB: Benchmarking LLMs in RAG | J. Chen, H. Lin, X. Han, L. Sun | AAAI 2024 | [arXiv:2309.01431](https://arxiv.org/abs/2309.01431) | Tests noise robustness, negative rejection, information integration and **counterfactual robustness**. | [V] |
| Lost in the Middle | N. F. Liu et al. | TACL 2024 | [arXiv:2307.03172](https://arxiv.org/abs/2307.03172) | Position sensitivity of long-context use. | [K] |
| The Power of Noise | F. Cuconasu et al. | SIGIR 2024 | [arXiv:2401.14887](https://arxiv.org/abs/2401.14887) | Effect of irrelevant and noisy passages on RAG. | [K] |
| Making Retrieval-Augmented LMs Robust to Irrelevant Context | O. Yoran et al. | ICLR 2024 | [arXiv:2310.01558](https://arxiv.org/abs/2310.01558) | NLI filtering and fine-tuning for robustness. | [K] |
| ClashEval | K. Wu, E. Wu, J. Zou | NeurIPS 2024 Datasets & Benchmarks | [arXiv:2404.10198](https://arxiv.org/abs/2404.10198) | How LLMs trade off priors vs perturbed retrieved content. | [K] |
| Certifiably Robust RAG against Retrieval Corruption (RobustRAG) | C. Xiang, T. Wu, Z. Zhong, D. Wagner, D. Chen, P. Mittal | arXiv 2405.15556 (ICML 2024 workshop) | [arXiv:2405.15556](https://arxiv.org/abs/2405.15556) | Isolate-then-aggregate gives **certified** answer quality under k corrupted passages. | [V] |
| PoisonedRAG | W. Zou, R. Geng, B. Wang, J. Jia | USENIX Security 2025 | [arXiv:2402.07867](https://arxiv.org/abs/2402.07867) | About 90% attack success with 5 injected texts per target question in a database of millions. | [V] |
| Sufficient Context | H. Joren, J. Zhang, C.-S. Ferng, D.-C. Juan, A. Taly, C. Rashtchian | ICLR 2025 | [arXiv:2411.06037](https://arxiv.org/abs/2411.06037) | Autorater for whether context is sufficient. Selective generation uses sufficiency plus confidence. | [V] |
| CUE-R: Beyond the Final Answer in RAG | S. Jain, V. N. Vedam | arXiv 2604.05467 (2026) | [arXiv:2604.05467](https://arxiv.org/abs/2604.05467) | Per-evidence remove, replace and duplicate interventions on HotpotQA and 2Wiki. Removing both supports hurts more than the sum of single removals. The authors list **agentic workflows as future work**. **Closest prior work for E.** | [V] |
| EviScope | S. S. Deswal | arXiv 2609.17081 (2026) | [arXiv:2609.17081](https://arxiv.org/abs/2609.17081) | Paired add/remove/distract/contradict evidence quartets. Answer accuracy hides unsupported answering. | [V] |
| BAR-RAG | authors not verified | arXiv 2602.03689 (2026) | [arXiv:2602.03689](https://arxiv.org/abs/2602.03689) | Counterfactual check: full context vs cited documents removed vs only cited documents kept. | [P] |
| Provenance Semirings | T. J. Green, G. Karvounarakis, V. Tannen | PODS 2007 | [doi:10.1145/1265530.1265535](https://doi.org/10.1145/1265530.1265535) | Algebraic lineage: which source tuples a derived fact depends on. This is the database tool that makes deletion sensitivity exact for deterministic steps. | [K] |

### E.4 Open-source implementations (E)

ContextCite ([MadryLab/context-cite](https://github.com/MadryLab/context-cite)), TracLLM ([Wang-Yanting/TracLLM](https://github.com/Wang-Yanting/TracLLM)), ALCE ([princeton-nlp/ALCE](https://github.com/princeton-nlp/ALCE)), AttributionBench ([osu-nlp-group/attributionbench](https://github.com/osu-nlp-group/attributionbench)), AIS data ([google-research-datasets/AIS](https://github.com/google-research-datasets/AIS)), PoisonedRAG ([sleeeepeer/PoisonedRAG](https://github.com/sleeeepeer/PoisonedRAG)), Sufficient Context (`hljoren/sufficientcontext`), RAGAS and ARES [K].

---

## F. Baselines MindDoc will be compared against

### F.1 GraphRAG and its critiques

| Work | Authors | Year / venue | Link | Takeaway for MindDoc | Tag |
|---|---|---|---|---|---|
| From Local to Global: A Graph RAG Approach to Query-Focused Summarization | D. Edge et al. | arXiv 2404.16130 (2024, v2 2025) | [arXiv:2404.16130](https://arxiv.org/abs/2404.16130) | Community summaries win on comprehensiveness and diversity for *global* questions over ~1M tokens. Vector RAG wins on directness. | [V] |
| LightRAG | Z. Guo et al. | arXiv 2410.05779 (2024) | [arXiv:2410.05779](https://arxiv.org/abs/2410.05779) | Cheaper dual-level graph retrieval. A common baseline. | [K] |
| HippoRAG; HippoRAG 2 | B. J. Gutiérrez et al. | NeurIPS 2024; arXiv 2025 | [arXiv:2405.14831](https://arxiv.org/abs/2405.14831) | Personalized PageRank over an OpenIE graph for multi-hop QA. | [V] / [P] |
| RAG vs. GraphRAG: A Systematic Evaluation and Key Insights | H. Han et al. | arXiv 2502.11371 (2025–2026 versions) | [arXiv:2502.11371](https://arxiv.org/abs/2502.11371) | RAG is better for single-hop and detail, GraphRAG for multi-hop. **Position bias** in LLM-judge summarization comparisons. | [V] |
| How Significant Are the Real Performance Gains? An Unbiased Evaluation Framework for GraphRAG | Zeng et al. | arXiv 2506.06331 (2025) | [arXiv:2506.06331](https://arxiv.org/abs/2506.06331) | Controlling position, length and trial bias makes GraphRAG gains "much more moderate". | [V] |
| When to use Graphs in RAG (GraphRAG-Bench) | Z. Xiang et al. | ICLR 2026 | [arXiv:2506.05690](https://arxiv.org/abs/2506.05690) | Graphs help on complex reasoning and stay stable as the corpus grows, but are not better for simple fact lookup. | [V] |

**Implication.** Any "MindDoc beats GraphRAG" claim must use order-swapped, multi-trial judging, report reference-based metrics, and split results by question type (single-hop, multi-hop, global).

### F.2 Hybrid, dense and contextual retrieval

| Work | Authors | Year / venue | Link | Takeaway | Tag |
|---|---|---|---|---|---|
| BM25 and beyond | S. Robertson, H. Zaragoza | FnTIR 2009 | — | Lexical baseline. | [K] |
| Reciprocal Rank Fusion | G. Cormack, C. Clarke, S. Buettcher | SIGIR 2009 | [doi:10.1145/1571941.1572114](https://doi.org/10.1145/1571941.1572114) | The fusion MindDoc uses. | [K] |
| Dense Passage Retrieval | V. Karpukhin et al. | EMNLP 2020 | [arXiv:2004.04906](https://arxiv.org/abs/2004.04906) | Dense baseline. | [K] |
| BEIR | N. Thakur et al. | NeurIPS 2021 Datasets & Benchmarks | [arXiv:2104.08663](https://arxiv.org/abs/2104.08663) | Zero-shot, 18 datasets. **BM25 is a robust baseline.** Rerankers and late interaction are best but costly. | [V] |
| Introducing Contextual Retrieval | Anthropic | Engineering blog, Sept 2024 | [anthropic.com](https://www.anthropic.com/engineering/contextual-retrieval) | Chunk-context prefixes. Top-20 retrieval failure drops 35% (embeddings), 49% (+contextual BM25) and 67% (+rerank). Blog post, not peer-reviewed. | [V] |
| Late Chunking | M. Günther et al. | arXiv 2409.04701 (2024) | [arXiv:2409.04701](https://arxiv.org/abs/2409.04701) | Embeds a long context first, then pools per chunk. | [K] |

### F.3 Entity resolution

| Work | Authors | Year / venue | Link | Takeaway | Tag |
|---|---|---|---|---|---|
| A Theory for Record Linkage | I. P. Fellegi, A. B. Sunter | JASA 1969 | [doi:10.1080/01621459.1969.10501049](https://doi.org/10.1080/01621459.1969.10501049) | Probabilistic m/u-weights. Unsupervised via EM. | [K] |
| Magellan | P. Konda, A. Doan et al. | PVLDB 9(12), 2016 | [doi:10.14778/2994509.2994535](https://doi.org/10.14778/2994509.2994535) | An end-to-end EM *system* (blocking, then matching) on the PyData stack. | [V] |
| DeepMatcher | S. Mudgal et al. | SIGMOD 2018 | [doi:10.1145/3183713.3196926](https://doi.org/10.1145/3183713.3196926) | Deep EM. Its benchmark suite is the standard one. | [K] |
| Ditto | Y. Li, J. Li, Y. Suhara, A. Doan, W.-C. Tan | PVLDB 14(1), 2021 | [VLDB pdf](https://www.vldb.org/pvldb/vol14/p50-li.pdf) | Sequence-pair classification with pre-trained LMs, up to +29% F1 over the previous state of the art. | [V] |
| Splink | R. Linacre, S. Lindsay, T. Manassis, Z. Slade, T. Hepworth | IJPDS 7(3), 2022 | [doi:10.23889/ijpds.v7i3.1794](https://doi.org/10.23889/ijpds.v7i3.1794) | Scalable Fellegi–Sunter with EM, in SQL (DuckDB or Spark). The practical unsupervised baseline. | [V] |
| WDC Products | R. Peeters, R. C. Der, C. Bizer | EDBT 2024 | [arXiv:2301.09521](https://arxiv.org/abs/2301.09521) | Benchmark that varies corner cases, unseen entities and training size. | [V] |
| Entity Matching using Large Language Models | R. Peeters, A. Steiner, C. Bizer | EDBT 2025 | [arXiv:2310.11244](https://arxiv.org/abs/2310.11244) | LLM matchers are competitive with little training data, but prompts must be tuned per dataset. | [V] |

### F.4 Anomaly detection for financial and transactional data

| Work | Authors | Year / venue | Link | Takeaway | Tag |
|---|---|---|---|---|---|
| Isolation Forest | F. T. Liu, K. M. Ting, Z.-H. Zhou | ICDM 2008 | [doi:10.1109/ICDM.2008.17](https://doi.org/10.1109/ICDM.2008.17) | Strong unsupervised tabular baseline. | [K] |
| LOF | M. Breunig, H.-P. Kriegel, R. Ng, J. Sander | SIGMOD 2000 | [doi:10.1145/342009.335388](https://doi.org/10.1145/342009.335388) | Local density outliers. | [K] |
| PyOD | Y. Zhao, Z. Nasrullah, Z. Li | JMLR 2019 | [arXiv:1901.01588](https://arxiv.org/abs/1901.01588) | Reference implementations. | [K] |
| ADBench | S. Han, X. Hu, H. Huang, M. Jiang, Y. Zhao | NeurIPS 2022 Datasets & Benchmarks | [arXiv:2206.09426](https://arxiv.org/abs/2206.09426) | 30 algorithms on 57 datasets. **No unsupervised method is statistically best.** | [V] |
| A Comprehensive Survey on Graph Anomaly Detection with Deep Learning | X. Ma et al. | TKDE 35(12), 2023 | [arXiv:2106.07178](https://arxiv.org/abs/2106.07178) | Taxonomy of node, edge, subgraph and graph anomalies. | [V] |
| GADBench | J. Tang, F. Hua, Z. Gao, P. Zhao, J. Li | NeurIPS 2023 Datasets & Benchmarks | [arXiv:2306.12251](https://arxiv.org/abs/2306.12251) | **Tree ensembles with neighbourhood aggregation beat GAD-specific GNNs.** Use XGB-Graph as the baseline. | [V] |
| Realistic Synthetic Financial Transactions for AML (AMLworld) | E. Altman et al. | NeurIPS 2023 Datasets & Benchmarks | [arXiv:2306.16424](https://arxiv.org/abs/2306.16424) | Agent-based synthetic AML data with complete labels. | [V] |

### F.5 Agent evaluation

| Work | Authors | Year / venue | Link | Takeaway | Tag |
|---|---|---|---|---|---|
| τ-bench | S. Yao, N. Shinn, P. Razavi, K. Narasimhan | arXiv 2406.12045 (2024) | [arXiv:2406.12045](https://arxiv.org/abs/2406.12045) | Tool-agent-user tasks under policies. The **pass^k** reliability metric. | [V] |
| Berkeley Function Calling Leaderboard (BFCL) | S. G. Patil et al. | ICML 2025 | [PMLR v267 patil25a](https://proceedings.mlr.press/v267/patil25a.html) | AST-based tool-call accuracy, abstention and multi-turn tests. An external audit rated v4 "flawed". | [V] |
| AgentBench; GAIA | X. Liu et al. (ICLR 2024); G. Mialon et al. (ICLR 2024) | — | [arXiv:2308.03688](https://arxiv.org/abs/2308.03688); [arXiv:2311.12983](https://arxiv.org/abs/2311.12983) | Broad agent task suites. | [K] |
| AI Agents That Matter | S. Kapoor, B. Stroebl, Z. Siegel, N. Nadgir, A. Narayanan | TMLR 2025 | [arXiv:2407.01502](https://arxiv.org/abs/2407.01502) | Report **cost alongside accuracy**, use repeated runs, and avoid overfit holdouts. | [V] |

---

## Sources

Primary pages consulted this session:

- https://research.google/pubs/pub45634/ · https://lunadong.com/publication/dependence_vldb.pdf · https://lunadong.com/publication/lifespan_vldb.pdf · https://dblp.org/rec/journals/pvldb/DongBS09 · https://arxiv.org/abs/1502.03519 · https://arxiv.org/abs/1505.02463 · https://arxiv.org/abs/1503.00303 · https://unpaywall.org/10.1145%2F1281192.1281309
- https://arxiv.org/abs/1912.10000 · https://aclanthology.org/2020.emnlp-main.667 · https://arxiv.org/abs/2405.16929 · https://arxiv.org/abs/2308.02357 · https://aclanthology.org/2024.emnlp-main.548/ · https://arxiv.org/abs/2502.09956 · https://mlanthology.org/neurips/2025/mo2025neurips-kggen · https://arxiv.org/abs/2510.22590 · https://arxiv.org/abs/2509.15464 · https://arxiv.org/abs/2601.09720
- https://arxiv.org/abs/2403.08319 · https://arxiv.org/abs/2504.13079 · https://arxiv.org/abs/2506.08500 · https://www.ijcai.org/proceedings/2025/1073 · https://arxiv.org/abs/2601.03746 · https://aclanthology.org/2026.emnlp-main.509.pdf
- https://arxiv.org/abs/2106.05707 · https://aclanthology.org/2023.emnlp-main.483 · https://aclanthology.org/2024.findings-acl.828 · https://arxiv.org/abs/2305.13507 · https://arxiv.org/abs/2205.12487 · https://github.com/VT-NLP/Mocheg · https://aclanthology.org/2024.emnlp-main.818 · https://arxiv.org/abs/2403.17169 · https://aclanthology.org/2024.naacl-long.362 · https://arxiv.org/abs/2502.16033 · https://arxiv.org/abs/2510.16505 · https://arxiv.org/abs/2607.25959 · https://arxiv.org/abs/2510.12383 · https://aclanthology.org/2022.emnlp-main.421
- https://aclanthology.org/S13-2001.pdf · https://arxiv.org/abs/1206.5333 · https://aclanthology.org/P18-1122/ · https://www.github.com/qiangning/MATRES · https://arxiv.org/abs/2304.05454 · https://arxiv.org/abs/2502.11114 · https://preview.aclanthology.org/setup/S15-2132 · https://arxiv.org/abs/2112.15280 · https://arxiv.org/abs/2501.13956 · https://arxiv.org/abs/2108.06314 · https://arxiv.org/abs/2406.09170 · https://arxiv.org/abs/2410.10813 · https://arxiv.org/abs/2412.15540 · https://arxiv.org/abs/2508.12282 · https://github.com/AuvaLab/itext2kg
- https://proceedings.mlr.press/v97/ma19c.html · https://arxiv.org/abs/2010.02433 · https://proceedings.mlr.press/v258/li25h.html · https://arxiv.org/abs/2312.01530 · https://arxiv.org/abs/2401.15884 · https://aclanthology.org/2024.naacl-long.389 · https://arxiv.org/abs/2606.02245 · https://arxiv.org/abs/2411.00784 · https://www.alphaxiv.org/overview/2607.18080 · https://arxiv.org/abs/2402.03271 · https://arxiv.org/abs/2406.00922 · https://arxiv.org/abs/2503.22674 · https://arxiv.org/abs/2508.21184
- https://arxiv.org/abs/2112.12870 · https://arxiv.org/abs/2305.14627 · https://aclanthology.org/2024.findings-acl.886 · https://arxiv.org/abs/2412.18004 · https://arxiv.org/abs/2409.00729 · https://arxiv.org/abs/2506.04202 · https://arxiv.org/abs/2507.04480 · https://arxiv.org/abs/2309.01431 · https://arxiv.org/abs/2405.15556 · https://arxiv.org/abs/2402.07867 · https://arxiv.org/abs/2411.06037 · https://arxiv.org/abs/2604.05467 · https://www.alphaxiv.org/abs/2609.17081 · https://arxiv.org/pdf/2602.03689
- https://arxiv.org/abs/2404.16130 · https://arxiv.org/abs/2405.14831 · https://arxiv.org/abs/2502.11371 · https://arxiv.org/abs/2506.06331 · https://arxiv.org/abs/2506.05690 · https://arxiv.org/abs/2104.08663 · https://www.anthropic.com/engineering/contextual-retrieval
- https://www.vldb.org/pvldb/vol14/p50-li.pdf · https://dblp.org/rec/journals/pvldb/KondaDCDABLPZNP16a · https://ijpds.org/article/view/1794 · https://arxiv.org/abs/2301.09521 · https://arxiv.org/abs/2310.11244
- https://arxiv.org/abs/2206.09426 · https://arxiv.org/abs/2106.07178 · https://arxiv.org/abs/2306.12251 · https://arxiv.org/abs/2306.16424
- https://arxiv.org/abs/2406.12045 · https://proceedings.mlr.press/v267/patil25a.html · https://epoch.ai/benchmarks/berkeley-function-calling-leaderboard/review · https://arxiv.org/abs/2407.01502

Items tagged [K] were not re-fetched this session. Their links are given for convenience and should be checked before citation.
