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
