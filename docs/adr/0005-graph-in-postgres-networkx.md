# ADR-0005 — Graph in Postgres + NetworkX/graspologic; no graph database yet

**Status:** Accepted (owner mandate 2026-11-10) — amended

**Context.** Case graphs are thousands to low millions of edges. Neo4j Community and GDS are GPLv3, with RBAC only in
Enterprise and GDS capped at 4 cores; igraph and leidenalg are GPL. The MVP is installed on customer machines, which
counts as distribution.

**Decision.** Store nodes/edges in Postgres (adjacency tables + recursive CTEs for paths); run analytics in-process with
NetworkX (BSD) and graspologic (MIT; Leiden / hierarchical Leiden) on case-scoped subgraphs; cache results per graph
version.

**Alternatives.** Neo4j (licence + second store); Apache AGE (Cypher inside Postgres — the first upgrade path);
igraph (fast but GPL).

**Consequences.** No Cypher for analysts; algorithms are bounded by single-process memory, which is fine per case.

**Revisit when.** Ad-hoc multi-hop querying becomes a product need (→ AGE) or interactive graphs exceed ~10M edges.

## Amendment 2026-11-10

Source: `docs/review/C_ADR_REVIEW.md`.
- Co-occurrence moves to a `co_mention` table and is shown as a weak signal, never as a relationship.
- graspologic stays in the optional ML profile; community detection runs on case-scoped graphs only.

## Implementation note 2026-11-13 (R5)

Built: migration 0008 moves `co_occurs` rows out of `relations` into `co_mentions`. Ingestion writes co-occurrence
only there. The knowledge graph shows it as dashed "named together" edges, counted separately from relations.
GraphRAG-lite may still use co-mentions as retrieval neighbours, after typed relations.
