# ADR-0005 — Graph in Postgres + NetworkX/graspologic; no graph database yet

**Status:** Proposed

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
