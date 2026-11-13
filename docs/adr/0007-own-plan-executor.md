# ADR-0007 — Own typed plan executor with four LLM roles

**Status:** Accepted (owner mandate 2026-11-10) — amended, deferred to R8

**Context.** Agent frameworks (OpenAI Agents SDK, Google ADK, LangGraph) provide loops, tools, handoffs and tracing;
NVIDIA NeMo Agent Toolkit is deprecated (EOL end-2026). Our hard requirements are durability in our own database,
permission checks per tool, provider independence (the v2 gateway already exists), reproducibility, and evaluation of
whole trajectories.

**Decision.** Implement a small executor: the Planner emits a JSON plan DAG validated against a tool registry (schema,
required permission, side-effect class); steps persist in `investigation_step`; the Verifier and Writer are separate
prompts with restricted inputs (`docs/architecture/INVESTIGATION_ENGINE.md`). Borrow patterns, not dependencies:
guardrails, handoffs and tracing spans (OpenAI Agents SDK), workflow-vs-agent split (Anthropic), evaluation sets (ADK).

**Alternatives.** Adopt the Agents SDK or LangGraph (faster start, but durability, authorisation and audit are still
ours to build, plus abstraction risk); Temporal now (heavy for the MVP).

**Consequences.** Roughly 1–2k lines we own and can explain end to end; fewer conveniences than a framework.

**Revisit when.** Multi-day human-in-the-loop timers are needed (→ Temporal) or the executor outgrows maintainability.

## Amendment 2026-11-10

Source: `docs/review/C_ADR_REVIEW.md`.
- **LLM roles never compute or alter numbers.** Amounts, totals, balances and date intervals come from deterministic,
  versioned tools with recorded inputs.
- Every tool declares whether it is deterministic; fragility re-runs (R8) re-execute deterministic stages by default.
