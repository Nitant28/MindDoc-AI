# ADR-0013 — Deployment topology per environment

**Status:** Accepted for dev and demo (owner mandate 2026-11-10); pilot host **Proposed** until pricing and data-residency
checks are complete.

**Context (verified 2026-11-10, `docs/review/research/POSTGRES_INFRA_RESEARCH.md`).** Render's free web service sleeps
after 15 minutes, has no disk, and cannot run background workers; Render free Postgres expires after 30 days with no
backups; Render and Neon have no India region; Supabase images are on PG 15/17; Aiven and AWS RDS offer PG18 in Mumbai.

**Decision.**

| Environment | Web | Worker | Database | Files |
|---|---|---|---|---|
| Development | uvicorn | separate process | Docker `pgvector/pgvector:0.8.7-pg18`, or a local PG18 + pgvector | local folder (content-addressed) |
| Demo | Render free web | embedded worker threads | Neon Free (PG18, pgvector) — needs the owner's Neon account | content-addressed store in the database for demo-size files, or S3-compatible bucket if configured |
| India pilot | paid container | separate worker | AWS RDS PG18 Mumbai (proposed; Aiven Mumbai or on-premise as fallbacks) | S3 Mumbai |

The embedded worker on a sleeping host is safe (leases and retries) but not throughput-reliable: demo only.

**Acceptance.** The same image runs in all three; configuration differs only by environment variables; health,
readiness and liveness endpoints exist; migrations run under an advisory lock at start when no pre-deploy hook exists.
