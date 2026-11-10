# ADR-0008 — Primary market: forensic review of borrower fund flows (India)

**Status:** Proposed — contested (decision at gate M1)

**Context.** Six candidate markets were scored in `docs/strategy/MARKET_SELECTION.md` (pain, willingness to pay,
competition, demo-data access, solo feasibility, showcase value). This supersedes the KYC suggestion in `docs/ROADMAP.md`.

**Decision.** Primary: loan end-use and related-party fund-trail review for Indian CA / forensic firms (4.05/5).
Fallback: procure-to-pay integrity for internal audit (3.70). The engine stays domain-agnostic; the domain lives in
ontology packs, detectors and report templates.

**Alternatives.** KYC / credit (most crowded), GST notices (low willingness to pay), legal (well-funded incumbents),
insurance (enterprise sales and sensitive data at this stage).

**Consequences.** Bank statements, Tally/ledger exports, GST summaries and director data become first-class parsers;
all demo data must be synthetic; findings are never labelled "fraud".

**Revisit when.** 25 interviews plus one retrospective pilot fail the kill criteria in MARKET_SELECTION §10.4.

## Amendment 2026-11-10

Source: `docs/review/C_ADR_REVIEW.md`.
`docs/review/D_MARKET_RESEARCH.md` found the problem real and regulation-driven (RBI 2026 fraud directions; 2024
wilful-defaulter direction; *Amit Iron*, 2026) but the business weaker than assumed (existing competitors; RBI allows
internal audit; capped fees). Rescored roughly level with procure-to-pay (3.70). The decision is taken at gate M1 on
interview evidence; work before M1 is market-agnostic.
