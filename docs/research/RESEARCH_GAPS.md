# MindDoc AI: Research Gaps, Problem Statements and Publishability

*Research date: 2026-11-10. Prior-work tables and verification tags ([V] / [P] / [K]) are in [RESEARCH_PAPERS.md](RESEARCH_PAPERS.md), and datasets are in [BENCHMARK_DATASETS.md](BENCHMARK_DATASETS.md).*

This file covers items (c)–(g) for each direction: the remaining gap, a formal problem statement, a candidate method, an experiment design and a publishability verdict. None of the directions is claimed to be novel. Each section names the closest prior work and states what is left over. "Feasible" means one engineer, CPU only, with API LLMs, in roughly 2–4 months.

---

## 0. Summary

| Dir. | Closest prior work | Residual gap | Feasibility | Verdict | Main risk |
|---|---|---|---|---|---|
| **A** Evidence-calibrated KG | Dong et al. 2009 (source dependence), KBT 2015 (extraction vs source error), Evidence Laundering (EMNLP 2026) | **Small–medium.** Calibrated fact confidence when redundancy is low (1–5 sources per fact), extraction is done by an LLM, documents span several modalities, dependence is soft, and human verifications are sparse. | High | Workshop; conference only with a real-data case study | Seen as "truth discovery + LLM". The independence story was already taken in 2026. |
| **B** Cross-modal contradiction | Kontrast (2026), MMIR (2025), PRISMM-Bench (ICLR 2026), FinDVer (EMNLP 2024), FEVEROUS / TabFact / ChartCheck | **Medium.** Discovering contradictions with no given claim, across business records (text, table, chart, scan, record), while separating *explained* from *unexplained* discrepancies. | Medium (extraction quality is the bottleneck) | Benchmark plus baseline could reach a conference (Findings or D&B track). Method alone is workshop-level. | Busy area. Real annotated data is costly. Searches here were incomplete. |
| **C** Temporal reconstruction | Graphiti/Zep (2025), ATOM (2025/26), MATRES / OmniTemp, SemEval-2015 TimeLine | **Medium.** Conflict-aware, uncertainty-bearing timeline reconstruction across documents, evaluated against gold timelines. ATOM leaves conflict resolution open. | High | Workshop. A conference is unlikely without a new annotated corpus. | The solver side (STP, MaxSAT) is classical, so novelty is thin. |
| **D** Active evidence acquisition | BED-LLM (ICLR 2026), Cost-aware RAG (2026), EDDI / GSMRL (AFA), UoT / MediQ / QuestBench | **Medium–large.** Choosing which *not-yet-held* document to obtain, using actions typed by gaps in the KG and valued by their effect on decisions. | Medium (needs a simulator and depends on A) | Workshop likely. Conference possible with a principled estimator and convincing simulation. | Simulator realism. The outcome model is the weak link. |
| **E** Investigation robustness | CUE-R (2026; agentic extension listed as future work), ContextCite (NeurIPS 2024), TracLLM (USENIX Sec 2025), provenance semirings (PODS 2007) | **Small–medium.** Source-deletion fragility of *multi-step, KG-mediated* findings, estimated from lineage plus a surrogate, and checked against real re-runs. | **Highest.** Ground truth is computable by re-running. | Workshop very likely. Conference possible at SIGIR/CIKM short or Findings level. | Crowded and fast-moving. Agent stochasticity. "Provenance is known" pushback. |

**Recommendation: pursue E first** (see §6), and build the synthetic investigation benchmark (BENCHMARK_DATASETS.md §3) as the shared substrate for A, B, C and D.

---

## 1. Direction A: Evidence-calibrated KG construction

### (c) Remaining gap

- **Already solved for structured web data.** TruthFinder, ACCU/DEPEN (Dong et al. 2009), LTM and CRH estimate source accuracy and truth jointly. Dong et al. 2009 detect copying (shared *false* values signal dependence) and handle changing truths. Knowledge Vault and KBT separate *extraction* error from *source* error and produce calibrated fact probabilities at web scale.
- **Partly solved for KG calibration.** Tabacof & Costabello (ICLR 2020) and Safavi et al. (EMNLP 2020) calibrate *embedding-predicted* links. Calibrating *extracted, evidence-backed* facts is a different target.
- **Partly solved for LLM-era conflicts.** CONFACT shows source-credibility cues help, CONFLICTS and RAMDocs benchmark conflict handling, and *Whose Facts Win?* shows that repetition flips preferences. **Evidence Laundering (EMNLP 2026)** shows that deep-research agents treat paraphrased same-origin pages as independent, and that collapsing likely same-origin pages to one source fixes much of it.
- **Residual gap.** None of the work above (as far as found) delivers *calibrated* per-fact confidence in the enterprise investigation regime, which has five features:
  1. Low redundancy, typically 1–5 mentions per fact. Web-scale fusion relies on many sources.
  2. LLM, OCR or VLM extraction with its own error model.
  3. Soft, document-level dependence: a memo restating an invoice, a statement copied from a ledger, a template-generated letter.
  4. Validity intervals, where a changed address is not a contradiction.
  5. A trickle of human verifications that should update source reliability.

  The evaluation should report ECE/Brier and how efficiently errors are caught under review, not just accuracy.
- **Honest size:** small–medium. Each ingredient is known, and the contribution would be how they are combined and validated in this regime.

### (d) Formal problem statement

Let $D$ be documents with source map $\sigma: D \to S$. An extractor emits mentions $m = (i, v, \tau, d, \ell, e_m)$, where:

- $i$ is a data item (entity, attribute),
- $v$ is a value,
- $\tau$ is a validity interval,
- $\ell$ is a locator (page, bounding box, cell),
- $e_m$ is a raw extraction score.

A claim is $c = (i, v, \tau)$ with latent truth $z_c \in \{0,1\}$. Unknowns are the source accuracies $a_s \in [0,1]$ and a document dependence matrix $\rho_{d,d'} \in [0,1]$, the probability that $d'$ derives from $d$. Human labels $y_c$ are observed for $c \in L \subset C$.

For *exclusive* attributes, at most one value is true per item and time point: $\sum_{v} z_{(i,v,\tau)} \le 1$ wherever the intervals overlap.

**Goal:** output $\hat p_c = \hat P(z_c = 1 \mid M, L)$ such that:

1. $\hat p$ is calibrated on held-out labeled claims (minimize ECE and Brier),
2. ranking claims by $\hat p$ maximizes the false claims caught in the first $k$ human reviews, and
3. adding copies of a document does not raise $\hat p$ beyond a single independent source would (a dependence-invariance property).

### (e) Candidate method: dependence-aware calibrated fusion (working name DACF)

1. **Mention correctness.** Combine LLM self-consistency (agreement over 3–5 sampled extractions), OCR token confidence over the span, and type and checksum validators. Map these to $P(\text{mention correct})$ with isotonic regression on about 300 labeled mentions. This follows the KBT idea of keeping extraction error separate from source error.
2. **Dependence estimation.** Pairwise features include MinHash text similarity, shared rare values, **shared deviations from the consensus** (Dong et al.'s copy signal), explicit references ("per invoice #123"), same template or sender, and time order. Feed them to a logistic or Bayesian copy model that gives $\rho_{d,d'}$. Each document gets a soft weight $w_d = \prod_{d' \prec d}(1-\rho_{d',d})$, compared against the hard same-origin collapse from Evidence Laundering.
3. **Temporal scoping.** Values compete only when their intervals overlap. Non-overlapping values become a *change event*, which is handed to Direction C, rather than a conflict.
4. **Inference.** EM in the style of ACCU. In the E-step, each candidate value's posterior comes from mention-correctness × source-accuracy × dependence weight. In the M-step, source accuracies are updated under a Beta prior. Human-verified claims are clamped. This runs in milliseconds to seconds on CPU for MindDoc-scale corpora.
5. **Post-hoc calibration.** Apply temperature or isotonic scaling on held-out human-verified claims, and report reliability diagrams.
6. *(Optional)* Rank claims for human review by expected uncertainty reduction. This links to D.

### (f) Experiment design

- **Datasets**
  - Synthetic investigation benchmark (primary). Source accuracy, copy rate, extraction noise and redundancy can all be controlled.
  - CONFLICTS and RAMDocs, recast as claim-level fusion.
  - Text2KGBench, for the extraction-quality component.
  - The classic Stock and Flight truth-discovery data (Li et al. 2012). Availability and license were **not verified** this session.
  - A small real case study using public SEC EDGAR filings plus company press releases. Press releases naturally copy filings, which provides real dependence. Check reuse terms first.
- **Baselines:** majority vote, max extraction confidence, TruthFinder, ACCU, ACCU-COPY/DEPEN, LTM, CRH, KBT-style two-layer (no dependence), LLM verbalized confidence given all evidence, MADAM-RAG, and a hard provenance gate (Evidence Laundering).
- **Metrics**
  - ECE (fixed and adaptive bins), Brier, NLL.
  - AUROC/AUPRC for detecting false claims.
  - Resolved-value accuracy.
  - Errors caught at *k* reviews.
  - Robustness curves against copy rate (0–80%) and number of sources (1–10).
- **Ablations:** remove extraction confidence, dependence, temporal scoping, or human labels. Compare soft discount vs hard collapse, and verbalized vs consistency confidence.

### (g) Publishability verdict

**Workshop** (data-quality, trustworthy-ML or KG workshops) is realistic. A **conference** (CIKM, KDD ADS, VLDB EA&B) is possible only with a real-data case study and a clear win over ACCU-COPY at realistic copy rates.

Risks:

- Reviewers who know the truth-discovery literature will see this as a recombination.
- Evidence Laundering already owns the narrative that "agents confuse correlated with independent sources".
- Results that are only synthetic will not carry a main-track paper.

---

## 2. Direction B: Cross-modal contradiction detection

### (c) Remaining gap

- **Already solved: verifying a given claim against tables, charts and text.** Examples are TabFact, INFOTABS, FEVEROUS, SciTab, ChartFC/ChartCheck, MOCHEG, FinDVer and QuanTemp. NLI tooling (MNLI, DocNLI, ContractNLI, MiniCheck) is mature.
- **Emerging: inconsistency detection with no given claim.** This exists *within one artifact* (ContraDoc for text, MMIR for webpages and slides, PRISMM-Bench for scientific papers). It exists *across* Wikipedia text, tables and Wikidata (Kontrast, 2026), and for table rows vs product images (Ovcharenko & Schelter 2025).
- **Residual gap.** None of these covers corpus-level discovery across *heterogeneous business records*: contracts, invoices, payment ledgers, registry extracts, scanned stamped copies and charts in management reports. That setting requires three things:
  1. Entity and time alignment *before* comparison, because the same vendor appears under three name variants.
  2. Unit, scale and currency normalization.
  3. Separating **explained discrepancies** (amendments, credit notes, partial payments, FX) from **unexplained contradictions**. This is where false-positive rates decide whether analysts can use the system.
- **Coverage caveat:** searches on text–table numeric inconsistency in financial reports were not completed (see §7).
- **Honest size:** medium.

### (d) Formal problem statement

Documents span modalities $\mu \in \{\text{text}, \text{table}, \text{chart}, \text{scan}, \text{record}\}$. Each yields assertions $a = (e, p, v, u, \tau, \ell, \mu, \kappa)$: entity, attribute, value, unit, time, locator, modality and extraction confidence. Given entity clusters $E$ and an attribute-compatibility relation, the comparable pairs are

$P = \{(a,a') : E(e)=E(e'),\ \text{compat}(p,p'),\ \tau \cap \tau' \neq \emptyset,\ d \neq d'\}$.

A pair is a contradiction, $y(a,a') = 1$, iff $\text{dist}_p(\text{norm}(v,u), \text{norm}(v',u')) > \text{tol}_p$ and no explaining assertion $x$ exists with $\text{explains}(x, a, a')$.

**Task:** return a ranked list $R \subseteq P$ with locators and explanations that maximizes recall at an analyst budget $k$, subject to a false-positive rate on benign variations of at most $\alpha$.

### (e) Candidate method: normalize, block, compare, explain

1. **Modality adapters that emit assertion JSON with locators**
   - Text: schema-constrained LLM extraction.
   - Tables: the existing table parser, with an LLM mapping headers to attributes once per table.
   - Charts: DePlot-style chart-to-table or a VLM, with axis-resolution metadata.
   - Scans: OCR with word boxes, then the text or table path.
   - Records: CSV/DB rows used directly.
2. **Normalization.** Handle scale words ("in thousands"), parentheses for negatives, % vs percentage points, dated FX, date granularity, and IBAN/VAT checksums.
3. **Blocking.** Block on (ER cluster × attribute × time window), so the number of pairs stays small and the method runs on CPU.
4. **Typed comparators.** Compare at the coarser of the two precisions. Chart tolerance is proportional to axis resolution. Free text goes through a CPU NLI cross-encoder first, and only uncertain pairs reach an LLM adjudicator.
5. **Explainer search.** Use rules plus an LLM over the KG to look for amendments, credit notes, partial-payment sums or FX, and down-weight a pair when one is found.
6. **Score.** $P(\text{contr.}) = P(\text{both extractions right}) \cdot P(\text{incompatible} \mid \text{norm}) \cdot (1 - P(\text{explained}))$, with the extraction terms coming from A.

### (f) Experiment design

- **Datasets**
  - Synthetic benchmark (primary; gold cross-modal pairs and benign variations).
  - FinDVer (financial hybrid documents; license not verified).
  - TAT-QA and FinQA, for the normalization and numeracy components.
  - TabFact, FEVEROUS and SciTab, with refuted claims treated as contradiction against the table.
  - ChartCheck and ChartQA, for chart reading.
  - MMIR and PRISMM-Bench, as an external multimodal sanity check (licenses not verified).
  - ContraDoc (text only).
- **Baselines**
  1. A frontier VLM on document pairs with a "list contradictions" prompt.
  2. All-pairs chunk NLI (DeBERTa-MNLI or MiniCheck) after hybrid-retrieval blocking.
  3. An LLM over GraphRAG-extracted triples.
  4. Kontrast-style table vs KG comparison.
  5. Rule-only comparators.
- **Metrics**
  - Pair-level P/R/F1, where a match requires locator overlap with gold.
  - P@k and R@k for k ∈ {10, 25, 50}.
  - **FP rate on benign variations.**
  - A confusion breakdown per modality pair.
  - Explanation correctness, human-rated on a sample.
  - $ per 100 documents, and latency.
- **Ablations:** remove blocking, normalization or explainer search. Compare chart extractors. Vary OCR degradation and remove confidence weighting.

### (g) Publishability verdict

A **conference** is possible as a *benchmark plus strong baseline* (ACL/EMNLP Findings, or a NeurIPS Datasets & Benchmarks track), but only if it includes real documents with human-annotated contradictions. The method alone is **workshop-level**.

Risks:

- Rapid 2025–26 activity (MMIR, PRISMM, Kontrast).
- Real annotated multimodal business documents are expensive and constrained by licensing (FinanceBench is non-commercial).
- A pipeline may be judged as engineering.
- The search coverage gap noted above.

---

## 3. Direction C: Temporal knowledge reconstruction

### (c) Remaining gap

- **Already solved:**
  - Within-document temporal relation extraction (TimeML, TempEval-3, TB-Dense, MATRES). Zero-shot LLMs were weak and inconsistent (Yuan et al. 2023), but global graph generation closes much of the gap (OmniTemp, EMNLP 2025).
  - Bi-temporal KG storage for agent memory (Graphiti/Zep; ATOM's dual time).
  - Time-sensitive QA benchmarks (TimeQA, TempReason, ToT, LongMemEval, TempRAGEval).
  - Truth that changes over time (Dong et al. 2009).
- **Weak or old:** cross-document timeline construction. The best F1 at SemEval-2015 Task 4 was 7.85.
- **Residual gap.** No system or benchmark was found that reconstructs a cross-document timeline from *incomplete and contradictory* evidence and does all three of the following:
  1. Represents uncertainty explicitly, for example "payment between 3 and 10 March".
  2. Resolves conflicts using source reliability.
  3. Returns the *minimal conflicting evidence set* for each timeline break.

  ATOM's README (per search summary) states that it does not handle temporal and logical conflict resolution.
- **Honest size:** medium as a task. The tools (Allen algebra, Simple Temporal Problems, MaxSAT) are classical.

### (d) Formal problem statement

Events $V$ have intervals $[s_v, f_v]$ in integer days. Evidence induces three kinds of constraints:

- Unary bounds, e.g. "March 2024" gives $s_v \in [\text{2024-03-01}, \text{2024-03-31}]$.
- Difference constraints, $s_u - s_v \le c$ ("within 30 days of").
- Document-creation-time bounds, $f_v \le \mathrm{DCT}(d)$ for events reported in the past tense.

There are also domain constraints, e.g. $s_{\text{payment}} \ge s_{\text{invoice}}$ and $s_{\text{invoice}} \in [s_{\text{contract}}, f_{\text{contract}}]$. Each constraint $k$ carries a weight $w_k$, the log-odds of its reliability (from A).

**Output:**

1. An assignment minimizing $\sum_k w_k \cdot \mathbb{1}[\text{violated}_k]$.
2. Marginal feasible intervals for each event.
3. The set of minimal infeasible subsets (timeline breaks), ranked by the weight that must be dropped to restore consistency.

### (e) Candidate method

1. LLM plus HeidelTime-style extraction of TIMEX values (with granularity) and relation cues into a typed constraint list with locators.
2. Build the STP distance graph and use Bellman–Ford to find negative cycles. Each negative cycle is a conflict set (Dechter, Meiri & Pearl 1991). Resolve by dropping the lowest-weight constraints, or solve exactly with OR-Tools CP-SAT on small graphs.
3. Get uncertainty by Monte Carlo over constraint inclusion with reliability probabilities, which yields interval marginals and a "break probability".
4. Store results bi-temporally (valid time vs ingestion time), as in Graphiti. Use the LLM only to verbalize explanations.

### (f) Experiment design

- **Datasets**
  - Synthetic benchmark (gold timelines with injected backdating, out-of-order payments and missing documents).
  - MATRES and OmniTemp, for the relation component.
  - TimeQA, TempReason and ToT, for temporal QA.
  - LongMemEval's temporal-reasoning and knowledge-update subsets, for comparison with agent-memory systems.
  - SemEval-2015 TimeLine (availability and license not verified).
- **Baselines:** Graphiti/Zep, ATOM, a long-context LLM generating the timeline directly, Beyond-Pairwise global generation, and rule-only extraction (HeidelTime, then sort).
- **Metrics:**
  - Endpoint MAE in days.
  - Interval coverage vs width (sharpness).
  - Temporal relation F1.
  - Transitivity-violation rate.
  - Timeline-break P/R, matching on overlap with gold minimal infeasible subsets.
  - Timeline-QA accuracy.
- **Ablations:** remove DCT bounds, domain constraints or reliability weights. Compare hard vs soft constraints and LLM vs rule extraction.

### (g) Publishability verdict

**Workshop.** A conference is **unlikely** unless a new, human-annotated, real cross-document corpus is released.

Risk: reviewers will read it as "STP plus LLM extraction". Benchmark coverage is also incomplete (the timeline-reconstruction search was not done). This is still worth building as a product feature, because timeline-break detection is high-value for investigations.

---

## 4. Direction D: Active evidence acquisition

### (c) Remaining gap

- **Already solved:**
  - VOI theory (Howard 1966; Krause & Guestrin 2005; adaptive submodularity).
  - Active feature acquisition over a *fixed feature schema* (Saar-Tsechansky et al. 2009; EDDI; GSMRL; AA-POMDP).
  - Deciding *when* or *what* to retrieve from an **existing index** (FLARE, Self-RAG, CRAG, Adaptive-RAG, DRAGIN, Search-R1).
  - Asking a user or oracle questions by information gain (UoT, MediQ, QuestBench, BED-LLM).
  - Selecting among costed evidence tiers that are already retrievable (Cost-aware RAG, 2026).
- **Residual gap.** Recommending which **document the analyst does not yet have** should be obtained next. Here actions are typed by gaps in the KG ("bank statement for vendor X, March 2025"), outcomes must be *predicted from the KG* before the document exists, costs differ by type, and value is measured by the effect on the investigation's decisions.

  The closest prior work is BED-LLM (EIG with explicit belief updates) plus Cost-aware RAG. Neither grounds actions or outcome models in a structured evidence graph.
- **Honest size:** medium–large. This is the most distinctive of the five, and the hardest to evaluate.

### (d) Formal problem statement

At step $t$ the state is the KG $K_t$, a hypothesis set $H$ and beliefs $b_t(h) = P(h \mid K_t)$. Actions are $a \in A_t$ (request(type, entity, period) or query(record system)) with cost $c(a) > 0$ and random outcome $Y_a$, which is either a document or "not available". The outcome model is $q(Y_a \mid K_t)$.

**Goal:** find a policy $\pi$ under budget $B$ that maximizes expected terminal utility $\mathbb{E}[U(b_T)]$, for example decision accuracy on $H$ net of misclassification costs.

The greedy rule is $a^* = \arg\max_a \mathrm{VOI}(a)/c(a)$, with $\mathrm{VOI}(a) = \mathbb{E}_{Y \sim q}[U(b_{t+1}^{a,Y})] - U(b_t)$.

### (e) Candidate method: KG-grounded VOI

1. **Gap detection.** Rules over the KG find expected-but-missing evidence: an invoice with no payment, a contract with no termination notice, an entity with no registry extract, a monthly series with a gap. LLM proposals are added, constrained to a typed action schema.
2. **Discrete outcome model.** Each action has 2–4 outcome classes, such as "payment found and matching", "found but mismatched" and "not found". Their probabilities mix KG base rates (how often similar invoices had matching payments) with LLM elicitation.
3. **VOI by simulation.** Insert hypothetical evidence for each outcome class, rerun A's fusion model incrementally on CPU, and compute the change in utility. Compute EIG or decision-VOI per unit cost, chosen greedily with an optional 2-step lookahead.
4. **Stop rule and output.** Stop when VOI/c falls below a threshold or the budget runs out. Output a ranked request list with a rationale for each item ("would resolve finding F3; 62% chance it flips").

### (f) Experiment design

- **Simulator.** Use synthetic benchmark universes with a *withheld* partition: about 40% of documents are hidden, each keyed to an action and costed by type. A weaker transfer test hides gold supporting documents in HotpotQA, 2Wiki and MultiHop-RAG.
- **Baselines:** random, cheapest-first, uncertainty sampling, an LLM "what should I request next?" prompt, FLARE/Self-RAG-style confidence triggers adapted to acquisition, BED-LLM-style EIG with LLM-only beliefs, the greedy and knapsack selectors from Cost-aware RAG, and an oracle best-in-hindsight.
- **Metrics:**
  - Area under the decision-accuracy vs cumulative-cost curve.
  - Cost to reach 90% of oracle accuracy.
  - Finding recall at budget.
  - **Outcome-model calibration** (Brier and log-loss on revealed outcomes).
  - The fraction of requests that changed a decision.
- **Ablations:** outcome-model source (KG, LLM or a mix), myopic vs lookahead, cost misspecification, and belief model (DACF vs verbalized LLM).

### (g) Publishability verdict

**Workshop likely.** A **conference** (AAAI/KDD applied track, or a main track if the estimator is principled and clearly beats BED-LLM-style baselines) is possible.

Risks:

- Simulator realism. Reviewers will ask whether the outcome distribution resembles real investigations.
- BED-LLM (ICLR 2026) and Cost-aware RAG (2026) are close and moving fast.
- D depends on A for beliefs, so it should come after A.

---

## 5. Direction E: Investigation robustness and counterfactual sensitivity

### (c) Remaining gap

- **Already solved at the single-answer level:**
  - Citation correctness metrics (AIS, ALCE, AttributionBench).
  - Correctness vs faithfulness (Wallat et al.).
  - Ablation-based context attribution (ContextCite, TracLLM, Shapley over retrieved documents).
  - Noise, counterfactual and poisoning robustness (RGB, ClashEval, PoisonedRAG, RobustRAG with certified bounds).
  - Sufficiency (Sufficient Context).
  - Per-evidence remove, replace and duplicate interventions on multi-hop QA (CUE-R, EviScope, BAR-RAG; all 2026).
- **Residual gap.** CUE-R explicitly lists deeper agentic workflows as future work. Prior work does not:
  1. Compute *source-level deletion fragility* for findings produced by a **multi-step agent over a KG**, where support flows through extraction, entity resolution, rules and LLM synthesis.
  2. Use **lineage** (provenance semirings) to get exact answers for the deterministic steps and approximate only the LLM steps.
  3. Validate the estimate against real re-runs at a known cost.
  4. Feed fragility into human review prioritization.
- **Coverage caveat:** the search on provenance and lineage for LLM agent pipelines was not completed (§7).
- **Honest size:** small–medium.

### (d) Formal problem statement

A corpus $D$ has sources $S$ and $\sigma: D \to S$. A stochastic pipeline $\Pi$ produces findings $F = \Pi(D)$. A finding $f$ "holds" under corpus $D'$ if it appears in at least $\lceil r/2 \rceil$ of $r$ runs of $\Pi(D')$.

**Fragility** is $\varphi(f) = \min\{|T| : T \subseteq S,\ f \text{ does not hold under } D \setminus \sigma^{-1}(T)\}$, which is $\infty$ if the finding never flips. Optionally it can be weighted by source cost, or counted over *effective* sources after collapsing dependence (A).

**Task:** estimate $\hat\varphi(f)$ and the minimizing set $\hat T(f)$ using far fewer than the exhaustive number of runs, such that $\hat\varphi$ agrees with $\varphi$ measured by actual re-runs. Report the cost in LLM calls.

### (e) Candidate method: lineage-first fragility

1. **Instrument provenance.** Every KG fact stores why-provenance as a monotone Boolean formula over source IDs. Joins are AND, and alternative derivations are OR. Entity-resolution merges contribute the sources of the records that were linked.
2. **Agent steps.** Each intermediate claim records the facts and chunks it consumed. For LLM synthesis steps, estimate source-level dependence with a ContextCite-style linear surrogate over random source ablations (sources number only in the tens). Alternatively, run leave-one-source-out on *that step only*.
3. **Compose lineage into the finding** and compute a **minimum hitting set** over its DNF clauses. This is exact by brute force or ILP at MindDoc scale, and it gives $\hat\varphi$ and $\hat T$. With A, copies are counted once.
4. **Validate** by sampling deletion sets (all singletons, plus pairs for fragile findings) and re-running the full pipeline $r$ times.
5. **Surface** the result in review: "rests on 1 effective source", sorting the queue by fragility × impact.

### (f) Experiment design

- **Datasets:**
  - Synthetic benchmark, with planted single-source findings, redundantly supported findings and *copied-support* findings.
  - HotpotQA (distractor) and 2WikiMultihopQA. Gold supporting facts and evidence triples give the expected fragility structure.
  - MultiHop-RAG (2–4 evidence documents per query).
  - Reproductions of the CUE-R and EviScope protocols, as comparison points.
- **Baselines:** citation count, ContextCite (aggregated per source), TracLLM, leave-one-out re-run, TMC-Shapley (Nematov et al.), and RobustRAG isolate-then-aggregate as a robustness reference.
- **Metrics:**
  - Flip-prediction AUROC/AUPRC over (finding, deletion set).
  - Exact match and Jaccard of $\hat T$ vs $T$.
  - Kendall τ between $\hat\varphi$ and $\varphi$.
  - Flip-probability calibration.
  - **LLM calls per finding** (cost).
  - Review utility: wrong findings caught when reviewing the top-k most fragile.
- **Ablations:** lineage-only vs surrogate-only vs hybrid, with and without dependence collapse, number of repeats $r$, and agent depth (1 step vs multi-step).

### (g) Publishability verdict

A **workshop** is very likely. A **conference** (SIGIR/CIKM short paper, ACL/EMNLP Findings) is possible if the hybrid estimator matches re-run ground truth at ≥10× lower cost and improves review outcomes.

Risks:

- The area is crowded, with relevant preprints appearing monthly in 2026.
- Agent nondeterminism makes ground truth noisy, so $r \ge 3$ repeats are needed.
- Reviewers may say "database provenance is known". The contribution must be the hybrid estimator, its validation and the investigation setting.

---

## 6. Which direction first: E

1. **Rigorous evaluation without human labels.** Ground truth for fragility comes from actually re-running the pipeline with sources removed. This is cheap at MindDoc scale (tens to hundreds of documents) on CPU plus API calls.
2. **It is mostly instrumentation.** MindDoc already stores citations and trace per answer (`chat_messages.meta_json`, per `docs/ARCHITECTURE.md`). It also keeps document and chunk references on entities and relations (`app/database/models.py`). Lineage propagation and a deletion harness are a few weeks of work.
3. **It closes an explicitly stated gap.** CUE-R names agentic workflows as future work. E's contribution (lineage plus surrogate for multi-step KG-mediated findings) is narrow and well defined.
4. **It is a direct product feature.** Fragility badges and a fragility-sorted review queue support the human-review step and the "evidence-backed" positioning.
5. **It sets up the others.** Dependence collapse (A) slots into the fragility count, and the deletion harness doubles as D's simulator machinery.

**Suggested sequence:**

1. E, plus the synthetic benchmark (months 1–2).
2. A (months 2–3), reusing the benchmark's copy-rate knobs.
3. The B benchmark track in parallel, if real annotated documents can be sourced.
4. D after A.
5. C as a product feature unless a corpus opportunity appears.

---

## 7. Before committing: required checks and kill criteria

| Check | Why | Kill or pivot if… |
|---|---|---|
| Search "provenance / lineage tracking for LLM agents or RAG pipelines", "why-provenance + LLM", and "data provenance agentic workflows" (2024–2026) | Not completed this session (search budget exhausted) | A paper already computes minimal source-deletion sets for multi-step agent findings and validates them by re-runs. If so, pivot to A. |
| Search "timeline reconstruction from conflicting documents benchmark" | Not completed | A released benchmark already covers C's setting. If so, reuse it rather than build one. |
| Search "numerical inconsistency text vs tables financial reports" | Not completed | Prior work covers B's enterprise setting. If so, B becomes benchmark-only or is dropped. |
| Read the full text of Evidence Laundering (EMNLP 2026) and Cost-aware RAG (2026) | Only abstracts and first pages were read | They already include soft dependence with calibration (A) or KG-typed acquisition (D). |
| Check whether CUE-R and EviScope released code and data | Needed for comparability | — |

---

## 8. Cross-cutting evaluation rules for the whole system

1. **Evaluate each layer** with the dataset and metric map in BENCHMARK_DATASETS.md §2, before running end-to-end tests.
2. **Control LLM-judge bias.** Swap answer order, align answer lengths, and run several trials, reporting the median and IQR. This follows Zeng et al. 2025 and Han et al. 2025. Validate every judge against at least 100 human-labeled items and report Cohen's κ. The judge model must differ from the system model.
3. **Account for stochastic runs.** Use at least 3 runs and report mean ± 95% CI (paired bootstrap) and pass^k (τ-bench).
4. **Report cost.** Give $ and tokens per query and per investigation, alongside accuracy (Kapoor et al., TMLR 2025).
5. **Contamination.** Public benchmarks predate model cutoffs, so lead with the synthetic benchmark generated from fresh seeds and with held-out templates.
6. **Split by question type.** Report single-hop, multi-hop and global questions separately when comparing with GraphRAG (Han et al.; GraphRAG-Bench).
7. **Pre-register** metrics, baselines and seeds in the repository before running the final test split.

---

## Sources

- Truth discovery and dependence: https://lunadong.com/publication/dependence_vldb.pdf · https://lunadong.com/publication/lifespan_vldb.pdf · https://arxiv.org/abs/1502.03519 · https://research.google/pubs/pub45634/ · https://arxiv.org/abs/1505.02463 · https://arxiv.org/abs/1503.00303
- KG calibration and construction: https://arxiv.org/abs/1912.10000 · https://aclanthology.org/2020.emnlp-main.667 · https://arxiv.org/abs/2405.16929 · https://arxiv.org/abs/2308.02357 · https://aclanthology.org/2024.emnlp-main.548/ · https://arxiv.org/abs/2502.09956 · https://arxiv.org/abs/2510.22590 · https://arxiv.org/abs/2509.15464
- Conflicts and independence: https://arxiv.org/abs/2403.08319 · https://arxiv.org/abs/2504.13079 · https://arxiv.org/abs/2506.08500 · https://www.ijcai.org/proceedings/2025/1073 · https://arxiv.org/abs/2601.03746 · https://aclanthology.org/2026.emnlp-main.509.pdf
- Cross-modal verification and inconsistency: https://arxiv.org/abs/2106.05707 · https://aclanthology.org/2023.emnlp-main.483 · https://aclanthology.org/2024.findings-acl.828 · https://aclanthology.org/2024.emnlp-main.818 · https://arxiv.org/abs/2403.17169 · https://aclanthology.org/2024.naacl-long.362 · https://arxiv.org/abs/2502.16033 · https://arxiv.org/abs/2510.16505 · https://arxiv.org/abs/2607.25959 · https://arxiv.org/abs/2510.12383
- Temporal: https://aclanthology.org/P18-1122/ · https://aclanthology.org/S13-2001.pdf · https://arxiv.org/abs/2304.05454 · https://arxiv.org/abs/2502.11114 · https://preview.aclanthology.org/setup/S15-2132 · https://arxiv.org/abs/2501.13956 · https://arxiv.org/abs/2108.06314 · https://arxiv.org/abs/2406.09170 · https://arxiv.org/abs/2410.10813 · https://github.com/AuvaLab/itext2kg
- Acquisition and information seeking: https://proceedings.mlr.press/v97/ma19c.html · https://arxiv.org/abs/2010.02433 · https://proceedings.mlr.press/v258/li25h.html · https://arxiv.org/abs/2401.15884 · https://aclanthology.org/2024.naacl-long.389 · https://arxiv.org/abs/2402.03271 · https://arxiv.org/abs/2406.00922 · https://arxiv.org/abs/2503.22674 · https://arxiv.org/abs/2508.21184 · https://arxiv.org/abs/2606.02245 · https://arxiv.org/abs/2411.00784
- Robustness and attribution: https://arxiv.org/abs/2112.12870 · https://arxiv.org/abs/2305.14627 · https://aclanthology.org/2024.findings-acl.886 · https://arxiv.org/abs/2412.18004 · https://arxiv.org/abs/2409.00729 · https://arxiv.org/abs/2506.04202 · https://arxiv.org/abs/2507.04480 · https://arxiv.org/abs/2309.01431 · https://arxiv.org/abs/2405.15556 · https://arxiv.org/abs/2402.07867 · https://arxiv.org/abs/2411.06037 · https://arxiv.org/abs/2604.05467 · https://www.alphaxiv.org/abs/2609.17081 · https://arxiv.org/pdf/2602.03689
- Evaluation methodology: https://arxiv.org/abs/2502.11371 · https://arxiv.org/abs/2506.06331 · https://arxiv.org/abs/2506.05690 · https://arxiv.org/abs/2406.12045 · https://arxiv.org/abs/2407.01502
- Classical references tagged [K] in RESEARCH_PAPERS.md (Dechter et al. 1991, Allen 1983, Green et al. 2007, Howard 1966, Golovin & Krause 2011) were not re-fetched this session.
