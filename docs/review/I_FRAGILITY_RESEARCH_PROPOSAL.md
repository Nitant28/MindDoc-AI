# I. Research proposal: leave-one-source-out (LOSO) fragility for investigation findings

*Deliverable I of the 2026-11-10 review. Status: **proposal, nothing implemented.** It narrows Direction E of
[RESEARCH_GAPS.md](../research/RESEARCH_GAPS.md) (§5, §6) to one measurable object, the LOSO fragility of a finding,
and fixes its definitions, baselines, experiment and kill criteria before any code is written.*

**How to read this.** Statements are tagged **[Established]** (follows from definitions or verified prior work),
**[Hypothesis]** (something we expect and must test) or **[Proposed]** (a design choice we are making). Every external
reference in §3 and the reference list was opened during this session and is marked **[verified]**; anything that
could not be checked is omitted or says so. Legal sources in §1 are secondary reports of judgments, labelled as such.

---

## 0. Summary

- **What:** for each finding (e.g. "₹4.0 cr of the 12 Mar 2025 term-loan disbursement reached a related party within
  3 days"), re-run the pipeline with each *independent source cluster* removed, and report which clusters the finding
  needs, which it merely cites, which it secretly depends on, and the smallest number of clusters whose removal kills
  it (**k-fragility**).
- **Why:** a borrower is ordinarily entitled to the forensic audit report and the material relied upon, and will
  attack specific documents. The reviewer must know, before issuing the report, which findings collapse if one
  document is excluded or discredited.
- **What it is not:** robustness to source removal is a property of the *evidential basis* of a finding, measured
  on *our pipeline*. It is not evidence that the finding is true (§2.2, §6).
- **Feasibility:** ground truth is computable by re-running the pipeline, so the core experiment needs no human
  labels. The cost is a formula in the number of clusters, runs and LLM calls (§2.9, §5.7).
- **Realistic venue:** workshop paper; a short main-track or Findings paper only if a cheap estimator matches
  exhaustive re-runs at much lower cost *and* the measured fragility tracks generator-known necessity (§8).

---

## 1. Problem statement and motivation

### 1.1 The reviewer's question

A lender-side forensic finding is assembled from many documents: bank statements (issued by the bank), GST returns
(from the GST portal), director and charge data (MCA registry), the borrower's ledger, stock statements and invoices
(prepared by the borrower or its counterparties). MindDoc's planned pipeline turns them into findings through parsing →
claims with evidence → entity resolution → deterministic detectors (D1–D7 in
[INVESTIGATION_ENGINE.md](../architecture/INVESTIGATION_ENGINE.md) §5) → an evidence-constrained LLM investigator.

Before a finding goes into a report, the reviewer needs four answers:

1. **Which sources does it actually rest on?** Not which ones it cites: an LLM can cite a document it did not need,
   and a finding can depend on a source it never cites (for example, an entity-resolution merge enabled by a phone
   number in an uncited KYC form).
2. **Are those sources independent?** A bank statement PDF and the borrower's Excel export of the same statement
   are two files but one origin. Counting them twice makes a finding look corroborated when it is not.
3. **If one source is excluded, discredited or shown to be mis-read, does the finding survive?**
4. **Is the finding stable at all,** or does it come and go between runs even when nothing changes?

### 1.2 The regulatory angle

- **[Established, secondary source]** In *State Bank of India v. Amit Iron Pvt. Ltd.* (2026 INSC 323, reported
  7 Apr 2026), the Supreme Court held that a personal hearing is not automatically required before an account is
  classified as fraud. A show-cause notice, a written representation and a reasoned order suffice, but borrowers
  should generally receive the *full* forensic audit report, not conclusions or extracts, with narrow exceptions
  (Verdictum report, [verified]). This builds on *SBI v. Rajesh Agarwal* (27 Mar 2023), which read natural justice
  into fraud classification (judgment PDF listed in `docs/strategy/MARKET_SELECTION.md` [S5]; not re-opened here).
- **Consequence [Proposed reading]:** the borrower's written representation will target specific documents ("that
  invoice is not ours", "that page was mis-read"). A firm that knows each finding's essential sources can answer
  this before issuing the report: either corroborate the finding from an independent cluster or state its single-
  source basis openly. A finding with *hidden dependence* on an uncited document is also a disclosure problem, because
  the material relied upon is then larger than the material shown.
- **Practice already asks for this, informally.** Heuer's Analysis of Competing Hypotheses includes, as step 6,
  analysing how sensitive the conclusion is to a few critical items of evidence (Heuer 1999, [verified]). Practitioner
  guidance on critiquing expert reports recommends checking what happens to the conclusions if statements without
  third-party support are removed (Bell & Wong, Grant Thornton Australia, 2024, practitioner blog, [verified]).
  LOSO makes that check mechanical, repeatable and source-level.

### 1.3 Why existing signals are not enough

- **Citation counts conflate copies with corroboration.** Agents treat paraphrased same-origin sources as independent
  confirmation (Evidence Laundering, EMNLP 2026, [verified]).
- **Citations are not dependence.** A citation can support a statement without having been used: up to 57% of
  citations were post-rationalised in one RAG study (Wallat et al. 2024, [verified]). The repo's claim verifier v2
  (`app/ai/verifier.py`) checks that a cited source is *consistent* with a sentence; it cannot say whether the
  finding *needed* that source.
- **Single-answer attribution does not cover a multi-stage pipeline.** Context-attribution methods (ContextCite,
  AttriBoT, TracLLM) score the spans inside one prompt. A MindDoc finding is produced by extraction, entity
  resolution, deterministic detectors and then an LLM, so a source can matter through a stage the LLM never sees.

---

## 2. Definitions

### 2.1 Setup and notation [Proposed]

| Symbol | Meaning |
|---|---|
| $D = \{d_1,\dots,d_n\}$ | documents in one case (investigation scope) |
| $\Pi_\theta(D;\omega) = F$ | pipeline run: configuration $\theta$ (git commit, model ids, prompt versions, thresholds) pinned; randomness $\omega$ (seed, LLM sampling, and uncontrollable server-side non-determinism of API models) |
| $F$ | set of findings produced by one run |
| $\mathrm{sig}(f) = (t_f, E_f, \tau_f, a_f)$ | finding signature: type (detector or hypothesis template), core entities keyed by **strong identifiers** (PAN, GSTIN, CIN, DIN, account number + IFSC; never internal entity ids, which change when sources are removed), time interval, magnitude (amount in paise, or a count) |
| $\mathrm{cite}(f) \subseteq D$ | documents holding the evidence regions behind $f$'s supporting claims |
| $\mathcal{S} = \{S_1,\dots,S_m\}$ | partition of $D$ into source clusters (§2.3) |
| $\mathcal{S}_f$ | clusters that contain at least one document in $\mathrm{cite}(f)$ |
| $\mathcal{N}_f \supseteq \mathcal{S}_f$ | lineage neighbourhood: clusters that contributed to any claim, resolution decision or detector input on $f$'s derivation path |
| $D_{-T}$ | $D \setminus \bigcup_{S \in T} S$ for $T \subseteq \mathcal{S}$ |
| $r_0,\ r$ | runs on the full corpus, runs per removal set |

### 2.2 Five properties that must not be confused

| Property | Question it answers | What it is a property of | Formal handle (below) | What the test varies |
|---|---|---|---|---|
| **Evidence dependence** | Which sources does $f$ need? | $(f, \Pi_\theta, D)$ | necessity $\nu_f(S)$, essential set $\mathrm{Ess}(f)$, witness sets $W_i$ | remove sources |
| **Source independence** | Could two sources be wrong for the same reason? | pairs of documents, before any finding exists | derivation graph, clusters $\mathcal{S}$ | nothing is re-run; it is estimated from the documents |
| **Finding robustness** | Does $f$ survive removal or perturbation of sources? | $(f, \Pi_\theta, D)$ plus a perturbation family | $\mathrm{LOSO}(f)$, $\kappa_f$, graded persistence $g_f$ | remove / replace / duplicate clusters |
| **Model instability** | Does $f$ change when the evidence does not? | $(f, \Pi_\theta, D)$ over $\omega$ and nearby $\theta'$ | $1 - h_f(\emptyset)$ | seeds, sampling, prompt order, paraphrased prompts |
| **Causal validity (truth)** | Did the described event actually happen? | the world | $z_f \in \{0,1\}$ | nothing in the pipeline; needs external verification |

Formally:

- **Independence [Proposed].** Two documents $d, d'$ are *independent with respect to claim* $c$ if what they report
  is conditionally independent given the truth: $P(v_d, v_{d'} \mid z_c) = P(v_d \mid z_c)\,P(v_{d'} \mid z_c)$.
  A copy violates this completely. Documents prepared by the same party, or produced by the same OCR template, can
  violate it partly. This is the source-dependence notion of truth discovery (Dong et al. 2009, [verified]), applied
  to documents instead of web sources.
- **Dependence** is about one finding and our pipeline. **Robustness** combines dependence with independence:
  without clusters, robustness is inflated by copies (Proposition P1 below).
- **Instability** is the noise floor. A drop in persistence after removing $S$ means nothing unless it exceeds the
  run-to-run variation on the unchanged corpus. "Deterministic" LLM settings still varied by up to 15% in accuracy
  across runs in one study (Atil et al., [verified]).
- **Truth is outside LOSO's reach.** LOSO measures the causal effect of an *input source on the pipeline's
  output*. That is a causal statement about the pipeline, not about the world.

Three consequences, which follow directly from the definitions [Established]:

- **P1 (copies inflate document-level robustness).** If $d'$ is a copy of $d$, removing $d$ alone leaves $d'$, so
  document-level necessity of $d$ is zero even when the finding has one origin. Removing the cluster $\{d, d'\}$
  gives the right answer.
- **P2 (robust does not mean true; fragile does not mean false).** If all witnesses share a common-cause error that
  the clustering missed (a forged document copied into a second one we failed to link; an entity-resolution rule that
  wrongly merges two companies in every run), $f$ is robust and false. A finding resting on one bank-issued statement
  ($\kappa_f = 1$) may be entirely true.
- **P3 (instability limits what can be detected).** With few runs, only large drops in persistence are
  statistically distinguishable from noise (worked numbers in §5.5).

### 2.3 Source clusters: the unit of removal [Proposed]

Build a directed **derivation graph** $G_{\mathrm{der}}$ on $D$ with an edge $d \to d'$ when:

1. $d'$ supersedes $d$ (a newer version of the same document: `supersedes` chain);
2. $d'$ is a near-duplicate of $d$ (MinHash Jaccard $\ge \tau_J$ on normalised text, or on transaction rows for
   statements);
3. $d'$ is derived from $d$: an explicit reference ("as per statement dated …"), or $d'$ reproduces $d$'s values
   *including its deviations from other sources*. Sharing errors is the copy signal of Dong et al. 2009.

**Copy clusters** $\mathcal{S}^{\mathrm{copy}}$ are the weakly connected components of $G_{\mathrm{der}}$. This is the
default unit.

**Control groups** $\mathcal{S}^{\mathrm{ctrl}}$ are a coarser, optional unit. Map each document to the party that
controlled its content, $\gamma: D \to \{\text{bank}, \text{GST portal}, \text{MCA}, \text{borrower},
\text{counterparty}, \dots\}$, and take the finest partition that is coarser than both $\mathcal{S}^{\mathrm{copy}}$
and the partition by $\gamma$. Documents in one control group can fail together (one preparer, one forger, one
template), even when they are not copies. Removing a whole control group answers "does the finding survive without
anything the borrower prepared?" This is an ablation (§5.6), not the default, because it is very coarse.

Granularity $g \in \{\text{doc}, \text{copy}, \text{ctrl}\}$ is recorded with every result. The clustering is itself
an estimate $\hat{\mathcal{S}}$, and its errors are a threat to validity (§6).

Schema alignment: F §6 defines `source_cluster.kind ∈ {same_document_versions, near_duplicate, derived_from,
same_issuer_system}`. The first three are the edge types above. `same_issuer_system` is the control-group level.

### 2.4 Finding identity across runs [Proposed]

The same finding must be recognised in a re-run even though its internal ids, wording and sometimes amount change.

- **Match score.** $\mu(f, f') = 0$ if $t_f \ne t_{f'}$. Otherwise
  $\mu(f,f') = J(E_f, E_{f'}) \cdot \mathrm{IoU}_\epsilon(\tau_f, \tau_{f'})$, where $J$ is the Jaccard overlap of
  strong identifiers and $\mathrm{IoU}_\epsilon$ is interval overlap with a slack of $\epsilon$ days. Magnitude is
  deliberately left out of identity and handled by graded persistence.
- **One-to-one assignment.** Within a run, findings are matched by maximum-weight bipartite matching over $\mu$ with a
  threshold $\tau_\mu$, so one re-run finding cannot "rescue" two originals.
- **Reference findings.** A single baseline run is not a reliable reference. Run $r_0$ times on $D$, group matched
  findings, and keep as the reference set $F^\star$ those present in at least $\eta r_0$ runs (default $\eta = 1/2$).
  Findings below that threshold are reported as **unstable**, and no fragility is computed for them.
- The matcher has a version (`matching_fn_version`). Its errors are measured against generator labels (§5.4).

### 2.5 Persistence [Proposed]

For $f \in F^\star$, removal set $T$ and run $j$, let $X_j(f, T) = 1$ if some $f' \in \Pi_\theta(D_{-T}; \omega_j)$ is
matched to $f$, and 0 otherwise.

- **Binary persistence:** $h_f(T) = \frac{1}{r_T}\sum_{j=1}^{r_T} X_j(f,T)$.
- **Graded persistence:** $g_f(T) = \frac{1}{r_T}\sum_{j} X_j(f,T)\cdot \min\!\left(1, \frac{a_{f'_j}}{a_f}\right)$,
  the share of the finding's magnitude that survives. A traced leakage dropping from ₹4.0 cr to ₹0.6 cr has
  $g = 0.15$ even though $h = 1$. Increases are capped at 1 here and recorded separately.
- **Baseline stability:** $h_f(\emptyset)$, using the $r_0$ full-corpus runs. Model instability is $1 - h_f(\emptyset)$.
- $f$ **holds** under $T$ iff $h_f(T) \ge \eta$.

### 2.6 LOSO score, essential, redundant, hidden and suppressing sources [Proposed]

- **Necessity of cluster $S$ for $f$:**
  $\nu_f(S) = \left[\dfrac{h_f(\emptyset) - h_f(\{S\})}{h_f(\emptyset)}\right]_+ \in [0,1]$.
  The graded version $\nu^g_f(S)$ uses $g_f$ instead.
- **LOSO fragility score:** $\mathrm{LOSO}(f) = \max_{S \in \mathcal{S}} \nu_f(S)$. A score of 1 means one cluster's
  removal kills the finding in every run; 0 means no single removal changes it.
- **Essential cluster:** $S \in \mathrm{Ess}(f)$ iff $f$ holds under $\emptyset$, does not hold under $\{S\}$, and the
  drop is significant (one-sided exact test on the counts $r_0 h_f(\emptyset)$ and $r_S h_f(\{S\})$ at level $\alpha$).
- **Redundant support:** $S \in \mathcal{S}_f$ (cited) with $\nu_f(S) \le \delta$. Two sub-cases must be told apart,
  because they mean opposite things:
  - *genuinely redundant:* the re-run's matched finding cites a substitute cluster that supplies the same claim type;
  - *decorative:* the re-run's finding cites nothing new. If the generator says $S$ is logically necessary, this is
    **unsupported persistence**, a hallucination signal.
- **Hidden dependence:** $S \notin \mathcal{S}_f$ but $S \in \mathrm{Ess}(f)$. The finding relies on material it does
  not cite, which matters for disclosure (§1.2).
- **Suppressor:** $S$ suppresses $g$ if $g \notin F^\star$ but $h_g(\{S\}) \ge \eta$ for a finding $g$ that **appears
  only after removal**. Typical causes are explaining documents: a credit note, a related-party disclosure, or a
  reconciling GST return. Suppressors are reported separately (`emergent_findings`) and never folded into the
  fragility of existing findings. If a suppressor is forged, a real finding is hidden, so suppressors deserve
  authenticity checks. Their existence also shows the pipeline is **non-monotone**, which matters for §2.7.

### 2.7 k-fragility and responsibility [Proposed; formal ancestry Established]

- **k-fragility:**
  $\kappa_f = \min\{|T| : T \subseteq \mathcal{S},\ h_f(T) < \eta\}$.
  Since an empty corpus yields no findings, $\kappa_f \le m$. $\kappa_f = 1$ iff $\mathrm{Ess}(f) \ne \emptyset$
  (up to the significance test).
- **Witness sets.** A witness $W \subseteq \mathcal{S}$ is a minimal set of clusters on which $f$ holds by itself. If the
  pipeline is monotone and deterministic, $f$ holds under $D_{-T}$ iff some witness $W_i$ is disjoint from $T$. Then
  $\kappa_f$ is the size of a **minimum hitting set** of $\{W_1,\dots,W_q\}$. With witnesses $\{A,B\},\{A,C\}$, the
  answer is $\kappa = 1$ ($A$). With $\{A,B\},\{C,D\}$, it is $\kappa = 2$.
- **Responsibility.** Following Chockler & Halpern (2004) and Meliou et al. (2011) [both verified]:
  $\rho_f(S) = 1/(1 + \min|\Gamma|)$ over contingency sets $\Gamma \subseteq \mathcal{S}\setminus\{S\}$ such that
  $f$ holds under $D_{-\Gamma}$ but not under $D_{-\Gamma-\{S\}}$, with $\rho_f(S) = 0$ if no such $\Gamma$ exists.
  Then $S$ is essential iff $\rho_f(S) = 1$, and $\kappa_f = \min_{S:\rho_f(S)>0} 1/\rho_f(S)$. Proof sketch: any
  contingency $\Gamma$ for $S$ gives a killing set $\Gamma \cup \{S\}$, so $\kappa_f \le 1/\rho_f(S)$. For $S$ in a
  minimum killing set $T^\star$, $T^\star\setminus\{S\}$ is a contingency, so $1/\rho_f(S) \le \kappa_f$.
  $\rho_f$ is the graded per-cluster quantity the UI can show.
- **Complexity [Established].** Minimum hitting set is NP-hard in general. Meliou et al. show responsibility for
  conjunctive queries is either PTIME or NP-hard depending on the query. At MindDoc scale (witnesses of 2–5 clusters,
  tens of clusters per neighbourhood), brute force or a small ILP is enough *when lineage is exact*. When an LLM stage
  sits on the path, there is no exact lineage, and exact $\kappa_f$ needs every subset of size $< \kappa_f$ tested:
  $\sum_{j=1}^{k}\binom{m_f}{j}$ removal sets, each run $r$ times.
- **Certification asymmetry.** One real re-run where $f$ fails certifies an *upper bound* $\kappa_f \le |T|$ (up to
  noise). A *lower bound* $\kappa_f > k$ needs all smaller sets tested, or a lineage-plus-monotonicity argument.
  Every stored $\kappa$ therefore carries `bound_type ∈ {exact, upper, lower}`.
- **Non-monotone pipelines** (detectors with explain-away rules) break the hitting-set shortcut: removing a
  suppressor can *create* support. For those findings, $\kappa_f$ is computed from re-runs only.

### 2.8 Worked example [illustrative]

Finding $f$ (detector D1 + D3): *"₹4.0 cr of the 12 Mar 2025 disbursement reached Sunrise Traders, which shares a
director with the borrower, within 3 days."*

| Cluster | Documents | Party | Role |
|---|---|---|---|
| A | $d_1$ bank statement PDF (Bank X); $d_2$ borrower's Excel export of the same statement (near-duplicate) | bank | money trail |
| B | $d_3$ MCA master data for Sunrise | registry | director link |
| E | $d_6$ director KYC form with the same mobile number | borrower | alternative link (enables an entity-resolution merge) |
| C | $d_4$ borrower ledger | borrower | cited but not used by D1 |
| G | $d_5$ Sunrise invoice to the borrower | counterparty | explains the payment as a purchase |

Witnesses are $\{A,B\}$ and $\{A,E\}$, so $\kappa_f = 1$ with $\mathrm{Ess}(f) = \{A\}$. B and E are redundant with
each other: removing the pair $\{B,E\}$ kills the related-party part. **Document-level LOO would remove $d_1$ alone,
find $d_2$ still present, and call the finding robust (P1).** If E is not cited, a significant drop after removing
$\{B,E\}$ but not $\{B\}$ reveals E as hidden support. Removing G may make a new finding appear ("payment with no
invoice"), so G is a suppressor of that finding, not part of $f$'s fragility.

Hypothetical counts with $r_0 = 10$, $r = 3$: $h(\emptyset) = 10/10$; $h(\{A\}) = 0/3$; $h(\{B\}) = h(\{E\}) =
h(\{C\}) = 3/3$; $h(\{B,E\}) = 0/3$. Result: $\mathrm{LOSO}(f) = 1$, $\kappa_f = 1$ (exact: all singletons tested),
$\rho(A) = 1$, $\rho(B) = \rho(E) = 1/2$, $\rho(C) = 0$.

### 2.9 Computational cost [Proposed]

Let $c_\Pi$ be the cost of one full pipeline run, $L$ the number of LLM calls in it, $L_f$ the LLM calls in $f$'s
investigator and verifier steps, and $m_f = |\mathcal{N}_f|$.

- **Naive exact LOSO** per case: $C_{\mathrm{naive}} = (r_0 + r\,m)\,c_\Pi$, with $(r_0 + r\,m)\,L$ LLM calls.
- **Incremental LOSO.** Parsing and per-document extraction depend on one document only, so they are cached by
  `(sha256, extractor_version)` and never re-run. Removing $S$ changes only:
  1. entity resolution on the connected components containing $S$'s mentions;
  2. detectors on the affected graph components;
  3. the LLM steps of findings with $S \in \mathcal{N}_f$.

  Deterministic stages run once per variant, and only LLM stages need $r$ repeats:
  $$C_{\mathrm{inc}} = r_0\,c_\Pi + \sum_{S \in \mathcal{S}}\Big[c_{\mathrm{ER}}(S) + c_{\mathrm{det}}(S) +
  r \sum_{f:\,S \in \mathcal{N}_f} c_{\mathrm{LLM}}(f)\Big],\qquad
  N_{\mathrm{LLM}} = r_0 L + r\sum_{f \in F^\star} m_f L_f.$$
  The LLM saving relative to naive is $\sum_f m_f L_f \,/\, (m L)$. It is large when findings have small
  neighbourhoods.
- **Catching emergent findings cheaply.** Run the (cheap, deterministic) detectors on every $D_{-S}$, and send only
  *new* candidates to the LLM.
- **Adaptive repeats.** Run $r = 3$. If all three agree with the baseline, stop. If they split, extend to
  $r_{\max}$. Deterministic findings (no LLM on the path, verified by identical output hashes) use $r = 1$.
- **Pairs and k-fragility.** Pairs are only needed for high-impact findings with $\mathrm{Ess}(f) = \emptyset$: at most
  $\binom{m_f}{2}$ sets, or fewer if lineage proposes witnesses. Greedy removal (remove the highest-$\nu$ cluster,
  repeat) gives a cheap certified upper bound.
- **Surrogate for the LLM step.** Fit a ContextCite-style model on $M$ random cluster-inclusion masks restricted to
  $\mathcal{N}_f$, $\hat h_f(T) = \sigma\big(\beta_0 + \sum_{S} \beta_S \mathbb{1}[S \notin T]\big)$. Use it to
  *propose* small killing sets, then confirm them with real re-runs. Proposals never count as results until a re-run
  confirms them.

---

## 3. Related work (verified)

Every entry was opened on its arXiv, ACL Anthology, proceedings, journal or bibliographic page this session (links in
the reference list). Venue is given only where a page stated it.

**Dropped:** BAR-RAG (arXiv 2602.03689). RESEARCH_PAPERS.md lists it as a cited-document removal check, but its
abstract describes an RL-trained boundary-aware reranker with no such protocol.

### 3.1 Leave-one-out, influence, "dropping a little data"

| Work | What it measures | Difference from LOSO fragility |
|---|---|---|
| Efron & Stein, Ann. Statist. 9(3), 1981 | Jackknife (leave-one-out) estimate of a statistic's variance; shown to be biased upward. | Variance of a smooth statistic over i.i.d. data. We test whether a discrete finding survives removal of correlated, non-exchangeable clusters. |
| Koh & Liang, ICML 2017 | Influence functions approximate the effect of removing or up-weighting a *training* point, using gradients and Hessian-vector products. | Training-time and differentiable. Our inputs are inference-time documents to a non-differentiable pipeline, and real re-runs are affordable at case scale. |
| Broderick, Giordano & Meager, arXiv 2011.14999 | Approximate Maximum Influence Perturbation: the smallest fraction of a sample whose removal overturns a conclusion. Some published economics results flip after dropping <1%. | **Closest conceptual ancestor of $\kappa_f$.** Theirs uses i.i.d. observations and an influence approximation. Ours uses dependent clusters and matched findings, validated by re-runs. |
| Ghorbani & Zou, ICML 2019 | Data Shapley: average marginal contribution over subsets; argued to beat LOO for valuing data. | Averages over coalitions and splits credit between redundant sources. $\kappa_f$ and $\mathrm{Ess}$ are minimal and worst-case. Both break without clustering. |

### 3.2 Causality, responsibility, provenance

| Work | What it measures | Difference |
|---|---|---|
| Chockler & Halpern, JAIR 22, 2004 | Degree of responsibility in structural causal models. | Same quantity, with clusters as variables and a stochastic pipeline as the model. |
| Meliou, Gatterbauer, Moore & Suciu, PVLDB 2011 | Causes and responsibility of tuples for query answers and non-answers: $\rho_t = 1/(1+\min\lvert\Gamma\rvert)$. PTIME/NP-hard dichotomy for conjunctive queries. | The formal template for §2.7, with "why-no" causes corresponding to our suppressors. They assume deterministic queries with exact lineage. We add an LLM stage, run noise and finding matching. |
| Green, Karvounarakis & Tannen, PODS 2007 | Provenance semirings: lineage of derived facts as polynomials over sources. | Makes the deterministic stages exact (witness sets come from why-provenance). Silent on LLM stages. |

### 3.3 Context attribution for LLMs and RAG

| Work | What it measures | Difference |
|---|---|---|
| ContextCite, NeurIPS 2024 | Surrogate model fit on random context ablations attributes a generated statement to context parts. | One generation, context spans, response likelihood. We need whole-pipeline re-runs, clusters and finding presence. We reuse its surrogate for the LLM step. |
| AT2, arXiv 2504.13752 | Learns to combine per-head attention weights, using ablation signal, to match ablation attribution cheaply. | A cheaper single-prompt proxy (baseline B6). |
| AttriBoT, ICLR 2025 | Fast approximation of leave-one-out *context* attribution (caching, hierarchy, proxy models; reports >300× speed-up). | LOO of one prompt's likelihood. Usable only inside our LLM step. |
| TracLLM, USENIX Security 2025 | Context traceback for long contexts by informed search, ensembling and denoising. | Single prompt. Its search is relevant for finding small killing sets. |
| Nematov et al., arXiv 2507.04480 | Exact Shapley vs approximations and other methods for retrieved documents, including redundant, complementary and synergistic ones. | Document-level, single answer. Its redundancy cases are where cluster-level removal is needed. |
| Saha Roy et al., WSDM 2025 | Counterfactual attribution: remove an evidence cluster (DBSCAN over content), regenerate $m$ times, score $1 -$ mean cosine similarity of answers. Clusters exist because redundant evidence otherwise looks unimportant. | **Closest single-answer precedent for cluster removal.** Their clusters are semantic; ours come from provenance (version, copy, derivation, issuer). Their outcome is answer similarity; ours is a matched finding. |
| RUBEN, ICDE 2026 demo | Minimal source subsets whose presence (and any superset) guarantees an output property, i.e. minimal jointly sufficient sets. | The sufficiency dual of our necessity view. These are our witness sets $W_i$, for one prompt. |

### 3.4 Counterfactual robustness and evidence sufficiency

| Work | What it measures | Difference |
|---|---|---|
| CUE-R, arXiv 2604.05467 (Apr 2026) | REMOVE, REPLACE and DUPLICATE per evidence item in single-shot RAG (HotpotQA, 2WikiMultihopQA). Scored on correctness, grounding proxy, confidence error and trace shift. Removing two supports hurts far more than either alone. **Verified:** the paper states that deeper agentic workflows, and combinatorial interventions over evidence pairs, are future work. No code link on the page. | Single-shot, item-level, answer outcome. Our setting is multi-stage findings, clusters, finding identity and minimal killing sets; their pair future work is our $\kappa = 2$ search. |
| EviScope, GroundLM workshop at EMNLP 2026 | 40 paired quartets that add, remove, distract or contradict evidence. Paired metrics expose failures that accuracy hides. | Controlled single-question benchmark. No fragility score. |
| RobustRAG, arXiv 2405.15556 | Isolate-then-aggregate gives certified quality bounds under a bounded number of *injected* passages. | Certifies against insertion. Ours measures dependence under deletion: a dual worst-case notion. |
| Sufficient Context, ICLR 2025 | Autorater for whether the context suffices, used for abstention. | Sufficiency of the whole context. We locate the necessary parts. |
| Atanasova et al., TACL 2022 | Whether fact-checkers detect evidence made insufficient by omissions (SufficientFacts). | Omission probes on single claims. |
| ERASER, ACL 2020 | Rationale comprehensiveness $m(x)_j - m(x\setminus r)_j$ and sufficiency $m(x)_j - m(r)_j$. | $\nu_f(S)$ is cluster-level comprehensiveness with a binary matched output. |
| Wallat et al., arXiv 2412.18004 | Citation correctness differs from faithfulness: up to 57% of citations were post-rationalised in their setting. | Motivates intervention over trusting citations. |

### 3.5 Source dependence and trust

| Work | What it measures | Difference |
|---|---|---|
| Dong, Berti-Equille & Srivastava, VLDB 2009 | Bayesian copy detection (shared rare or false values) inside truth discovery. | Supplies the copy signal for $G_{\mathrm{der}}$. It estimates truth from many sources; we measure one finding's dependence on a few. |
| Knowledge-Based Trust, PVLDB 8(9), 2015 | Source trustworthiness from the correctness of extracted facts, separating extraction error from source error. | A source can "fail" through our extraction. Removal cannot tell the two apart (§6). |
| Evidence Laundering, EMNLP 2026 | Agents credit paraphrased same-origin clusters like independent sources. A provenance check reduces the failure. | Studies credibility, not removal fragility. It supports clustering before counting. |

### 3.6 Provenance in LLM agents (2026)

| Work | What it measures | Difference |
|---|---|---|
| Wang et al., survey, arXiv 2606.04990 | Taxonomy of execution provenance and evidence tracing. Reports that no benchmark evaluates the complete provenance chain. | Survey. The lineage side is open, not solved. |
| Liao et al., arXiv 2607.20827 | Whether agent actions change when only a source's *authority* label changes. | Perturbs labels, not presence. |
| Yun et al., arXiv 2610.09581 | In forensic reconstruction of agent logs, LLMs give correct answers while making unsupported source assertions. Explicit record bindings help. | Supports explicit claim-to-region binding as a prerequisite. |
| Lu et al. (*Agents that Matter*), arXiv 2605.27621 | Removal-based attribution over *agents*. Reports LOO is about as effective as combinatorial methods, at lower cost. | Units are agents. Whether this holds for sources is RQ5. |

**Search caveat.** One extended search for provenance-based deletion analysis of agent findings (the check left open
in RESEARCH_GAPS §7) found the four papers above. None computes minimal source-deletion sets for multi-stage findings
validated by re-runs. One search is not proof of absence, so kill criterion K1 repeats it.

### 3.7 Intelligence and forensic analysis

| Work | What it measures | Difference |
|---|---|---|
| Heuer, *Psychology of Intelligence Analysis*, CIA CSI 1999, ch. 8 (ACH) | Step 3: the *diagnosticity* of evidence across hypotheses. Step 6: how sensitive the conclusion is to a few critical items if they were wrong. | LOSO mechanises step 6 at source level. It measures **necessity, not diagnosticity**: an item can be necessary yet consistent with the benign explanation. Hence the benign-hypothesis ablation (§5.6). |
| Dhami, Belton & Mandel, *Appl. Cogn. Psychol.* 33(6), 2019 | Randomised study of 50 analysts. ACH steps were skipped, its effect on confirmation bias was mixed, and it may increase inconsistency and error. | A structured technique must be tested, not assumed useful (§5.8). |
| Bell & Wong, Grant Thornton Australia, 2024 (practitioner blog) | Test whether conclusions survive removing statements that lack third-party support. | This is the control-group ablation. |

One search found no peer-reviewed forensic-accounting paper that formalises this. That is recorded as *not found*.

### 3.8 Model instability

- **Self-consistency (ICLR 2023):** sample several paths and take the majority answer. Used as baseline B4. It is a
  stability signal, not a dependence signal.
- **Atil et al., arXiv 2408.04667:** up to 15% run-to-run accuracy variation under "deterministic" settings.
  Justifies $r_0 > 1$.
- ***Lost in the Middle* (TACL):** position effects. Removing a source also shifts positions, so prompt order is
  randomised to avoid confounding.
- **Jain & Wallace, NAACL 2019:** attention often fails to track importance, so B6a is expected to be weak.

---

## 4. Baselines [Proposed]

Each baseline produces two outputs:

- a **finding score** $s(f)$, read as "is $\kappa_f = 1$?";
- a **cluster score** $s(f,S)$, read as "is $S$ essential?".

| ID | Baseline | Definition | Cost |
|---|---|---|---|
| B1 | Citation count | $s(f) = 1/\lvert\mathrm{cite}(f)\rvert$. Cluster score is uniform over cited documents (aggregated per cluster). | free |
| B2 | Independent cluster count | $s(f) = 1/\lvert\mathcal{S}_f\rvert$. Flag $\kappa = 1$ iff some evidence-template slot (e.g. "money trail", "relationship") is filled by exactly one cluster; that cluster gets $s(f,S) = 1$. | free once clusters exist |
| B3 | Retrieval-rank perturbation | Re-run only the LLM step with retrieval perturbed: drop the top-1 chunk, shuffle order, use $k/2$ and $2k$. $s(f) = 1 -$ mean persistence. Not source-aware, so the cluster score is the cluster of the dropped chunk. | $\approx 4r$ LLM steps per finding |
| B4 | LLM self-consistency | $s(f) = 1 - h_f(\emptyset)$ from the $r_0$ baseline runs. No cluster score. Tests whether instability is mistaken for fragility. | reuses baseline runs |
| B5 | Top-citation ablation | Remove the passage the investigator ranks first (or cites first), re-run only the final LLM step. $s(f) = 1$ if $f$ disappears; $s(f,S) = 1$ for that passage's cluster. | $r$ LLM steps per finding |
| B6 | Influence by attention or similarity | (a) Attention share (raw, or AT2) on each cluster's tokens in the investigator prompt. (b) Cosine similarity between the finding statement and each cluster's evidence text. $s(f,S)$ is the normalised share, and $s(f) = \max_S s(f,S)$. | one forward pass (a); embeddings (b) |
| B7 | Cluster-level ContextCite | Surrogate fit on $M$ random cluster masks, for the **LLM step only**. | $M$ LLM steps per finding |
| B8 | Lineage only | Witness sets from deterministic why-provenance, ignoring the LLM step. $\kappa$ is the minimum hitting set. | CPU only |
| **H** | **Hybrid (proposed estimator)** | Lineage for deterministic stages, plus B7 proposals for the LLM step, plus real re-runs confirming the proposed singletons and pairs inside $\mathcal{N}_f$. | measured |
| **E** | **Exhaustive LOSO (reference)** | All singletons over $\mathcal{S}$, plus pairs within $\mathcal{N}_f$ for findings with $\mathrm{Ess} = \emptyset$, with $r_0 = 10$ and $r = 3$, adaptive to 5. | §5.7 |

---

## 5. Experimental design

### 5.1 Research questions [Hypotheses stated as testable claims]

- **RQ1, validity.** Does measured necessity (E) agree with generator-known logical necessity? *H1:* cluster-level
  E reaches AUROC ≥ 0.9 for essential $(f, S)$ pairs on MindDoc-Synth. Disagreements split into *unsupported
  persistence* (the finding survives removal of a logically necessary cluster) and *spurious dependence*.
- **RQ2, single-source detection.** Which method best flags $\kappa^\star_f = 1$? *H2:* B1 and B4 are weak, B2 is
  strong without copies but degrades with copy rate, and H matches E.
- **RQ3, copy invariance.** *H3:* as the injected copy rate rises from 0 to 80%, document-level LOSO increasingly
  calls single-origin findings robust, while cluster-level LOSO with oracle clusters stays flat. Estimated clusters
  fall in between.
- **RQ4, instability.** What share of apparent flips is within the noise floor? *H4:* without $r_0 > 1$, a material
  share of "essential" labels is noise.
- **RQ5, cost.** *H5:* H recovers E's $\mathrm{Ess}$ sets (Jaccard ≥ 0.9) and $\kappa \in \{1, 2, \ge 3\}$ with
  ≥ 10× fewer LLM calls.
- **RQ6, utility (later, §5.8).** Does showing fragility help reviewers catch weak findings faster without making them
  over-trust robust ones?

### 5.2 Datasets

- **MindDoc-Synth (primary; planned, not built).** Described in
  [EVALUATION_FRAMEWORK.md](../architecture/EVALUATION_FRAMEWORK.md) §4 and H. For this study the generator must also
  emit:
  1. for each planted finding, its **witness sets**: the minimal document sets from which the scheme's evidence
     template is satisfiable;
  2. the **derivation graph** of injected copies, exports, versions and derived documents, with a copy-rate knob;
  3. the **controlling party** of every document;
  4. for benign look-alikes, the **explaining documents**, which are the suppressor ground truth.

  Ground truth then follows: $\nu^\star_f(S) = 1$ iff $S$ intersects every witness, and $\kappa^\star_f$ is the minimum
  hitting set.

  **Caveat [Established]:** this is *logical* necessity under the generator's template. The pipeline may
  legitimately find another route the template did not anticipate. Every disagreement is inspected and labelled as
  either a template gap or a pipeline error before it is scored.
- **HotpotQA, distractor setting (sanity check).** Licence CC BY-SA 4.0, as stated on hotpotqa.github.io [verified].
  The answer plays the role of the finding and each paragraph is a cluster. Gold supporting facts mark the necessary
  paragraphs. Persistence after removing a gold paragraph measures answering from parametric memory, a known confound
  on a public, contaminated set. Share-alike applies to any redistributed derivative.
- **MultiHop-RAG (sanity check).** COLM 2024 [verified]. 2,556 queries over 609 news articles published
  26 Sep–26 Dec 2023. Non-null queries need 2–4 pieces of evidence, and 301 null queries have none [verified on the
  arXiv HTML]. Null queries test emergent findings and abstention. Licence: ODC-BY according to the GitHub README
  [verified]. ODC-BY covers the database. The README does not address copyright in the underlying news text, so keep
  the data internal and do not redistribute article text without checking.
- **Limit:** both public sets are single-stage RAG. They test the *measurement* (matching, noise floor, cluster
  removal), not the multi-stage claim, which only MindDoc-Synth can test.

### 5.3 What is measured

| Target | Metric |
|---|---|
| Essential $(f,S)$ pairs vs $\nu^\star$ | precision, recall, F1 of $\mathrm{Ess}$; AUROC and AUPRC of $\nu_f(S)$ and of each baseline's $s(f,S)$ |
| $\kappa$ | exact agreement on the bins $\{1, 2, \ge 3\}$; Kendall $\tau_b$ between estimated and true $\kappa$; share of stored $\kappa$ values that are only upper bounds |
| Single-source findings | AUROC and AUPRC of $s(f)$ for $\kappa^\star = 1$; recall at a fixed review budget (top-$k$ by fragility × amount) |
| Failure modes | unsupported-persistence rate; hidden-dependence recall; suppressor precision and recall vs explaining documents |
| Copy invariance | gap $\lvert\kappa(\text{copy rate } x) - \kappa(0)\rvert$ by granularity and clustering method |
| Instability | distribution of $h_f(\emptyset)$; share of findings excluded as unstable; flips not significant under §5.5 |
| Matcher | precision and recall of cross-run finding matching against generator identities |
| Cost | LLM calls, tokens and wall-clock per finding; fidelity of H vs E plotted against calls |

### 5.4 Ground-truth checks on the instrument itself

Before the main runs:

1. Run E twice with different seeds. Report test–retest agreement of $\mathrm{Ess}$ sets. This is the ceiling any
   estimator can reach.
2. Audit the matcher on 100 generator-labelled finding pairs.
3. Confirm that deterministic stages give identical output hashes across runs, so $r = 1$ is justified there.

### 5.5 Statistical analysis and sample size

- **Unit and dependence.** Findings are nested within cases, so every CI is a **cluster bootstrap over cases**
  (resample cases, $B = 2000$). Comparisons between methods on the same findings use the paired cluster bootstrap.
  Paired binary decisions (the $\kappa = 1$ flag) use McNemar's test. Holm correction is applied across baselines.
  Metrics, seeds and splits are pre-registered (RESEARCH_GAPS §8).
- **Flip significance with few runs (one-sided Fisher exact test).**
  - With $r_0 = r = 3$, only $3/3 \to 0/3$ reaches $p = 1/\binom{6}{3} = 0.05$.
  - With an asymmetric design, $r_0 = 10$ and $r = 3$: $10/10 \to 0/3$ gives $p = 1/\binom{13}{3} \approx 0.0035$, and
    $10/10 \to 1/3$ gives $p = 11/286 \approx 0.038$. But $10/10 \to 2/3$ gives $p = 66/286 \approx 0.23$, which is
    not significant.

  Baseline runs are paid once per case and removal runs once per cluster, so **$r_0 = 10$, $r = 3$ (adaptive to 5)**
  is the default.
- **Sample size for estimating a proportion** (e.g. the recall of essential-pair detection) to a half-width $w$ at
  95%:
  $$n = \frac{z_{0.975}^2\,p(1-p)}{w^2}\cdot \mathrm{DE},\qquad \mathrm{DE} = 1 + (\bar{m} - 1)\,\mathrm{ICC},$$
  where $\bar{m}$ is the number of units per case. *Illustration with assumed inputs:* $p = 0.5$, $w = 0.05$,
  $\bar{m} = 8$, ICC $= 0.1$ gives $385 \times 1.7 \approx 654$ units, or about 82 cases at 8 findings per case.
- **Sample size for a paired comparison** (H vs the best baseline on the $\kappa = 1$ flag), by the normal
  approximation to McNemar's test, with discordance probability $\psi$ and accuracy difference $\delta$:
  $$n = \frac{\big(z_{1-\alpha/2}\sqrt{\psi} + z_{1-\beta}\sqrt{\psi - \delta^2}\big)^2}{\delta^2}.$$
  *Illustration:* $\psi = 0.25$, $\delta = 0.10$, $\alpha = 0.05$, power 0.8 gives $n \approx 194$ findings, or about
  330 after the design effect.
- **The inputs $p$, $\bar m$, ICC and $\psi$ are assumptions.** A 10-case pilot measures them, and the test-split size
  is fixed from the pilot before the test split is touched. Synthetic cases are cheap to generate, so the binding
  constraint is re-run cost (§5.7), not data.

### 5.6 Ablations

- Removal unit: document vs copy cluster vs control group.
- Oracle clusters vs estimated clusters (MinHash only; + explicit references; + the shared-deviation copy signal).
- $r_0 \in \{3, 10\}$, $r \in \{1, 3, 5\}$, adaptive vs fixed.
- Thresholds $\eta$ and $\tau_\mu$; binary vs graded persistence.
- Restricted ($\mathcal{N}_f$) vs full LOSO, which measures the missed indirect and emergent effects.
- Incremental vs full entity-resolution recomputation.
- Temperature 0 vs sampling; prompt-order randomisation on vs off; verifier on vs off.
- Perturbation type: remove vs replace (an amount altered) vs duplicate (adding a copy must not change cluster-level
  $\kappa$).
- **Diagnosticity extension:** run LOSO for the benign look-alike hypothesis too. An evidence cluster that is
  essential to both the scheme finding and its benign explanation is necessary but not diagnostic (§3.7).

### 5.7 Compute budget (formula, not a number)

For $N$ cases, the exhaustive reference costs

$$N^{\mathrm{E}}_{\mathrm{LLM}} = \sum_{c=1}^{N}\Big[r_0 L_c + \bar r \sum_{f \in F^\star_c}\big(m_f + P_f\big) L_f\Big],$$

where $P_f$ is the number of pair sets tested for $f$ and $\bar r$ is the realised mean number of adaptive repeats.

- Tokens are $N_{\mathrm{LLM}} \cdot (\bar t_{\mathrm{in}} + \bar t_{\mathrm{out}})$, and money is
  $N_{\mathrm{LLM}} (\bar t_{\mathrm{in}} p_{\mathrm{in}} + \bar t_{\mathrm{out}} p_{\mathrm{out}})$ at the pinned
  model's prices.
- Deterministic CPU cost is $\sum_c (1 + m_c + P_c)\,\bar c^{\mathrm{inc}}_{\mathrm{det},c}$.
- Baselines add $4\bar r\sum_f L_f$ (B3), $\bar r\sum_f L_f$ (B5) and $\sum_f M_f L_f$ (B7). B1, B2, B4, B6 and B8
  are essentially free.
- H's cost is measured, and RQ5 reports it as the ratio $N^{\mathrm{H}}_{\mathrm{LLM}} / N^{\mathrm{E}}_{\mathrm{LLM}}$.
- $L_f$, $m_f$, $P_f$ and $\bar t$ come from the pilot. The budget is then fixed and recorded in the run config
  before the full run.

### 5.8 Reviewer study (later; not part of the first paper)

Design: within-subject, with forensic reviewers from design-partner firms and synthetic cases containing planted
single-source, hidden-dependence and *robust-but-false* findings. Each reviewer sees the fragility panel on some
cases and not on others.

Measures:

- time to disposition per finding;
- planted weak findings caught;
- over-trust rate (robust-but-false findings accepted).

Dhami et al. (2019) found that a structured technique can increase inconsistency, so the study must be able to show
that the panel hurts.

---

## 6. Threats to validity and limitations

| Threat | Effect on the score | Mitigation |
|---|---|---|
| **Correlated sources the clustering missed** (a statement and a ledger keyed from it with no explicit reference; two invoices from one forger) | $\kappa$ is overstated: the finding looks corroborated when it is not | copy signal from shared deviations; control-group ablation; report $\kappa$ at both granularities; RQ3 measures the size of this error |
| **Over-merged clusters** (unrelated documents joined by template similarity) | $\kappa$ is understated: false "single-source" alarms | cluster membership stores the reason per edge; reviewers can split a cluster; precision of $\hat{\mathcal S}$ is measured on Synth |
| **Adversarial duplication** (a borrower submits the same fabricated evidence in several forms to look corroborated) | defeats count-based baselines, and document-level LOSO | cluster-level removal is invariant to exact and near copies by construction; *derived* copies with altered wording remain a gap |
| **Pipeline non-determinism** (API models, retrieval ties, thread order) | spurious flips; unstable references | $r_0 = 10$; exact-test flips; "unstable" findings excluded and shown as such; deterministic stages verified by hashes |
| **Finding-matching errors** (a split or merged finding across runs; changed amount read as a new finding) | false flips, or missed flips | identity excludes magnitude; one-to-one matching; matcher audited against generator identities; $\tau_\mu$ sensitivity reported |
| **Removal ≠ discrediting.** Deleting a document is not the same as the document being shown false: a real challenge may *replace* a value, not remove it | LOSO answers "without this source" only | replace and corrupt perturbations as an ablation; UI wording says "without", never "if false" |
| **Extraction vs source failure** | a cluster may be "essential" only because one OCR'd page carries a mis-read amount | essential clusters link to their regions, so the reviewer checks the pixels; KBT-style separation is future work |
| **Synthetic-to-real gap** | witness structure on Synth may be cleaner than real cases | public sanity sets; a real closed-case pilot with a design partner before any product claim |
| **Goodhart effects** | if fragility becomes a target, the agent may pad findings with redundant citations, or avoid single-source findings that are true | measured necessity, not citation count, is the score, so padding does not help; single-source findings are shown, not suppressed; do not optimise the investigator against LOSO without a held-out check |
| **Combinatorial limits** | exact $\kappa$ is unknown beyond pairs for many findings | store `bound_type`; never show an upper bound as exact |
| **Robustness is not truth** | a robust finding can be false (shared error, wrong entity merge applied consistently), and a fragile one can be true | the score is labelled "evidential basis", shown next to verification status, never merged into a probability of fraud |

**Explicit statement [Established by definition].** LOSO fragility measures how a finding's presence in *our
pipeline's output* depends on *the sources we hold*. It does not establish that the event happened, that the
documents are authentic, or that the conclusion would survive other evidence we do not hold.

---

## 7. How it maps onto MindDoc

### 7.1 What must exist first (prerequisites)

At commit `ee814b0` none of these exist. The v2 schema has `documents.content_hash`, chunks, entities and entity
relations (mostly `co_occurs`). The answer-sentence claim verifier (`app/ai/verifier.py`) checks consistency, not dependence.

| # | Prerequisite | Why LOSO needs it | Where it is specified |
|---|---|---|---|
| P1 | Claims with evidence regions (`claim` versions, `finding_support.claim_version_id`) | lineage from finding to region; $\mathrm{cite}(f)$ | F §3–§4; DATA_MODEL §6 |
| P2 | Findings with a canonical `finding_key` built from strong identifiers | cross-run matching (§2.4) | F §4 |
| P3 | `source_cluster` with `kind` and per-member reason | removal unit (§2.3) | F §6 |
| P4 | A deterministic, re-runnable pipeline: pinned versions, seeds, per-step input hashes and a step cache keyed by `(step, input_hash)` | incremental re-runs (§2.9) | INVESTIGATION_ENGINE §2; ADR-0007 |
| P5 | Corpus views with exclusions: run a case over $D_{-T}$ *without deleting anything*, via an `excluded_cluster_ids` scope on the run | removal without data loss; audit trail | new; uses `case_source` (F) |
| P6 | Deterministic detectors D1–D7 with why-provenance output | witness sets for B8 and H | INVESTIGATION_ENGINE §5 |
| P7 | MindDoc-Synth with witness sets, derivation graph, controlling parties and explaining documents | ground truth (§5.2) | EVALUATION_FRAMEWORK §4; H (benchmark LB) |

Minimum viable order: P1 → P2 → P3 (versions and near-duplicates first; derived-from later) → P4 + P5 → exhaustive
LOSO on deterministic findings only → add the LLM step → H. Exhaustive LOSO with no LLM step is already useful: it
needs P1–P5 only and is exact with $r = 1$.

### 7.2 Storage (aligned with F §4 and §6)

`finding_robustness` (F §4) is used as reserved. Column semantics:

| Column | Meaning here |
|---|---|
| `finding_id` | the finding version assessed (findings are versioned in F, so a new evidence snapshot means a new robustness row) |
| `run_id` | the robustness run: the set of pipeline runs ($r_0$ baseline plus removal runs) that produced this row |
| `method` | `loso_cluster` (E, exhaustive). Proposed additional enum values: `loso_hybrid` (H) and `loso_document` (ablation only, never shown to reviewers) |
| `n_clusters` | number of clusters actually tested: $\lvert\mathcal{S}\rvert$ for full LOSO, $\lvert\mathcal{N}_f\rvert$ for restricted |
| `essential_cluster_ids[]` | $\mathrm{Ess}(f)$ |
| `k_fragility` | $\kappa_f$, null if not computed. Its bound type goes in `details` |
| `persisted_fraction` | **proposed definition:** share of tested single-cluster removals under which $f$ still holds, $\lvert\{S: h_f(\{S\}) \ge \eta\}\rvert / n_{\text{clusters}}$ |
| `details jsonb` | `granularity`, `loso_score`, `baseline_persistence` $h_f(\emptyset)$, `r0`, `r`, `eta`, `tau_mu`, per-cluster `{nu, nu_graded, rho, h, runs}`, `redundant_cluster_ids`, `decorative_cluster_ids`, `hidden_dependence_cluster_ids`, `emergent_findings` (suppressor → finding key), `k_bound_type` ∈ {exact, upper, lower}, `killing_set`, `matching_fn_version`, `llm_calls`, `tokens` |
| `pipeline_version`, `computed_at` | as in F |

Two supporting records are needed, unless G's job and agent-step design already covers them:

- `pipeline_run(id, case_id, robustness_run_id?, pipeline_version, corpus_snapshot_hash, excluded_cluster_ids[],
  seed, run_index, status, llm_calls, tokens)`;
- `pipeline_run_finding(pipeline_run_id, finding_key, matched_finding_id?, match_score, magnitude)`.

Re-runs write findings **only** to these run tables, never to `finding`. A removal run is hypothetical, like the
scenario branches in INVESTIGATION_ENGINE §4.

### 7.3 What the reviewer sees

- **Badge per finding:** "Rests on **1** independent source: Bank X statement, Mar 2025 (2 files, 1 origin)" /
  "Survives removal of any single source (k ≥ 2)" / "Unstable: appeared in 6 of 10 identical runs".
- **Detail panel:** per-cluster bars for $\nu$ and $\rho$, marked *cited & needed* / *cited, not needed* /
  *needed, not cited* (hidden dependence: add to the report annex) / *removing this creates another finding*
  (suppressor: check its authenticity). Each cluster opens its regions in ≤ 2 clicks (DATA_MODEL §8).
- **Review queue:** sort by fragility × amount. Single-source, high-amount findings come first, with an action to
  request a corroborating document (the hook for Direction D).
- **Fixed caveat text:** "Robustness describes the evidence we hold, not whether the finding is true."
- **Report:** the evidence annex lists essential and hidden-dependence clusters for every finding, so the material
  relied upon is complete.

---

## 8. Publishability and kill criteria

### 8.1 Venue and the result that would make it publishable

- **Realistic:** a workshop paper (RAG and grounding, trustworthy NLP, or data-quality workshops; GroundLM at EMNLP
  2026 is an example of the venue type that took EviScope).
- **Stretch:** a short or Findings paper (ACL/EMNLP Findings, SIGIR/CIKM short), if all of the following hold:
  1. cluster-level LOSO beats document-level LOSO and count baselines at flagging $\kappa^\star = 1$, with the gap
     growing with copy rate (RQ2, RQ3);
  2. H reproduces exhaustive LOSO (Ess Jaccard ≥ 0.9, $\kappa$-bin agreement ≥ 0.9) at ≥ 10× fewer LLM calls
     (RQ5);
  3. unsupported persistence and hidden dependence are shown to be frequent enough to matter in a multi-stage
     pipeline;
  4. results are not synthetic only: at least one public set, plus a closed real case or a described pilot.
- **Contribution claim (narrow, honest):** a definition of finding-level, cluster-based deletion fragility for
  multi-stage evidence pipelines; an estimator mixing exact lineage with a localized surrogate; and its validation
  against exhaustive re-runs. Not "LOO for RAG", which CUE-R, Saha Roy et al. and AttriBoT already cover.

### 8.2 Kill criteria (stop or pivot if any holds)

| ID | Condition | Action |
|---|---|---|
| K1 | A paper already computes minimal source-deletion sets for multi-stage agent or KG findings and validates them against re-runs (re-check the four 2026 provenance papers in §3.6 in full text, and search again) | drop the research claim; keep LOSO as a product feature |
| K2 | E's own test–retest agreement on Ess sets is below 0.8 after $r_0 = 10$ | the instrument is too noisy; fix determinism first or abandon |
| K3 | B2 (independent cluster count) matches E within the CI on RQ2 *and* RQ3 | re-runs add nothing over counting clusters; ship B2 and stop the research |
| K4 | H needs ≥ 50% of E's LLM calls to reach the fidelity targets | no estimator contribution; at most a workshop measurement note |
| K5 | Real-case pilot: reviewers judge flagged single-source findings uninformative (they already knew), or the user study shows more over-trust | stop the UI work; keep the score as an internal QA metric |
| K6 | Prerequisites P1–P5 slip past the R8 window in J_ROADMAP | defer; do not build a parallel lineage system just for the paper |

---

## References ([verified] this session unless marked otherwise)

**Leave-one-out, influence, dropping data**
- Efron, B., Stein, C. (1981). The jackknife estimate of variance. *Ann. Statist.* 9(3). doi:10.1214/aos/1176345462 — https://portal.mardi4nfdi.de/wiki/Publication:1162320
- Koh, P. W., Liang, P. (2017). Understanding Black-box Predictions via Influence Functions. ICML. https://arxiv.org/abs/1703.04730
- Broderick, T., Giordano, R., Meager, R. An Automatic Finite-Sample Robustness Metric: When Can Dropping a Little Data Make a Big Difference? https://arxiv.org/abs/2011.14999
- Ghorbani, A., Zou, J. (2019). Data Shapley. ICML, PMLR 97:2242–2251. https://proceedings.mlr.press/v97/ghorbani19c.html

**Causality and provenance**
- Chockler, H., Halpern, J. Y. (2004). Responsibility and Blame: A Structural-Model Approach. *JAIR* 22:93–115. https://jair.org/index.php/jair/article/view/10386 · https://arxiv.org/abs/cs/0312038
- Meliou, A., Gatterbauer, W., Moore, K. F., Suciu, D. (2011). The Complexity of Causality and Responsibility for Query Answers and non-Answers. PVLDB. https://arxiv.org/abs/1009.2021
- Green, T. J., Karvounarakis, G., Tannen, V. (2007). Provenance semirings. PODS, 31–40. doi:10.1145/1265530.1265535 — https://bibtex.github.io/PODS-2007-GreenKT.html

**Context attribution**
- Cohen-Wang, B., Shah, H., Georgiev, K., Mądry, A. (2024). ContextCite. NeurIPS. https://arxiv.org/abs/2409.00729 · https://proceedings.neurips.cc/paper_files/paper/2024/hash/adbea136219b64db96a9941e4249a857-Abstract-Conference.html
- Cohen-Wang, B., Chuang, Y.-S., Madry, A. (2025). Learning to Attribute with Attention (AT2). https://arxiv.org/abs/2504.13752
- Liu, F., Kandpal, N., Raffel, C. (2025). AttriBoT. ICLR. https://arxiv.org/abs/2411.15102
- Wang, Y., Zou, W., Geng, R., Jia, J. (2025). TracLLM. USENIX Security. https://arxiv.org/abs/2506.04202
- Nematov, I., et al. (2025). Source Attribution in Retrieval-Augmented Generation. https://arxiv.org/abs/2507.04480
- Saha Roy, R., Schlotthauer, J., Hinze, C., Foltyn, A., Hahn, L., Kuech, F. (2025). Evidence Contextualization and Counterfactual Attribution for Conversational QA over Heterogeneous Data with RAG Systems. WSDM. https://arxiv.org/abs/2412.10571
- Rorseth, J., Godfrey, P., Golab, L., Srivastava, D., Szlichta, J. (2026). RUBEN: Rule-Based Explanations for Retrieval-Augmented LLM Systems. ICDE demo. https://arxiv.org/abs/2605.10862

**Counterfactual robustness and sufficiency**
- Jain, S., Vedam, V. N. (2026). CUE-R: Beyond the Final Answer in Retrieval-Augmented Generation. https://arxiv.org/abs/2604.05467
- Deswal, S. S. (2026). EviScope. GroundLM workshop, EMNLP. https://arxiv.org/abs/2609.17081
- Xiang, C., Wu, T., Zhong, Z., Wagner, D., Chen, D., Mittal, P. Certifiably Robust RAG against Retrieval Corruption. https://arxiv.org/abs/2405.15556
- Joren, H., et al. (2025). Sufficient Context. ICLR. https://arxiv.org/abs/2411.06037
- Atanasova, P., Simonsen, J. G., Lioma, C., Augenstein, I. (2022). Fact Checking with Insufficient Evidence. *TACL* 10:746–763. https://aclanthology.org/2022.tacl-1.43
- DeYoung, J., et al. (2020). ERASER. ACL, 4443–4458. https://aclanthology.org/2020.acl-main.408/
- Wallat, J., Heuss, M., de Rijke, M., Anand, A. Correctness is not Faithfulness in RAG Attributions. https://arxiv.org/abs/2412.18004

**Source dependence and trust**
- Dong, X. L., Berti-Equille, L., Srivastava, D. (2009). Integrating Conflicting Data: The Role of Source Dependence. VLDB / PVLDB 2(1). https://lunadong.com/publication/dependence_vldb.pdf
- Dong, X. L., et al. (2015). Knowledge-Based Trust. PVLDB 8(9). https://arxiv.org/abs/1502.03519
- Zhou, R., et al. (2026). Evidence Laundering: Deep Research Agents Mistake Correlated Sources for Independent Evidence. EMNLP, 11682–11693. https://aclanthology.org/2026.emnlp-main.509/

**Agent provenance (2026 preprints)**
- Wang, Y., et al. From Agent Traces to Trust (survey). https://arxiv.org/abs/2606.04990
- Liao, J., et al. Auditing Provenance Sensitivity in LLM Agent Action Selection. https://arxiv.org/abs/2607.20827
- Yun, T., et al. Correct Answers, Unsupported Findings. https://arxiv.org/abs/2610.09581
- Lu, M., Huang, Y., Lin, C., Lee, S.-I. Agents that Matter. https://arxiv.org/abs/2605.27621

**Instability**
- Wang, X., et al. (2023). Self-Consistency Improves Chain of Thought Reasoning in Language Models. ICLR. https://arxiv.org/abs/2203.11171
- Atil, B., et al. Non-Determinism of "Deterministic" LLM Settings. https://arxiv.org/abs/2408.04667
- Liu, N. F., et al. Lost in the Middle. TACL. https://arxiv.org/abs/2307.03172
- Jain, S., Wallace, B. C. (2019). Attention is not Explanation. NAACL. https://arxiv.org/abs/1902.10186

**Intelligence and forensic practice**
- Heuer, R. J. (1999). *Psychology of Intelligence Analysis*, ch. 8. CIA Center for the Study of Intelligence. https://www.cia.gov/resources/csi/static/Pyschology-of-Intelligence-Analysis.pdf
- Dhami, M. K., Belton, I. K., Mandel, D. R. (2019). The "analysis of competing hypotheses" in intelligence analysis. *Appl. Cogn. Psychol.* 33(6):1080–1090. https://strathprints.strath.ac.uk/69049/
- Bell, A., Wong, J. (2024). Critiquing another expert's report. Grant Thornton Australia (practitioner blog). https://www.grantthornton.com.au/insights/blogs/critiquing-another-experts-report/

**Datasets**
- Yang, Z., et al. (2018). HotpotQA. EMNLP. Licence CC BY-SA 4.0. https://hotpotqa.github.io/
- Tang, Y., Yang, Y. (2024). MultiHop-RAG. COLM. Licence ODC-BY (README). https://arxiv.org/abs/2401.15391 · https://github.com/yixuantt/MultiHop-RAG

**Legal (secondary reports)**
- *State Bank of India v. Amit Iron Pvt. Ltd.*, 2026 INSC 323 — report: https://www.verdictum.in/amp/court-updates/supreme-court/state-bank-of-india-v-amit-iron-private-limited-2026-insc-323-furnish-full-forensic-audit-report-1611556
- *State Bank of India v. Rajesh Agarwal* (27 Mar 2023) — judgment link as listed in `docs/strategy/MARKET_SELECTION.md` [S5]; not re-opened this session.
