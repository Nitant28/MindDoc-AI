# ADR-0012 — Case (engagement) scoping inside tenants

**Status:** Accepted (owner mandate 2026-11-10)

**Context.** Today every user has a private tenant and all their documents form one workspace. Investigation work is
per engagement (a borrower, a vendor review) with its own team, period and sources; mixing unrelated engagements in one
graph produces false links.

**Decision.** `tenant` = organisation. Inside it, `case` groups sources (`case_source`, many-to-many), members
(`case_member` with roles lead / analyst / reviewer / viewer), graphs, findings and reports. Retrieval and chat can be
scoped to a case or to the whole tenant; analytics, discovery and findings are always case-scoped. Tenant isolation is
enforced by RLS (ADR-0002); case authorisation by application checks.

**Migration.** Existing documents become members of a default case per tenant ("General"), so current flows keep working.

**Acceptance.** A user who is not a member of a case cannot read its sources, findings or reports (API tests); RLS tests
remain per tenant.

## Implementation note 2026-11-14

Built in migration 0009 and `app/cases/access.py`. Choices made where the ADR was silent:
- The default "General" case needs no membership rows: every active member of the organisation uses it (admins as
  lead, members as analysts); explicit rows can raise a role. All other cases are explicit-membership only; tenant
  admins are **not** implicit members of them.
- A document is visible when any of its cases is visible; changing or deleting it needs analyst rights in every case
  that holds it; it cannot be removed from its last case. Tenant-wide views (graph, timeline, overview, evaluation,
  chat without a case) are filtered to the caller's visible documents. Query logs: members see their own, admins all.
- Organisation membership is by invitation link (no email is sent). `tenant_invites` is not under RLS (redeemed before a
  tenant context exists), like `users`. Acceptance test: `tests/test_cases.py`.
