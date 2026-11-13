# ADR-0011 — Bank-statement extraction: layout-generic geometry + balance arbitration

**Status:** Accepted (owner mandate 2026-11-10)

**Context.** Statement formats vary by bank and change over time. Bank-specific regex breaks on every change;
table models are general-purpose and not validated on statements; LLMs can invent or alter numbers. The only published
comparison found (AI-BAAM, arXiv 2510.16066) shows template extraction beating LLM pipelines on known formats in
accuracy and cost. Full design: `docs/review/E_BANK_STATEMENT_DESIGN.md`.

**Decision.**
1. Extract word boxes (pdfplumber/pypdfium2 for text layers; Tesseract/RapidOCR for scans).
2. Infer columns from a header lexicon (a data file) refined by numeric right-edge alignment; segment rows by date tokens
   with narration continuations.
3. Parse fields deterministically into `Money` (ADR-0010).
4. **Arbitrate** ambiguous interpretations (column roles, direction, row boundaries) by the statement's own running
   balances, recording that the choice was made by arbitration.
5. Reconcile deterministically (row, page, statement, printed totals, cross-statement) and **diagnose** failures with
   reason codes; never modify a value to force reconciliation.
6. Layout profiles confirmed by reviewers are stored as data and reused; hand-written templates only as a last resort
   justified by a StatementBench failure.
7. LLMs never produce or edit amounts, dates or balances.

**Alternatives.** Per-bank templates (high maintenance); table-recognition models as default (heavy, unvalidated);
LLM/VLM extraction (hallucination risk, cost, data egress).

**Consequences.** Own code to maintain (`app/finance/`); accuracy is measured, not assumed (StatementBench, H §3).

**Acceptance.** J R3/R4 targets on held-out layout families; zero false alarms on correctly extracted statements.
