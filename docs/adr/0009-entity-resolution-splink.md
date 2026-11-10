# ADR-0009 — Entity resolution with Splink and human-confirmed merges

**Status:** Accepted (owner mandate 2026-11-10) — amended (factual fix)

**Context.** v2 merges entities only on identical normalised names, so "ABC Infra Pvt Ltd" and "A.B.C. Infrastructure
Private Limited" stay separate — and graph analytics are wrong whenever identities are wrong.

**Decision.** Deterministic pre-linking on validated strong identifiers (GSTIN, PAN, CIN, DIN, account + IFSC) with hard
cannot-link rules on conflicting strong identifiers; Splink (Fellegi–Sunter, DuckDB backend) for probabilistic matching
on names, addresses, phones and emails; score bands → auto-link / review queue / keep separate; every merge is a
reversible event carrying its "why linked" features. Reviewer decisions become labels for later threshold tuning.

**Alternatives.** Embedding similarity only (no calibrated match probabilities, weak on identifiers); Ditto (needs
labels and a GPU); Zingg (AGPL, Spark).

**Consequences.** An explainable, unsupervised baseline. Splink pulls in igraph (GPL) for clustering — isolate it or
replace the clustering step with NetworkX connected components in the shipped build.

**Revisit when.** ≥2k labelled pairs exist and a supervised matcher beats Splink on held-out F1.

## Amendment 2026-11-10

Source: `docs/review/C_ADR_REVIEW.md`.
- **Correction:** Splink 5.0.0 (MIT) has no hard dependency on igraph; `igraph` is the optional `splink[igraph]` extra.
  Install core Splink only. Splink also offers a `postgres` extra (evaluate in R5).
- Identifier validation runs before any identifier can drive a merge, and is implemented only from official
  specifications (GSTN, Income Tax, MCA, RBI), never from informal examples.
- UPI VPA and account + IFSC pairs are strong identifiers for statement counterparties.
