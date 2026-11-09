# MindDoc — Security & Governance Architecture (proposal v0.1)

> Current-state findings: `docs/audit/CURRENT_STATE_AUDIT.md`. This document defines the target controls.

## 1. Assets and adversaries

| Asset | Why it matters |
|---|---|
| Customer documents and derived claims | confidential financial/legal data; regulated personal data (India DPDP Act 2023) |
| The evidence graph and findings | integrity: a tampered edge or finding misleads an investigation |
| Audit trail | non-repudiation for decisions |
| Credentials, API keys, model provider keys | lateral movement, cost abuse |

| Adversary | Example |
|---|---|
| Other tenant | IDOR on `/documents/{id}`, cross-tenant retrieval through a shared index or cache |
| Malicious document author | **indirect prompt injection**, PDF/JS exploits, decompression bombs, poisoned "evidence" |
| Over-privileged insider / agent | agent executes actions beyond the user's rights; analyst edits evidence without trace |
| External attacker | credential stuffing, token theft, SSRF through connectors |

## 2. Controls (target)

### Identity & access
- OIDC/SSO for orgs (later); local accounts with Argon2id (or PBKDF2 ≥ 600k), MFA for admins.
- **RBAC** roles: `viewer`, `analyst`, `reviewer`, `admin`; **markings** on sources/regions/claims (`PII`, `PHI`,
  `PRIVILEGED`, custom) — Palantir-style mandatory controls checked *in addition to* roles.
- **Authorisation is enforced in the data layer**, not only in routes: every query is built through a
  `scoped_session(tenant, principal)` that injects tenant + marking predicates; Postgres **Row-Level Security**
  as defence in depth. Retrieval, graph traversal, analytics and agent tools all go through the same scope.
- Short-lived access tokens (15 min) + rotating refresh tokens; token revocation list.

### Agents & tools (the part most systems get wrong)
- Agents act **as the requesting principal** — never with a service account's broader rights.
- Tools are registered with a schema, a required permission and a side-effect class: `read`, `compute`,
  `write-proposal`, `external`. Only `read`/`compute` run autonomously; `write-proposal` creates an `Action` that a
  human with the right role must approve; `external` (email, ticket, webhook) is disabled by default per tenant.
- Document content is **data, never instructions**: retrieved text is wrapped and labelled as untrusted, instruction-like
  spans are neutralised, tool-call arguments derived from documents are validated against schemas and allow-lists
  (no URLs from documents reach an HTTP tool), and the system prompt is never overridable from context.
- Output validation: structured outputs are schema-validated; findings without evidence IDs are rejected by the
  verifier before reaching the UI.

### Data protection
- TLS everywhere; encryption at rest (disk/volume + object store SSE); per-tenant encryption keys later (envelope encryption).
- PII: detection at ingest → markings; optional **redaction before external LLM calls** per tenant policy
  (with re-identification map kept server-side); local-model mode for zero egress.
- Retention & deletion: per-tenant retention policy; deletion cascades through regions, chunks, embeddings, claims,
  graph and caches, and is itself audited (tombstone + proof of deletion).
- Secrets: never in the repo; environment/secret manager; startup refuses insecure defaults in production.

### Ingestion hardening
- Content sniffing (not extension), size/page/pixel limits, PDF sanitisation (strip JS/embedded files, render-only),
  decompression-bomb guards, per-tenant quotas, parsing in a sandboxed worker with CPU/memory limits.

### Integrity & audit
- Append-only `AuditEvent` table, **hash-chained** (`prev_hash`) and periodically anchored (signed digest), so silent
  edits are detectable.
- Every claim/edge/finding change is an event with actor, reason and before/after references.

## 3. Security test suite (must pass in CI)
- Cross-tenant: for every endpoint and agent tool, a second tenant receives 404/empty (property-based over IDs).
- Marking enforcement: a `viewer` without `PII` clearance never sees marked regions in answers, snippets or graph labels.
- Prompt-injection corpus: attack success rate tracked per release (target ↓, never claimed 0).
- Upload fuzzing: malformed PDFs/images, zip bombs, polyglots.
- Agent escalation: agent attempts a write without approval → blocked and audited.
