# MindDoc AI: Industry Landscape for Evidence Intelligence

*Research date: 2026-11-10. Audience: the MindDoc owner (student / independent engineer). Goal: pull engineering principles out of how leading platforms build multimodal ingestion, grounded evidence models, knowledge graphs, retrieval, and governed agents, and skip the marketing.*

Companion document: [TECHNOLOGY_EVALUATION.md](./TECHNOLOGY_EVALUATION.md) (per-technology verdicts, licenses, CPU feasibility, benchmarks).

---

## 0. How to read this

**Verification legend** (applied per claim or per row):

| Tag | Meaning |
|---|---|
| **[V]** | Verified on a primary page (official docs, repository README, paper) fetched during this research. |
| **[P]** | Primary source, but seen only as an official-page search excerpt or a partial fetch. The wording is the vendor's, but surrounding detail may be missing. |
| **[S]** | Secondary source (third-party blog, aggregator, partner page). |
| **[K]** | Author's prior knowledge, not re-checked in this session. Check it before relying on it. |
| **[U]** | Could not be verified. |

- **Vendor-reported numbers** are labelled as such. None were reproduced independently.
- **Established practice** means multiple independent implementations exist and the semantics are documented. **Speculative** means a plausible idea that has no evidence at MindDoc's scale yet. Section 9 keeps the two apart.
- **Research limit:** the web-search quota ran out near the end of this research. A small number of items could not be re-checked and are tagged [K] or [U] rather than guessed.

**MindDoc today** (from `docs/ARCHITECTURE.md`): FastAPI, SQLite, an in-memory NumPy vector index, sentence-transformers (MiniLM plus a cross-encoder), OpenCV/EasyOCR/PyMuPDF, a GraphRAG-lite knowledge graph, guardrails, an LLM gateway, and React.

---

## 1. TL;DR: the principles worth copying

1. **The typed, governed object model is the product. The graph picture is just one view of it.** Palantir's Ontology combines object types, link types, action types, functions and interfaces. It is bound to data and to permissions, and it is the only API that apps and agents use. (§2)
2. **Every write goes through a named, validated, audited action. AI proposes, and a person or a rule commits.** The same pattern shows up in Palantir action types with submission criteria, AIP Logic staged or reviewed edits, Chatbot Studio action tools with confirmation, OpenAI `needs_approval`, and ADK action confirmations. (§2, §5, §6)
3. **Grounding is offsets plus geometry plus version.** Azure Document Intelligence gives every paragraph, table cell and figure character spans into one canonical `content` string plus bounding polygons. Claude Citations returns char, page and content-block locations. In MindDoc, every claim should resolve to `(document, page, polygon, char span, extractor@version)`. (§4.4, §7.4)
4. **Use deterministic workflows for ingestion and save agents for open-ended investigation.** Sources: Anthropic's "workflows vs agents" essay, ADK's deterministic workflow agents, and Palantir's deployment of extraction strategies as batch transforms. (§7.1, §6.1, §2.8)
5. **Choose an extraction strategy per document class by measuring quality, speed and cost on your own sample.** Palantir Document Intelligence is built around exactly this comparison. NVIDIA and Docling both chain specialised detectors (page elements, table structure, OCR) rather than relying on one model. (§2.8, §3.1, §8.5)
6. **Use hybrid retrieval with contextualised chunks and a reranker, and measure it on your own queries.** Anthropic reports 35%, 49% and 67% fewer retrieval failures for the successive steps (vendor-reported). (§7.2)
7. **LLM-built graph summaries are expensive.** Defer LLM work to query time unless the corpus is small and stable. Microsoft's GraphRAG README warns that indexing "can be an expensive operation". LazyGraphRAG reports indexing at 0.1% of full GraphRAG's cost (vendor-reported). (§4)
8. **Time is a first-class dimension.** Separate "when it was true in the world" from "when the system learned it", and invalidate superseded facts instead of deleting them, as Zep/Graphiti does. (§8.4)
9. **Entity resolution comes before link analysis.** Quantexa's whole product is ER followed by network generation. A graph built from unresolved mentions produces misleading centrality and community results. (§8.1)
10. **Security labels travel with the data and constrain AI exactly as they constrain users.** Palantir Markings propagate to derived resources, and AIP rejects model requests that carry disallowed markings. (§2.3)
11. **Evals are a build artifact, not an afterthought.** Examples: AIP Evals suites, ADK `adk eval` criteria, and OpenAI trace grading. (§2.7, §6.1, §5.3)
12. **Make long-running state explicit, persisted and resumable, and remember that approval is not exactly-once.** OpenAI's HITL docs say this directly and recommend idempotency keys. LangGraph and Temporal persist checkpoints and history. (§5.1, §8.6)

---

## 2. Palantir Foundry / AIP

### 2.1 Ontology primitives

| Primitive | What Palantir's docs say (paraphrased) | Ver. | MindDoc analogue |
|---|---|---|---|
| **Object type** | Schema definition of a real-world entity or event. An object is one instance. | [V] | `Document`, `Page`, `Region`, `Claim`, `Entity`, `Event`, `Investigation`, `Finding` |
| **Property / shared property** | A characteristic of an object type. A shared property is reused across object types so its metadata is managed centrally. | [V] | Shared `confidence`, `source_span`, `valid_from/valid_to`, `marking` |
| **Link type** | Schema of a relationship between two object types. A link is one instance. | [V] | `Region-contains->Claim`, `Claim-mentions->Entity`, `Claim-supports/contradicts->Claim` |
| **Action type** | Schema for a set of changes to objects, property values and links applied at once, including side effects on submission. | [V] | `ApproveFinding`, `MergeEntities`, `RejectClaim`, `AttachEvidence` |
| **Function** | Code-based logic with inputs and an output. Ontology-integrated functions take objects or object sets and can be used in actions and apps. | [V] | Python functions such as `contradiction_score(claim_a, claim_b)` |
| **Interface** | Describes the shape and capabilities of an object type. Object types can implement several interfaces. | [V] | `Grounded` (page + polygon + span), `Temporal` (valid/recorded times), `Marked` |
| **Object set** | A collection of object instances. | [V] | Saved queries and investigation working sets |

- **Digital twin framing.** The docs call the Ontology "the digital twin of an organization" [V].
- **Interface limits.** The docs flag that interface link types and aggregations are "not yet supported in any language" and that interface action support is still expanding [P]. So the abstraction is still maturing even at Palantir.

### 2.2 Writeback through actions (the "kinetic" layer)

- **Submission criteria** are conditions over parameters and user properties, combined with operators. An action can be submitted only if all criteria pass. Criteria are separate from edit permissions [P].
- **Rule order matters.** Multi-rule actions compile into one edit per object [P].
- **Webhooks: writeback vs side effect.**
  - A webhook can be configured as a **writeback**, whose output parameters feed later rules.
  - Or it can be a **side effect**, which runs after rules are evaluated. The user may see "success" before side-effect webhooks finish, and multiple side-effect webhooks run in no guaranteed order.
  - Side effects are not triggered when submission criteria fail [P].
- **Test runs** enforce the same security and criteria as live submissions and preview side effects [P].
- **Branches.** An October 2025 announcement added a toggle to allow webhook execution on branches [P].

**Engineering lesson (established).** An action is four things at once:
1. a transaction boundary,
2. validation,
3. a permission check,
4. an audit record.

External effects are explicitly **not atomic** with the edit. MindDoc should model approvals the same way: commit the edit and an outbox row in one DB transaction, then run notifications or exports asynchronously.

### 2.3 Security: markings, roles, purpose, checkpoints

- **Markings vs roles.** Markings are Foundry's implementation of *mandatory* access control, while project roles are *discretionary*. Derived resources inherit markings unless they are explicitly removed [P].
- **Classification-based access controls** are not on by default and need Palantir involvement to configure [P].
- **Purpose limitation.** Define permitted purposes before granting access, and reassess access when the purpose ends or changes [P].
- **Checkpoints** make users justify configured interactions and keep the records for review [P].
- **AIP and markings.** Enrollment admins set an allowlist of mandatory markings that models may receive. The check looks at every mandatory marking on the request token, not only those on the data in the request. AIP "rejects the request if the token includes any mandatory Marking outside the allowlist", and this applies to interactive and automated workflows alike [V].

**Lesson.** Store markings as data, propagate them along lineage (derived claims inherit the strictest source marking), and enforce them on *every* read path. The LLM context builder is a read path too.

### 2.4 Lineage

- Marking inheritance by derived resources [P] is lineage used for security.
- For Document Intelligence, deployed Python transforms "produce the same results as the corresponding configuration" in the app [P]: the experiment and the production pipeline run the same config.
- The Data Lineage application itself was not researched in detail [U].

**Lesson.** Persist `extractor@version + config_hash` on every derived row. Without that, there is no lineage.

### 2.5 AIP Logic

- **What it is.** A no-code environment for building, testing and releasing LLM-powered functions out of blocks. The "Use LLM" block is a prompt, tools and an output. Tools include "Apply actions" (the LLM edits the Ontology through Actions) and "Call function" [P].
- **Proposals, not writes.** In the debugger, proposed edits appear but are **not executed**. Automate can apply them or **stage them for human review** [P].
- **Staged writes.** Edits are held in temporary storage and applied when execution completes [P].

**Lesson.** LLM output is an *edit proposal* that passes through validation, then approval, then commit. Never let the model write directly.

### 2.6 AIP Chatbot Studio (formerly AIP Agent Studio)

- **Renamed.** AIP Chatbot Studio was "previously known as AIP Agent Studio" [P].
- **Tool types** include:
  - Action tools, which run automatically or after user confirmation,
  - Command tools,
  - a Request-clarification tool that lets the agent pause and ask,
  - Ontology semantic search [P].
- **Ontology MCP** exposes object types, action types and query functions as MCP tools [P].

**Lesson.** Agent tools are thin wrappers over the same governed actions and queries humans use, with a confirmation flag per tool.

### 2.7 AIP Evals

- An evaluation suite is a collection of evaluation functions and test cases used to benchmark AIP Logic functions.
- Suites can be generated automatically ("Generate evals"), can target several functions, and use built-in or custom evaluators. Results show on a metrics dashboard.
- Manually created suites output the function's return value but provide **no aggregated metrics** [P].

### 2.8 AIP Document Intelligence

- **What it does.** Open a media set, run several **extraction strategies**, and compare them on **quality, speed and token cost** [P].
- **Two strategy families** [P]:
  - *Traditional*: raw text for electronically generated PDFs, plus OCR and layout detection (per the machine-translated Japanese page).
  - *Generative*: a VLM with a custom prompt. Optional preprocessing runs OCR first and passes the OCR output plus the page image to the VLM.
- **Evals.** Extraction is LLM-graded. The docs note that extraction evaluations need Claude 4 Sonnet to be available in the enrollment [P].
- **Deployment.**
  - As a Python transform that batches over a media set. Palantir advises against editing prompts inside the generated template, because batch results could then diverge from what the app showed.
  - Or as Python functions that process one page at a time, with optional chunking and embedding helpers [P].

**Lesson (established).** An extraction strategy is a **versioned, evaluated, per-document-class configuration**, not a hard-coded pipeline. "OCR first, then VLM with OCR text as context" is a documented hybrid.

### 2.9 Why the Ontology is more than a graph visualization

A graph visualization shows nodes and edges. The Ontology is an **operational contract** with five properties a picture lacks:

1. **Typed schema with semantics.** It has object types, properties and interfaces, so code can reason about shape (`Grounded`, `Temporal`) rather than inspecting free-form node labels.
2. **Bound to sources.** Datasets and models map onto object types, properties and links ("integrates an organization's datasets and models", per the core-concepts page [V]). The graph is derived from data and never hand-maintained.
3. **Kinetic.** Action types are the write path. They carry submission criteria, permissions, side-effect semantics and test runs (§2.2), so decisions get *written back*.
4. **Uniform security for humans and AI.** Markings and roles apply whether a person or an LLM is reading (§2.3).
5. **One API for apps, functions, agents and MCP.** The same object, action and function surface is exposed to Logic, Chatbot Studio and MCP (§2.5 and §2.6). Agents therefore inherit governance instead of re-implementing it.

**For MindDoc**, the knowledge-graph page should be one consumer of an evidence ontology. That ontology should have typed objects, interfaces, governed actions, an audit log and markings. It should not *be* the ontology.

---

## 3. NVIDIA

### 3.1 NeMo Retriever Library (formerly NeMo Retriever extraction / NV-Ingest)

- **Naming.** The current docs call it **"NeMo Retriever Library"** (repo `NVIDIA/NeMo-Retriever`) [V]. Older docs (25.x) say NeMo Retriever extraction is "also known as NVIDIA Ingest and nv-ingest", with code at `github.com/nvidia/nv-ingest` [P]. *Changed recently: renamed and moved during 2026 (26.x docs).*
- **What it extracts.** It classifies and extracts text, tables, charts and infographics from PDF, Office, HTML, images, audio and video (some early access). Output is DataFrame-shaped rows [V].
- **Pipeline (worth copying even without NVIDIA hardware)** [V]:
  - a **Page Elements** detector for layout and chart/infographic detection,
  - a **Table Structure** model,
  - a **Graphic Elements** model,
  - pdfium text extraction by default, with hybrid, OCR and Nemotron Parse methods available,
  - Nemotron OCR v2 for local runs,
  - optional VLM captioning.
- **Table-structure model.** YOLOX-based and meant to work alongside OCR. NVIDIA warns it "does not always guarantee to retrieve the correct table structure" on uncommon styles or poor images [P].
- **Hardware** [P]:
  - GPU is **required** for local inference with HF models or NIMs, and **not required** for build.nvidia.com hosted inference.
  - The core pipeline fits on a single A10G-class GPU (about 4.8 GiB).
  - The 26.5 docs recommend at least 256 GB RAM and 32 CPU cores for production.
  - VLM captioning at BF16 needs at least 80 GB GPU memory.
  - Python 3.12+.

### 3.2 Embedding and reranking NIMs

- **Models.** Current examples include `llama-nemotron-embed-1b-v2`, `llama-nemotron-rerank-1b-v2`, and VL (vision-language) variants for multimodal retrieval [P].
- **License.** NVIDIA's pages cite the **NVIDIA Open Model License** with the **Llama 3.2 Community License** as additional terms, and call the models ready for commercial use [P]. One third-party page claims a different license (OpenMDW-1.1) for the rerank HF weights [S]. **Verify the model card before use.**

### 3.3 Enterprise RAG blueprint

- The blueprint previously titled "Multimodal PDF Data Extraction for Enterprise RAG" now sits under **"Build an Enterprise RAG Pipeline"** (page updated February 2026) [P].
- Listed features: multimodal extraction, audio/video, VLM answers, hybrid search, reranking, agentic RAG, and an MCP server [P].
- **Vendor-reported:** "15x" multimodal extraction throughput and a 50% reduction in incorrect answers versus an open-source alternative on one H100 [P]. Not independently verified, and the baseline is not named on the page excerpt.

### 3.4 NIM

- NIM is a set of containers for self-hosting GPU-accelerated inference using TensorRT-LLM, vLLM or SGLang, exposing "industry-standard APIs" [V].
- **Licensing** [V]:
  - Development and test access comes through the NVIDIA Developer Program, including "free access to NIM API endpoints for unlimited prototyping".
  - **Production self-hosting is positioned under NVIDIA AI Enterprise.**

### 3.5 NeMo Agent Toolkit: deprecated (changed recently)

- The repository states: "NVIDIA NeMo Agent Toolkit has been deprecated as of October 2026 and will reach end of life (EOL) by end of year 2026" [V].
- Suggested migrations: **NeMo Relay** (observability and governance), **NeMo Helix** (evaluation and optimization CLI), and **NeMo Fabric** (agent harnesses) [V].
- **What it offered, as ideas to copy:**
  - a profiler run through `nat eval`, producing per-request metrics CSV, aggregated JSON, trace events and a Gantt chart of LLM/tool spans,
  - token and tool-usage forecasting,
  - evaluators including Ragas metrics and a trajectory evaluator.
  - The docs also marked evaluation "experimental" [P].
- **Do not adopt** the toolkit itself.

### 3.6 NeMo Guardrails

- **License.** Apache-2.0 [V].
- **Five rail types** [V]:
  1. input,
  2. dialog,
  3. retrieval (filters retrieved chunks before they reach the LLM),
  4. execution (tool inputs and outputs),
  5. output.
- **Colang.** Colang 1.0 is the default, and 2.0 is supported [V].
- **Versions.** The README lists 0.24.1 as the latest release and also says 0.25.0 dropped Python 3.10 [V]. The inconsistency probably reflects a release in progress.

**Lesson.** "Retrieval rails" is the right abstraction for MindDoc's prompt-injection scan. Treat every retrieved chunk as untrusted input and filter or sanitise it *before* context assembly.

### 3.7 What a CPU-only student build can realistically use

| NVIDIA asset | Usable on CPU-only? | Notes |
|---|---|---|
| Pipeline *design* (page elements, then table structure, then graphic elements, then OCR, with per-element rows) | Yes, as a pattern | Re-implement with CPU models (Docling or PaddleOCR; see TECHNOLOGY_EVALUATION §4). |
| Hosted NIM endpoints (build.nvidia.com) | Yes, for prototyping | Documents leave the machine. Use only for non-sensitive test data, and production terms differ (§3.4). |
| NeMo Retriever Library local models | No | GPU required [P]. |
| NeMo Guardrails | Yes | Python library. The rails call an LLM, so latency and cost come from the LLM. |
| NeMo Agent Toolkit | Do not adopt | Deprecated (§3.5). |
| Nemotron embed/rerank 1B | Technically CPU-runnable [K] but slow | License stack: NVIDIA Open Model License plus Llama 3.2 terms. |

---

## 4. Microsoft

### 4.1 GraphRAG indexing pipeline

The default dataflow, in order [V]:

1. **TextUnits.** Chunk documents (default 1,200 tokens).
2. **Documents table.** Link documents to their units for provenance.
3. **Graph extraction.**
   - The LLM extracts entities and relationships per unit, and the results are merged.
   - The LLM summarises each entity and relationship description.
   - **Claim extraction** ("covariates") is **optional and off by default**, and generally needs prompt tuning.
4. **Graph augmentation.** Hierarchical **Leiden** community detection runs recursively until a community-size threshold is reached.
5. **Community summarization.** The LLM writes a **community report** per community, then summarises each report.
6. **Embeddings.** Entity descriptions, text units and community reports are embedded into a vector store.

Variants and status:

- **FastGraphRAG** replaces LLM extraction with NLP and always skips claims [V].
- **Query modes:**
  - **Global** uses community summaries.
  - **Local** uses entity neighbourhoods.
  - **DRIFT** is local search plus community context.
  - **Basic** is top-k vector search [V].
- **Status.** The README calls the code "a demonstration", not "an officially supported Microsoft offering". It warns that indexing "can be an expensive operation" and says to "start small". License is MIT [V].
- **Releases.** v3.0.0 restructured the code into a monorepo of packages and required `graphrag init --force`. v3.1.2 is the latest seen [P]. *Changed recently.*
- **Leiden implementation.** GraphRAG imports `hierarchical_leiden` from **graspologic** (MIT) [S][V for graspologic license].

### 4.2 DRIFT and LazyGraphRAG

- **DRIFT.** The query is matched against the top-K community reports to produce a primer answer plus follow-up questions, and each follow-up is run as a local search. On 50 "local" questions judged by an LLM, Microsoft reports DRIFT beat Local Search 78% of the time on comprehensiveness and 81% on diversity (vendor-reported) [P].
- **LazyGraphRAG** (Microsoft Research blog, 25 Nov 2024) [V]:
  - **Indexing.** NLP noun-phrase extraction plus co-occurrence graph statistics give a hierarchical community structure, with **no LLM summarization at index time**.
  - **Query.** LLM subquery refinement, then best-first and breadth-first matching with an LLM relevance test under a "relevance test budget", then map-reduce over extracted claims.
  - **Vendor-reported results:**
    - indexing cost "identical to vector RAG and 0.1% of the costs of full GraphRAG",
    - global-query quality comparable to GraphRAG Global Search at "more than 700 times lower query cost".
  - **Evaluation setup:** 5,590 AP news articles, 100 synthetic queries (50 local, 50 global), LLM pairwise judging on comprehensiveness, diversity and empowerment.
  - **Availability.** A June 2025 editor's note says it was integrated into Microsoft Discovery and Azure Local. The page does **not** confirm it ships in the open-source `graphrag` package [V].

### 4.3 What the GraphRAG evaluations do and do not show

From the paper "From Local to Global" (arXiv 2404.16130) [V]:

- **Datasets.** Podcast transcripts (about 1M tokens) and news articles (about 1.7M tokens). The authors used gpt-4-turbo.
- **Method.** 125 generated "sensemaking" questions per dataset. An LLM judge compared answers head-to-head on comprehensiveness, diversity and empowerment, with directness as a control. Each comparison ran five times.
- **Headline results.** Global GraphRAG beat vector RAG on comprehensiveness (72–83% podcast, 72–80% news) and diversity (75–82%, 62–71%). Vector RAG was the most "direct".
- **Token efficiency.** Root-level community summaries needed about 2.3–2.6% of the tokens of source-text summarisation.
- **Claim-based validation.** A second experiment used Claimify claim extraction (47,075 claims). Non-tie LLM labels agreed with claim-based labels 78% of the time for comprehensiveness and 69–70% for diversity.
- **Limitations the authors state:**
  - only two corpora of about 1M tokens,
  - **fabrication rates not measured**,
  - mixed empowerment results,
  - many claim-based ties (33% / 39%) and sensitivity to the tie threshold.

**Takeaway.** The evidence supports GraphRAG for **corpus-level sensemaking** ("what are the main themes?"). It does **not** show better **factual accuracy** or citation precision, which are the metrics an evidence platform lives on. MindDoc must measure those itself.

### 4.4 Azure Document Intelligence (layout model)

- **Naming.** Now titled **"Azure Document Intelligence in Foundry Tools"**. The doc was updated 2026-10-19. The current GA API is v4.0 (2024-11-30) [V]. *Changed recently: renamed under Foundry Tools.*
- **What layout extracts** [V]:
  - text, selection marks, tables, paragraphs,
  - paragraph **roles**: title, sectionHeading, pageHeader, pageFooter, pageNumber, footnote,
  - figures (with optional cropped figure images) and sections.
- **Tables** [V]:
  - row and column counts, row and column spans, and `columnHeader` flags,
  - per-cell bounding polygons and spans into the top-level `content`,
  - rotated tables are supported,
  - in 2024-11-30, table and figure bounding regions **exclude captions and footnotes**,
  - "Layout tables are extracted ... without considering the semantics of the content" [P].
- **Markdown output.** `outputContentFormat=markdown`. In v4.0, tables are rendered as **HTML tables** to preserve merged cells, and selection marks use Unicode ☒/☐ [V].
- **Geometry.**
  - Polygons are flat point lists, clockwise from the element's top-left [P].
  - Each page reports `unit`. The example shows `pixel`. PDFs are reported in inches [K], so verify before converting coordinates.
- **Limits.** Up to 2,000 PDF/TIFF pages, 500 MB on S0, images from 50×50 to 10,000×10,000 px [V].

**The design pattern to copy** (established, and also used by Claude Citations and Docling):

1. Keep **one canonical text string per document**.
2. Give every structural element **(a)** `spans` (offset, length) into that string and **(b)** `boundingRegions` (page number plus polygon).
3. Use spans for text-level citation and polygons for pixel-level highlighting.

MindDoc's `vision/highlight.py` already boxes cited passages. Make the span-and-polygon pair the *primary key of evidence* rather than a rendering detail.

---

## 5. OpenAI

### 5.1 Agents SDK

- **Core primitives.** Agents (an LLM with instructions and tools), agents as tools or **handoffs**, and **guardrails** (input and output validation) [V].
- **Other features** [V]:
  - function tools with automatic schemas, and MCP tool calling,
  - **sessions** (persistent working memory across runs),
  - **human in the loop**, **tracing**, realtime and voice agents,
  - **sandbox agents** (isolated workspaces, resumable sessions).
  - Tool guardrails appear in the API reference [V].
- **HITL mechanics** (worth copying exactly) [V]:
  - Mark a tool `needs_approval=True`, or pass an async function that decides per call.
  - When the model calls such a tool, the run **pauses**, and pending items appear as `interruptions` (`ToolApprovalItem`).
  - `result.to_state()` returns a `RunState`, which serialises with `to_string()`/`to_json()`. **Loading a state does not authenticate it**, so deserialise only from trusted storage.
  - `state.approve(item)` and `state.reject(item)` are scoped to a call ID. Options include `always_approve` and a custom rejection message.
  - Resume with `Runner.run(agent, state)`.
  - The docs recommend keeping snapshots server-side, authenticating reviewers, validating decisions against server-held pending items, and preventing replay.
  - **"Approval also does not guarantee exactly-once execution", so consequential tools should use idempotency keys.**

### 5.2 Structured Outputs

- **Guarantee.** With `strict: true`, the API "ensures the model will always generate responses that adhere to your supplied JSON Schema". JSON mode only guarantees valid JSON. Prefer Structured Outputs [V].
- **Failure modes.** Refusals are detectable programmatically, but "a refusal does not necessarily follow the schema". Check for refusal or incomplete output (for example, the max-tokens limit) before parsing. The first request with a new schema has extra latency [V].
- **Schema subset.** Only a subset of JSON Schema is supported, and unsupported keywords error under strict mode [S, via Azure docs]. The official full list was in a truncated part of the page [U]. Examples show `additionalProperties: false`, every property listed in `required`, and recursive `$ref` [V].

### 5.3 Agent evals and trace grading

- **Trace grading** assigns structured scores or labels to an agent trace (decisions, tool calls, reasoning steps). **Trace evals** aggregate graded traces across many examples to catch regressions [P].
- **Suggested questions:** did the agent pick the right tool, did a handoff happen when it should, and did it break an instruction or a safety policy [P].
- **Changed recently.** The standalone *graders* page states OpenAI "is deprecating graders as part of the evals and fine-tuning workflows" and points to a deprecations page for timelines [P]. The deprecations page could not be fetched [U]. **Do not build MindDoc's eval harness on OpenAI-hosted graders.** Keep evals local and vendor-neutral.

### 5.4 Human-in-the-loop patterns, synthesised (established)

| Pattern | Where documented | MindDoc use |
|---|---|---|
| Per-tool approval flag plus pause and resume with serialized state | OpenAI Agents SDK [V], ADK action confirmations [V], LangGraph `interrupt` + checkpointer [P], Palantir action tools with confirmation [P] | Any agent step that writes (merge entities, mark finding, export) |
| Stage edits, then human review, then commit | AIP Logic / Automate [P] | Agent-proposed `Finding` objects sit in `pending_review` |
| Request clarification as a tool | Palantir Chatbot Studio [P] | Agent asks the investigator instead of guessing |
| Idempotency keys on side-effecting tools | OpenAI HITL docs [V] | `action_id` UUID unique constraint |

---

## 6. Google

### 6.1 Agent Development Kit (ADK)

- **Docs moved.** Documentation now lives at **adk.dev** (redirected from google.github.io/adk-docs) [V].
- **Languages.** Python, TypeScript/JS, Go, Java and Kotlin [V].
- **Agent types** [V]:
  - LLM agents,
  - **workflow agents** (Sequential, Parallel, Loop), which are deterministic and not LLM-driven,
  - custom agents,
  - **graph workflows** with routes, retries and timeouts, labelled "New in ADK 2.0!". ADK TypeScript 2.0 is GA with graph workflows. *Changed recently.*
- **Tools and runtime** [V]:
  - function, MCP and OpenAPI tools,
  - sessions with rewind, state, memory, artifacts, and context compression and caching,
  - callbacks and plugins.
- **Human in the loop.** Action confirmations for function tools, human input in graph workflows, and resume and cancel for runs [V].
- **Evaluation** [V]:
  - **Test files** (`*.test.json`, one session) for unit-style checks, and **evalsets** (many sessions) for integration-style runs.
  - Criteria include:
    - `tool_trajectory_avg_score` (exact trajectory match),
    - `response_match_score` (ROUGE-1),
    - `final_response_match_v2` (LLM-judged),
    - `rubric_based_final_response_quality_v1`, `rubric_based_tool_use_quality_v1`,
    - `hallucinations_v1`, `safety_v1`,
    - multi-turn criteria.
  - Defaults: trajectory 1.0, response match 0.8.
  - Efficiency metrics (tool calls, tokens, duration) are reported but never pass or fail a run.
  - Run with `adk eval`, pytest (`AgentEvaluator.evaluate`), or the web UI.
  - Some LLM criteria need Vertex credentials.

**Lesson.** Separate **trajectory** evaluation (did the agent call the right tools in a sensible order?) from **final-response** evaluation, and report cost and latency alongside quality.

### 6.2 Gemini document understanding

- **Limits.** PDFs up to **50 MB or 1,000 pages**, and each page counts as **258 tokens** [V].
- **Scaling.** Pages larger than 3072×3072 are scaled down and pages smaller than 768×768 are scaled up. Higher resolution "doesn't improve performance" [V].
- **Files API** stores uploads for 48 hours [V].
- **Non-PDF formats** [V]:
  - DOC/PPT are rendered as images.
  - DOCX/PPTX send extracted text plus embedded images, so layout and charts may be lost.
  - XLSX sends only the **first sheet**, as CSV, losing formulas.
- **Billing note (Gemini 3).** Native PDF text isn't billed, and image-processed pages count under the IMAGE modality [V].
- **Gap for MindDoc.** Gemini returns understanding, not a guaranteed coordinate map. If you use it, pair it with a layout extractor that supplies polygons.

### 6.3 Document AI

- **Processor families** [V]:
  - Enterprise Document OCR (200+ languages, handwriting, quality scoring),
  - Form Parser (key-value pairs, checkboxes, tables),
  - **Layout Parser** (text, tables, lists, and **context-aware chunks**; some preview versions are Gemini-based),
  - Custom Extractor (generative versions are Gemini-based and officially English-only),
  - Custom Classifier and Splitter,
  - specialised parsers (invoice, bank statement, ID proofing, and others).
- **Layout Parser chunking.** Chunks can carry **ancestor headings and table titles**, so a paragraph isn't separated from its heading [P].
- **Gemini layout parser versions** run on Gemini 3.0 Pro/Flash and are labelled preview [P].

**Lesson (established).** Chunk along document structure, and prepend the heading path to each chunk. This is the same idea as Anthropic's Contextual Retrieval, done deterministically.

---

## 7. Anthropic

### 7.1 "Building effective agents" (19 Dec 2024)

- **Definitions** [V]:
  - **Workflows** are "systems where LLMs and tools are orchestrated through predefined code paths".
  - **Agents** dynamically direct their own process and tool use.
- **Workflow patterns:**
  - prompt chaining,
  - routing,
  - parallelization (sectioning or voting),
  - orchestrator-workers,
  - evaluator-optimizer.
- **Advice:**
  - Start with the simplest solution, and add agents only when the number of steps is unpredictable.
  - Agents cost more and compound errors.
  - Frameworks can hide prompts, so understand what's underneath.
  - Invest in the agent-computer interface (tool docs, examples, "poka-yoke" parameters).
- **Three principles:** simplicity, transparency (show the plan), and careful tool design [V].
- The page now notes that "much of the tooling landscape has changed" since publication [V].

**Mapping to MindDoc:**
- Ingestion is prompt chaining plus routing (by document class).
- Q&A is a workflow: plan, retrieve, rerank, generate, then verify (already in `ai/rag.py`).
- Only **investigations** (open-ended, multi-hop, unknown step count) justify an agent loop.

### 7.2 Contextual Retrieval (19 Sep 2024)

- **Method.** Prepend 50–100 tokens of LLM-generated, chunk-specific context before both embedding and BM25 indexing [V].
- **Vendor-reported results.** The metric is 1 − recall@20 (failed retrievals) [V]:

| Configuration | Failure rate | Reduction |
|---|---|---|
| Baseline | 5.7% | — |
| Contextual Embeddings | 3.7% | −35% |
| + Contextual BM25 | 2.9% | −49% |
| + reranking | 1.9% | −67% |

- **Cost.** About $1.02 per million document tokens, one time, using prompt caching [V].
- **Domains tested:** code, fiction, ArXiv and science papers [V].
- **Caveats Anthropic itself gives** [V]:
  - Under about 200k tokens, put everything in the prompt instead of using RAG.
  - Chunking choices matter.
  - Reranking adds latency.
  - "Run evaluations on your own data."
- **CPU-friendly variant for MindDoc (established).** Generate the context *deterministically* from the structure (document title + section path + page + table caption), and optionally add LLM context for high-value corpora.

### 7.3 Model Context Protocol (MCP): current revision 2026-07-28 (changed recently)

The changelog lists changes since 2025-11-25 [V]:

- **Stateless protocol.** Protocol-level sessions, the `Mcp-Session-Id` header and the initialize handshake are removed. Every request now carries its protocol version and capabilities in `_meta`. A new `server/discover` RPC advertises supported versions and capabilities.
- **Tasks extension.** Tasks moved out of core into the `io.modelcontextprotocol/tasks` extension, with polling via `tasks/get` and input via `tasks/update`.
- **Multi Round-Trip Requests** replace server-initiated sampling and elicitation requests.
- **Deprecated:** Roots, Sampling and Logging, the HTTP+SSE transport, and Dynamic Client Registration (in favour of Client ID Metadata Documents).
- **Tracing:** OpenTelemetry trace-context propagation is documented for `_meta` keys.
- **Caching:** results carry `ttlMs`/`cacheScope`.

**Implication.** If MindDoc exposes its evidence tools over MCP, target the 2026-07-28 revision. Treat MCP as a **transport for the same governed actions and queries**, not as a separate permission model.

### 7.4 Citations API

- **Location types** [V]:
  - `char_location` for plain text,
  - `page_location` for PDFs,
  - `content_block_location` for custom content.
- **How it works.** PDFs are text-extracted and chunked into sentences. `cited_text` does not count toward output tokens (or input tokens when passed back). The API guarantees "valid pointers to the provided documents" [V].
- **Limits** [V]:
  - **Image citations are not supported.** "PDFs that are scans of documents and do not contain extractable text are not citable."
  - **Citations and structured outputs are incompatible.** Using both returns HTTP 400.

**Implication for MindDoc.** Scanned evidence must be OCR'd *by MindDoc* and passed as custom-content blocks (your own region-level chunks). Each cited block then maps back to MindDoc's region ID, polygon and span. Do not depend on the provider to ground scans.

---

## 8. Other relevant platforms and libraries

### 8.1 Quantexa: entity resolution and graph decision intelligence

- **Positioning.** Entity resolution feeds **network generation**, which "dynamically generates the context needed to automate millions of operational decisions" [P].
- **Claims.** ER models need "no need for pre-resolved training data", with **batch and dynamic** modes. Use cases are AML, fraud, credit risk and customer intelligence [P].
- **Stack.** Built on Hadoop, Spark and Elastic [P].
- **Not public:** internal algorithms and accuracy claims ("99%") are marketing [U].

**Principle (established in record linkage).**
1. Resolve entities with explainable match weights.
2. Build the graph from **resolved** entities.
3. Generate the network *around a subject on demand* rather than computing one giant global graph.

For MindDoc, investigations should start from a subject entity and expand k hops over resolved entities with evidence-weighted edges.

### 8.2 Hebbia

- **Architecture as described.** "Matrix" is a grid UI on a multi-agent framework. An orchestrator delegates to independent subsystems (distillation, reasoning, output agents), each with a tightly scoped context [P via Hebbia blog].
- **Decomposition.** Hebbia calls its approach "iterative source decomposition" and says it processes full documents [S].
- **Reported redesign.** Separating retrieval from output formatting reportedly "nearly eliminated tool-use hallucinations" [S].

**Principle.** A **grid UI** (rows = documents, columns = questions, cells = cited answers) is a strong, auditable interface for evidence review. Every cell is an independent, retryable, cacheable job.

### 8.3 Neo4j GraphRAG patterns

- **`neo4j-graphrag` Python package** [P]:
  - `VectorRetriever` runs similarity search on a vector index.
  - **`VectorCypherRetriever`** runs vector search, then a custom Cypher query to pull graph context.
  - `SimpleKGPipeline` builds a KG from text with an LLM (requires APOC).
- **Principle (established).** "Vector entry point, then graph expansion" is portable. In Postgres it is a pgvector top-k followed by a recursive CTE over `edges`.

### 8.4 Zep / Graphiti: temporal knowledge graphs for agents

- **Paper.** arXiv 2501.13956 (Jan 2025) [V].
  - Graphiti is a "temporally-aware knowledge graph engine".
  - **Vendor-reported:** 94.8% vs 93.4% (MemGPT) on DMR, and up to 18.5% accuracy improvement with 90% lower latency on LongMemEval.
- **Model** [S]:
  - **bi-temporal edges**: event validity window (`valid_at`/`invalid_at`) plus ingestion time,
  - conflicting facts are **invalidated, not deleted**, using an LLM invalidation prompt per new edge,
  - hybrid retrieval combining cosine, BM25 and BFS, with point-in-time queries.
- **Library** [V]:
  - Apache-2.0.
  - Backends: Neo4j 5.26, FalkorDB, and Amazon Neptune. **Kuzu is marked deprecated.**
  - It "works best with LLMs that support structured output", and other services "may result in incorrect output schemas and ingestion failures".

**Principle for MindDoc (established in temporal databases).** Every `Claim` and `Relationship` row gets:
- `valid_from` and `valid_to` (world time, extracted from the document),
- `recorded_at` and `superseded_at` (system time).

Contradictions create a new row plus a `supersedes` link, never an UPDATE that loses history.

### 8.5 Docling (IBM, LF AI & Data)

- **Basics.** MIT code, hosted in the LF AI & Data Foundation. Broad format coverage (PDF, Office, HTML, images, audio, email). A unified `DoclingDocument` with lossless JSON export [V].
- **Models.** An RT-DETR-based layout model (11 labels) and TableFormer. HF tags show CDLA-Permissive-2.0 and Apache-2.0 [V]. **Granite-Docling-258M** (Apache-2.0, 17 Sep 2025) is the end-to-end VLM option and outperforms SmolDocling on Docling's own benchmarks [V].
- **CPU numbers** (2024 technical report, OCR off, 225 pages) [V]:
  - Apple M3 Max: 1.27–2.45 pages/s.
  - Xeon E5-2690: 0.60–1.57 pages/s.
  - TableFormer: 2–6 s per table on CPU.
  - EasyOCR on CPU: "upwards of 30 seconds per page" (the reason to prefer other OCR engines on CPU).

### 8.6 LlamaIndex and LangGraph

- **LangGraph** [P]:
  - `interrupt()` pauses a node and persists state through a **checkpointer**, keyed by a thread ID.
  - With a checkpointer, "you already have durable execution enabled".
  - Docs advise deterministic, idempotent nodes, side effects wrapped in tasks, and a durable (Postgres/SQLite) checkpointer in production.
- **LlamaIndex** [K]: indexing and retrieval abstractions plus event-driven "Workflows". LlamaParse is a hosted commercial parser. Not re-verified this session.

**Principle.** Whatever framework you use, the investigation state must live in **your** database (`investigation_steps` table). A framework checkpointer is an implementation detail behind it.

---

## 9. Synthesis: established practice vs speculative ideas

### 9.1 Established engineering practice (adopt with confidence)

| # | Practice | Evidence |
|---|---|---|
| E1 | Typed object model with governed actions as the only write path, plus an audit log | Palantir Ontology and actions [V/P]. Standard CQRS and command patterns [K]. |
| E2 | Canonical text with offset spans and per-element polygons as the grounding primitive | Azure DI [V], Claude Citations [V], Marker polygons [V] |
| E3 | Per-element extraction pipeline (layout, then table structure, then OCR) with versioned strategies, evaluated per document class | NVIDIA [V], Docling [V], Palantir Doc Intelligence [P] |
| E4 | Hybrid lexical plus dense retrieval, rank fusion, cross-encoder rerank | Anthropic [V], pgvector README [V], Qdrant RRF/DBSF [V] |
| E5 | Structure-aware chunking with a heading path in the chunk | Document AI Layout Parser [P], Contextual Retrieval [V] |
| E6 | Entity resolution before graph analytics, with explainable match weights | Quantexa [P], Splink (Fellegi-Sunter) [V] |
| E7 | Bi-temporal facts and invalidate-not-delete | Graphiti [V/S], temporal DB practice [K] |
| E8 | Mandatory labels that propagate along lineage and are enforced for LLM context too | Palantir Markings [P/V] |
| E9 | Workflows for predictable tasks, agents only for open-ended ones | Anthropic [V], ADK workflow agents [V] |
| E10 | HITL via pause, serialized state and resume, plus idempotency keys | OpenAI [V], LangGraph [P], ADK [V] |
| E11 | Transactional outbox for side effects, and at-least-once consumers that are idempotent | Debezium docs [V], Kafka EOS limits [V] |
| E12 | Eval suites per stage (extraction, retrieval, answer, trajectory) in CI | AIP Evals [P], ADK [V], RAGAS/ARES/DeepEval [V] |
| E13 | OpenTelemetry traces across pipeline and LLM calls | MLflow OTel compatibility [V], MCP trace propagation [V] |

### 9.2 Promising but speculative (prototype behind a flag, then measure)

| # | Idea | Why speculative | How to de-risk |
|---|---|---|---|
| X1 | GraphRAG-style community reports over a case corpus | Evidence is LLM-judged "sensemaking" wins, fabrication is unmeasured, cost is high | Compute only for a curated investigation subset. Score report claims for citation precision. |
| X2 | LazyGraphRAG-style deferred graph summarisation | The Microsoft implementation isn't confirmed in OSS. MindDoc would re-implement it. | Compare against hybrid RAG on 30 global questions from your own corpus. |
| X3 | Agentic investigations that generate hypotheses | Errors compound (Anthropic) and no public benchmark fits the evidence domain | Constrain the agent to read-only tools plus "propose finding". Grade trajectories. |
| X4 | ML anomaly discovery (graph or time-series outliers) as leads | High false-positive risk and no ground truth | Present as ranked leads with SHAP explanations, and track investigator accept rate. |
| X5 | Small local VLM for end-to-end page parsing on CPU | Throughput and accuracy on MindDoc documents unknown | Benchmark Granite-Docling vs Docling's standard pipeline on 50 labelled pages. |
| X6 | LLM-based temporal invalidation of conflicting claims (Graphiti-style) | One LLM call per new edge, and errors silently retire true facts | Rules first (same subject, predicate and period). LLM only proposes, and a human approves. |

---

## 10. Recommended for MindDoc

| Principle / pattern | Source platform(s) | Adopt | Concrete MindDoc mechanism |
|---|---|---|---|
| Evidence ontology (typed objects, interfaces, links) | Palantir | **Now** | SQL tables `document, page, region, claim, entity, relationship, investigation, finding` plus an `interfaces` convention (`Grounded`, `Temporal`, `Marked`) |
| Actions as the only write path, with audit | Palantir, OpenAI, ADK | **Now** | `actions` registry (name, params schema, criteria fn) and an `action_log` table. All UI and agent writes go through `POST /actions/{name}`. |
| AI proposes, human commits | AIP Logic, Chatbot Studio, OpenAI HITL | **Now** | `finding.status ∈ {proposed, approved, rejected}`. Agents can only call `propose_*`. Approval endpoint requires reviewer auth plus an idempotency key. |
| Span + polygon + extractor version on every derived row | Azure DI, Claude Citations, Docling | **Now** | `region(page_id, bbox_polygon, char_start, char_end, extractor, extractor_version, config_hash)` |
| Per-document-class extraction strategies with evals | Palantir Doc Intelligence, NVIDIA, Docling | **Now** (simple), **Later** (VLM strategies) | Strategy config YAML per class. Benchmark CER, TEDS and pages/s on a 50-page labelled set. |
| Structure-aware chunks with heading path; hybrid + rerank | Document AI, Anthropic | **Now** | Prefix `title > section > page` to the chunk text. BM25 (Postgres FTS) plus pgvector, then RRF, then cross-encoder. |
| LLM contextual chunk prefixes | Anthropic | **Later**. Trigger: recall@20 on your eval set plateaus below target after the deterministic prefix. | Batch job with prompt caching, stored as `chunk.context` |
| Entity resolution before graph analytics | Quantexa | **Now** | Splink (DuckDB) over the entity mention table, writing `entity_cluster_id` and match weights |
| Subject-centred network generation | Quantexa, Neo4j VectorCypher | **Now** | pgvector entry, then recursive CTE k-hop, then igraph PageRank/Leiden on the subgraph |
| Bi-temporal claims; invalidate, don't delete | Graphiti | **Now** (schema), **Later** (LLM invalidation) | `valid_from, valid_to, recorded_at, superseded_at, supersedes_id` |
| Markings propagate along lineage and gate the LLM context | Palantir | **Later**. Trigger: first multi-user or shared workspace with mixed sensitivity. | `marking` column, max-of-sources propagation, filter in the retriever and context builder |
| Retrieval rails (treat chunks as untrusted) | NeMo Guardrails | **Now** | Existing `guardrails.py` injection scan applied per chunk before context assembly |
| Workflows for ingestion and Q&A; agent only for investigations | Anthropic, ADK | **Now** | Keep `rag.py` as a workflow. New `investigations` module with bounded agent loop and step budget. |
| Eval suites per stage, in CI | AIP Evals, ADK, OpenAI trace grading | **Now** | `tests/evals/` with extraction, retrieval, answer-faithfulness and trajectory suites, run via pytest |
| Trace grading of agent runs | OpenAI, ADK | **Later**. Trigger: the investigation agent exists. | Store OTel spans, grade tool choice and order against gold trajectories |
| GraphRAG community reports | Microsoft | **Later / limited**. Trigger: users ask corpus-level "themes" questions over at most about 1M tokens per case. | Leiden (igraph) communities, then LLM report with citations per claim, scored for citation precision |
| MCP server for evidence tools | Anthropic MCP, Palantir Ontology MCP | **Later**. Trigger: external agent clients need access. | Target the 2026-07-28 spec and expose only read queries and `propose_*` actions |
| Hosted NVIDIA NIM / NeMo Retriever | NVIDIA | **No** for core (GPU or hosted data egress) | Copy the pipeline design only |
| NeMo Agent Toolkit | NVIDIA | **No** | Deprecated October 2026 |

---

## 11. Sources

Dates are publication or last-updated dates where shown, otherwise "accessed 2026-11-10". Type: **P** = primary (vendor docs, repository, paper), **S** = secondary.

| # | URL | Publisher | Date | Type |
|---|---|---|---|---|
| 1 | https://palantir.com/docs/foundry/ontology/core-concepts/ | Palantir | accessed 2026-11-10 | P |
| 2 | https://palantir.com/docs/foundry/object-link-types/type-reference/ | Palantir | accessed 2026-11-10 | P |
| 3 | https://palantir.com/docs/foundry/interfaces/interface-overview/ | Palantir | accessed 2026-11-10 | P |
| 4 | https://palantir.com/docs/foundry/action-types/submission-criteria/ | Palantir | accessed 2026-11-10 | P |
| 5 | https://palantir.com/docs/foundry/action-types/side-effects-overview/ | Palantir | accessed 2026-11-10 | P |
| 6 | https://www.palantir.com/docs/foundry/action-types/webhooks | Palantir | accessed 2026-11-10 | P |
| 7 | https://palantir.com/docs/foundry/action-types/test-run/ | Palantir | accessed 2026-11-10 | P |
| 8 | https://palantir.com/docs/foundry/announcements/2025-10/ | Palantir | Oct 2025 | P |
| 9 | https://www.palantir.com/docs/foundry/security/markings | Palantir | accessed 2026-11-10 | P |
| 10 | https://palantir.com/docs/foundry/security/access-control-propagation/ | Palantir | accessed 2026-11-10 | P |
| 11 | https://palantir.com/docs/foundry/security/classification-based-access-controls/ | Palantir | accessed 2026-11-10 | P |
| 12 | https://www.palantir.com/docs/foundry/privacy-civil-liberties/pcl-in-practice/ | Palantir | accessed 2026-11-10 | P |
| 13 | https://palantir.com/docs/foundry/checkpoints/configure-checkpoints/ | Palantir | accessed 2026-11-10 | P |
| 14 | https://palantir.com/docs/foundry/aip/control-llm-data-access-with-markings/ | Palantir | accessed 2026-11-10 | P |
| 15 | https://www.palantir.com/docs/foundry/logic/overview/ | Palantir | accessed 2026-11-10 | P |
| 16 | https://palantir.com/docs/foundry/logic/staged-writes/ | Palantir | accessed 2026-11-10 | P |
| 17 | https://palantir.com/docs/foundry/agent-studio/tools | Palantir | accessed 2026-11-10 | P |
| 18 | https://palantir.com/docs/foundry/agent-studio/overview/ | Palantir | accessed 2026-11-10 | P |
| 19 | https://www.palantir.com/docs/foundry/palantir-mcp/ | Palantir | accessed 2026-11-10 | P |
| 20 | https://palantir.com/docs/foundry/aip-evals/create-suite/ | Palantir | accessed 2026-11-10 | P |
| 21 | https://palantir.com/docs/foundry/aip-evals/run-suite/ | Palantir | accessed 2026-11-10 | P |
| 22 | https://www.palantir.com/docs/foundry/document-intelligence/overview/ | Palantir | accessed 2026-11-10 | P |
| 23 | https://palantir.com/docs/foundry/document-intelligence/core-concepts/ | Palantir | accessed 2026-11-10 | P |
| 24 | https://palantir.com/docs/foundry/document-intelligence/deploy-to-python-transforms/ | Palantir | accessed 2026-11-10 | P |
| 25 | https://docs.nvidia.com/nemo/retriever/latest/extraction/multimodal-extraction/ | NVIDIA | 26.8.x era, accessed 2026-11-10 | P |
| 26 | https://docs.nvidia.com/nemo/retriever/latest/extraction/prerequisites-support-matrix/ | NVIDIA | accessed 2026-11-10 | P |
| 27 | https://docs.nvidia.com/nemo/retriever/26.5.0/extraction/prerequisites-support-matrix/ | NVIDIA | 26.5.0 | P |
| 28 | https://build.nvidia.com/nvidia/nemoretriever-table-structure-v1/modelcard | NVIDIA | accessed 2026-11-10 | P |
| 29 | https://build.nvidia.com/nvidia/build-an-enterprise-rag-pipeline/blueprintcard | NVIDIA | updated Feb 2026 | P |
| 30 | https://developer.nvidia.com/blog/nvidia-nemo-retriever-delivers-accurate-multimodal-pdf-data-extraction-15x-faster/ | NVIDIA | accessed 2026-11-10 | P (vendor claim) |
| 31 | https://docs.api.nvidia.com/nim/reference/nvidia-llama-nemotron-embed-1b-v2 | NVIDIA | accessed 2026-11-10 | P |
| 32 | https://docs.api.nvidia.com/nim/reference/nvidia-llama-nemotron-rerank-1b-v2 | NVIDIA | accessed 2026-11-10 | P |
| 33 | https://developer.nvidia.com/nim | NVIDIA | accessed 2026-11-10 | P |
| 34 | https://github.com/NVIDIA/NeMo-Agent-Toolkit | NVIDIA | deprecation notice Oct 2026 | P |
| 35 | https://docs.nvidia.com/nemo/agent-toolkit/1.9/improve-workflows/profiler.html | NVIDIA | v1.9 | P |
| 36 | https://docs.nvidia.com/nemo/agent-toolkit/1.9/improve-workflows/evaluate.html | NVIDIA | v1.9 | P |
| 37 | https://github.com/NVIDIA-NeMo/Guardrails | NVIDIA | accessed 2026-11-10 | P |
| 38 | https://microsoft.github.io/graphrag/index/default_dataflow/ | Microsoft | accessed 2026-11-10 | P |
| 39 | https://microsoft.github.io/graphrag/ | Microsoft | accessed 2026-11-10 | P |
| 40 | https://github.com/microsoft/graphrag | Microsoft | accessed 2026-11-10 | P |
| 41 | https://github.com/microsoft/graphrag/releases | Microsoft | accessed 2026-11-10 | P |
| 42 | https://arxiv.org/html/2404.16130v2 | Edge et al., Microsoft Research | 2024 (v2) | P (paper) |
| 43 | https://www.microsoft.com/en-us/research/blog/introducing-drift-search-combining-global-and-local-search-methods-to-improve-quality-and-efficiency/ | Microsoft Research | 2024 | P |
| 44 | https://www.microsoft.com/en-us/research/blog/lazygraphrag-setting-a-new-standard-for-quality-and-cost/ | Microsoft Research | 25 Nov 2024 (note 6 Jun 2025) | P |
| 45 | https://microsoft.github.io/graspologic/latest/reference/reference/partition.html | Microsoft | accessed 2026-11-10 | P |
| 46 | https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/prebuilt/layout?view=doc-intel-4.0.0 | Microsoft | updated 2026-10-19 | P |
| 47 | https://openai.github.io/openai-agents-python/ | OpenAI | accessed 2026-11-10 | P |
| 48 | https://openai.github.io/openai-agents-python/human_in_the_loop/ | OpenAI | accessed 2026-11-10 | P |
| 49 | https://developers.openai.com/api/docs/guides/structured-outputs | OpenAI | accessed 2026-11-10 | P |
| 50 | https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/structured-outputs | Microsoft | accessed 2026-11-10 | S (for OpenAI schema subset) |
| 51 | https://developers.openai.com/api/docs/guides/trace-grading | OpenAI | accessed 2026-11-10 | P |
| 52 | https://developers.openai.com/api/docs/guides/agent-evals/ | OpenAI | accessed 2026-11-10 | P |
| 53 | https://developers.openai.com/api/docs/guides/graders.md | OpenAI | accessed 2026-11-10 (snippet) | P |
| 54 | https://adk.dev/ | Google | accessed 2026-11-10 | P |
| 55 | https://adk.dev/evaluate/ | Google | accessed 2026-11-10 | P |
| 56 | https://aistudio.google.com/docs/document-processing (redirect from ai.google.dev) | Google | accessed 2026-11-10 | P |
| 57 | https://docs.cloud.google.com/document-ai/docs/processors-list | Google | accessed 2026-11-10 | P |
| 58 | https://docs.cloud.google.com/document-ai/docs/layout-parse-chunk | Google | accessed 2026-11-10 | P |
| 59 | https://www.anthropic.com/engineering/building-effective-agents | Anthropic | 19 Dec 2024 | P |
| 60 | https://www.anthropic.com/news/contextual-retrieval | Anthropic | 19 Sep 2024 | P |
| 61 | https://modelcontextprotocol.io/specification/latest/changelog | MCP project | rev. 2026-07-28 | P |
| 62 | https://platform.claude.com/docs/en/build-with-claude/citations | Anthropic | accessed 2026-11-10 | P |
| 63 | https://www.quantexa.com/platform/entity-resolution-software/ | Quantexa | accessed 2026-11-10 | P (vendor) |
| 64 | https://a-teaminsight.com/blog/quantexa-addresses-aml-with-contextual-decision-intelligence/ | A-Team Insight | n.d. | S |
| 65 | https://www.hebbia.com/blog/inside-hebbias-deeper-research-agent | Hebbia | accessed 2026-11-10 | P (vendor) |
| 66 | https://sacra.com/c/hebbia/ | Sacra | accessed 2026-11-10 | S |
| 67 | https://openai.com/index/hebbia | OpenAI | accessed 2026-11-10 | S (customer story) |
| 68 | https://neo4j.com/developer/genai-ecosystem/graphrag-python/ | Neo4j | accessed 2026-11-10 | P |
| 69 | https://arxiv.org/abs/2501.13956 | Rasmussen et al. (Zep) | 20 Jan 2025 | P (paper) |
| 70 | https://github.com/getzep/graphiti | Zep | accessed 2026-11-10 | P |
| 71 | https://blog.getzep.com/beyond-static-knowledge-graphs/ | Zep | n.d. | P (vendor blog) |
| 72 | https://github.com/docling-project/docling | Docling / LF AI & Data | accessed 2026-11-10 | P |
| 73 | https://arxiv.org/html/2408.09869 | Auer et al. (IBM) | 2024 | P (tech report) |
| 74 | https://huggingface.co/ibm-granite/granite-docling-258M | IBM | 17 Sep 2025 | P |
| 75 | https://docs.langchain.com/oss/python/langgraph/interrupts | LangChain | accessed 2026-11-10 | P |
| 76 | https://docs.langchain.com/oss/javascript/langgraph/durable-execution | LangChain | accessed 2026-11-10 | P |
