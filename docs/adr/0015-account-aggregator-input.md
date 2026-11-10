# ADR-0015 — Account Aggregator (ReBIT) data as a consent-scoped input

**Status:** Accepted (owner mandate 2026-11-10)

**Context.** Regulated lenders can receive bank data through the Account Aggregator framework as structured JSON;
CA and forensic firms cannot (AA only delivers to regulated financial-information users — D §2). The ReBIT deposit schema
(verified 2026-11-10) defines transactions with `type` (CREDIT/DEBIT), `mode`, `amount`, `currentBalance`,
`transactionTimestamp`, `valueDate`, `txnId`, `narration`, `reference`, and an account summary.

**Decision.** MindDoc **imports** AA FI data that the customer already holds (file upload of the decrypted FI JSON/XML,
or a later connector run by the regulated customer). MindDoc does **not** act as an FIU or AA, does not request consent
itself, and never treats the schema as access to bank records. Imported data maps onto `statement` / `statement_txn`
(`direction_source=column`, no bounding boxes), with provenance = consent artefact reference + payload hash, and runs the
same reconciliation. Schema version is recorded per payload.

**Acceptance.** Sample AA payloads (built from the published schema, synthetic values) import, reconcile, and show
provenance; payloads failing schema validation are rejected with a clear error.
