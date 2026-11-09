# ADR-0004 — Claim-centric, bitemporal evidence model

**Status:** Proposed

**Context.** v2 stores entities and co-occurrence edges; an extracted statement and a verified fact look identical and
corrections overwrite history. Forensic reports must disclose the "material relied upon" and survive challenge.

**Decision.** Adopt `docs/architecture/DATA_MODEL.md`: Source → Page → Region → Mention/Claim → Evidence;
relationships are materialised from claims with an explicit epistemic status; valid time and system time on claims
and relationships; append-only reviews, resolutions and merges.

**Alternatives.** Property graph with a single confidence attribute (loses provenance and history); full event
sourcing of every table (heavier than needed).

**Consequences.** More tables and joins; every UI element can explain *why*; time-travel and graph diff become
queries; ML and graph analytics consume a clean, labelled substrate.

**Revisit when.** Lineage or time-travel query latency exceeds targets at ~10M claims.
