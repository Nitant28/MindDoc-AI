# ADR-0003 — Job table + transactional outbox now; Kafka at a trigger

**Status:** Proposed

**Context.** We need async ingestion, retries, a dead-letter queue and visible lifecycle now. Kafka adds consumer
groups, replay and partitioned ordering — valuable once several independent consumers exist — at an operational cost.

**Decision.** Define every event contract now (`docs/architecture/EVENT_CATALOG.md`). Step A: outbox rows written in the
same transaction as state changes; a dispatcher moves them to a Postgres job table consumed with
`FOR UPDATE SKIP LOCKED`; handlers are idempotent, keyed by deterministic IDs. Step B (Kafka 4 in KRaft mode, single
broker in Docker Compose, outbox → Kafka relay) when ≥3 independent consumer groups need the same stream with replay,
or sustained load exceeds ~200 events/s.

**Alternatives.** Kafka from day one (no current fan-out to justify it); Celery + Redis (second stateful store, Redis
licence change); Redpanda (BSL).

**Consequences.** Producers never change when Kafka arrives; replay requirements are tested from the start.

**Revisit when.** Continuous discovery (layer L8) ships — expected to be the trigger.
