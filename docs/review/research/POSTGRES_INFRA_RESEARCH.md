# PostgreSQL, Alembic and asynchronous ingestion: infrastructure research

> Deliverable G input. Research date: **2026-11-10**. Every external claim has a link and a tag:
> **[verified]** = read on the linked primary page on the date above; **[unverified]** = secondary source only,
> or the page could not be read. Prices and limits change often; they are recorded as read on 2026-11-10.
> GitHub licence and release data come from the GitHub REST API (`/repos/{owner}/{repo}` and `/releases/latest`) on the
> same date.

Current state of MindDoc AI 2.1.0 (from the repo): SQLite via SQLAlchemy 2 with an auto-add-column migrator
(`app/database/models.py`), vectors stored as JSON text in `document_chunks.embedding`, a per-tenant in-memory
NumPy dense + BM25 index (`app/ml/retrieval.py`), ingestion run inside the upload request
(`app/services/ingestion.py`), one free Render Docker web service in Oregon with no disk (`render.yaml`).

## 1. PostgreSQL 18

**Release and support.** PostgreSQL 18.0 was released on **2025-09-25**
([release notes](https://www.postgresql.org/docs/release/18.0/)) **[verified]**. The current minor is **18.6**, and 18 is
supported until **2030-11-14** ([versioning policy](https://www.postgresql.org/support/versioning/)) **[verified]**.
PostgreSQL 19 is not final yet: the same page announces "PostgreSQL 19 RC 1" on 2026-10-15 **[verified]**. Target 18 now;
plan a move to 19 in 2027 once extensions (pgvector, btree_gist) and hosts support it.

Features that matter to MindDoc (all from the [18.0 release notes](https://www.postgresql.org/docs/release/18.0/) unless
another link is given):

| Feature | What shipped | Relevance | Tag |
|---|---|---|---|
| Asynchronous I/O | New AIO subsystem; backends can "queue multiple read requests". Controlled by `io_method`; new view `pg_aios`. It helps "sequential scans, bitmap heap scans, vacuums, and other operations". | Faster scans and vacuum. pgvector only adds AIO for its indexes in the unreleased 0.9.0 (§2), so expect little for HNSW queries or the job queue. Do not count on it in capacity plans. | **[verified]** |
| `uuidv7()` | Built-in UUID v7 generator; values are "temporally sortable". `uuidv4()` alias added. | Time-ordered keys keep B-tree inserts local. Fits DATA_MODEL's ULID ids: use native `uuid` + `uuidv7()` instead of ULID strings. Note that deterministic, content-derived ids (DATA_MODEL §1.6) still need hashing (e.g. UUID v5 or a hash), not v7. | **[verified]** |
| Temporal keys | `PRIMARY KEY` / `UNIQUE` with `WITHOUT OVERLAPS` on the **last** column; `FOREIGN KEY (..., PERIOD col)` | Declarative "no two versions of the same claim overlap in valid time" and "a relationship's period is covered by its entity's period". See limits below. | **[verified]** |
| Virtual generated columns | Generated columns are now **virtual by default**; `STORED` keeps the old behaviour. | Cheap derived columns (e.g. `is_current`). See limits below. | **[verified]** |
| OAuth authentication | New `oauth` method in `pg_hba.conf`, needs a validator library (`oauth_validator_libraries`) and a libcurl build. | Not needed: the app connects with its own role. Useful later for human DBA access via SSO on self-hosted installs. | **[verified]** |
| `OLD`/`NEW` in `RETURNING` | `INSERT/UPDATE/DELETE/MERGE ... RETURNING old.*, new.*`. | Write a history row or outbox payload from one statement (before/after image) without a trigger. | **[verified]** |
| B-tree skip scan | Multi-column B-tree indexes usable without a filter on the leading column. | Helps `(tenant_id, ...)` composite indexes used without `tenant_id` (admin/ops queries). | **[verified]** |
| AFTER-trigger role | AFTER triggers now run as the role that queued the event. | Matters for RLS + audit triggers: behaviour differs from PG ≤17. | **[verified]** |
| Smaller items | `NOT ENFORCED` CHECK/FK constraints; `log_lock_failures`; data checksums on by default; MD5 passwords deprecated. | Staged constraints in migrations; lock diagnostics (no change to `SKIP LOCKED`); use SCRAM on self-hosted installs. | **[verified]** |

**Temporal constraint details and limits** (from [CREATE TABLE, PG18](https://www.postgresql.org/docs/18/sql-createtable.html)) **[verified]**:

- The `WITHOUT OVERLAPS` column must be a **range or multirange** type (`tstzrange`, `daterange`). **Empty ranges are not
  allowed.**
- The other key columns (e.g. `tenant_id`, `claim_id`) need GiST equality support. For scalar types this means the
  **`btree_gist` extension**, which the docs call "the expected way to use this feature".
- The constraint is enforced with a **GiST index**; `UNIQUE (id, valid_at WITHOUT OVERLAPS)` behaves like
  `EXCLUDE USING GIST (id WITH =, valid_at WITH &&)`.
- A `PERIOD` foreign key passes if the referenced rows' periods, combined, **fully cover** the referencing row's period.
  The referenced table must have a `WITHOUT OVERLAPS` PK or unique key.
- **Only `NO ACTION` is supported** for temporal foreign keys: the docs mark `RESTRICT`, `CASCADE`, `SET NULL` and
  `SET DEFAULT` as "not supported" for them.
- `UPDATE/DELETE ... FOR PORTION OF` (automatic splitting of periods) is **not** in PG18, nor in the PG19 RC docs
  (§8.1). Period splitting must be done in application code.
- On partitioned tables, the partition key columns must be part of the constraint and compared with equality.

**Virtual generated column limits** ([CREATE TABLE, PG18](https://www.postgresql.org/docs/18/sql-createtable.html))
**[verified]**: the expression may use only built-in functions and types, must be immutable, may not reference other
tables or other generated columns. The page does not say whether virtual columns can be indexed; treat them as
"not indexable" and use `STORED` for anything you filter on (e.g. a `system_current` flag).

## 2. pgvector

All facts from the [pgvector README](https://github.com/pgvector/pgvector) and
[CHANGELOG](https://github.com/pgvector/pgvector/blob/master/CHANGELOG.md), read 2026-11-10, unless noted.

- **Version and licence.** Latest release **0.8.7 (2026-10-01)**; 0.9.0 is unreleased and will add "asynchronous I/O for
  indexes" and drop Postgres 13 and 14 **[verified]**. The LICENSE file is the PostgreSQL-style licence ("Portions
  Copyright ... PostgreSQL Global Development Group") **[verified]**: permissive, fine for on-prem.
- **PG18 support.** Added in 0.8.1 (2025-09-04, "support for Postgres 18 rc1"); 0.8.2 fixed `EXPLAIN` output for PG18 and
  a **buffer overflow in parallel HNSW builds**; 0.8.3 fixed "possible index corruption with HNSW vacuuming" **[verified]**.
  Use **≥ 0.8.3**; the official image `pgvector/pgvector:0.8.7-pg18` exists
  ([Docker Hub](https://hub.docker.com/r/pgvector/pgvector)) **[verified]**.
- **Types and limits.** `vector` is 4 bytes per dimension + 8; `halfvec` is 2 bytes per dimension + 8. Both store up to
  16,000 dimensions, but **HNSW indexes `vector` up to 2,000 dims and `halfvec` up to 4,000** **[verified]**. MindDoc's
  MiniLM embeddings (384 dims) fit either; `halfvec(384)` halves storage and index size (776 vs 1,544 bytes per vector).
- **HNSW.** Use `halfvec_cosine_ops` (or an expression index `(embedding::halfvec(384))`). Query recall is controlled by
  `hnsw.ef_search` (default 40), which can be set per transaction with `SET LOCAL` **[verified]**.
- **Filtered search.** "Filtering is applied *after* the index is scanned": with a filter matching 10% of rows and default
  `ef_search` 40, "only 4 rows will match on average". Since 0.8.0, **iterative index scans** (`hnsw.iterative_scan =
  strict_order | relaxed_order`) keep scanning until enough rows pass the filter, bounded by `hnsw.max_scan_tuples`
  (default 20,000) **[verified]**. With `relaxed_order`, wrap in a `MATERIALIZED` CTE and re-sort (`ORDER BY distance + 0`
  on PG17+) **[verified]**.
- **Multitenancy.** The README warns that "sharing an approximate index between tenants means vectors from one tenant can
  affect recall (and speed) for other tenants", and recommends **list partitioning by tenant or separate tables**
  **[verified]**. For MindDoc's first years (few tenants, each with tens of thousands of chunks), the simplest correct
  choice is: **exact search** (no ANN index) using a B-tree on `(tenant_id, document_id)` while a tenant is small, and an
  HNSW index on a tenant partition once it grows. Exact search gives perfect recall and needs no build memory.
- **Build memory.** "Indexes build significantly faster when the graph fits into `maintenance_work_mem`"; a NOTICE appears
  when it no longer fits; "Do not set `maintenance_work_mem` so high that it exhausts the memory on the server"; parallel
  build workers default to 2 **[verified]**. On a 256 MB Render Basic database, keep `maintenance_work_mem` at about 64 MB
  and build indexes after bulk load. Rough sizing (estimate, not from a source): 100k chunks × `halfvec(384)` ≈ 78 MB of raw
  vectors plus HNSW neighbour lists, so an in-memory build of 100k chunks needs a 1 GB-class instance; anything smaller
  still builds, only slower.
- **Host versions.** Neon ships 0.8.6 on PG18 ([Neon](https://neon.com/docs/extensions/pg-extensions)) **[verified]**;
  RDS launched PG18 with 0.8.1 ([AWS](https://aws.amazon.com/about-aws/whats-new/2025/11/amazon-rds-postgresql-major-version-18/))
  **[verified]**; Render does not state a version ([Render](https://render.com/docs/postgresql-extensions)) **[verified]**.
  Check `extversion` at startup and refuse to build HNSW indexes below 0.8.3.

## 3. Lexical search in Postgres

### 3.1 Built-in full-text search is not BM25

The PG18 docs state that `ts_rank` and `ts_rank_cd` "do not use any global information" (no corpus-wide term rarity, i.e.
no IDF), and that ranking "can be expensive since it requires consulting the `tsvector` of each matching document"
([Controlling Text Search](https://www.postgresql.org/docs/18/textsearch-controls.html)) **[verified]**. Length
normalisation is available through a bit mask (e.g. `1` = divide by 1 + log length; `4` = cover-density extent distance,
`ts_rank_cd` only) **[verified]**. In short: FTS finds matches well (GIN index on `tsvector`), but ranks them worse than
BM25, especially for rare terms such as GSTINs, invoice numbers and party names.

### 3.2 BM25 extensions and their licences (GitHub API, 2026-11-10)

| Option | Licence | Latest release | Postgres support | Hosting reality | Verdict |
|---|---|---|---|---|---|
| ParadeDB [`pg_search`](https://github.com/paradedb/paradedb) (Tantivy) | **AGPL-3.0** **[verified]** | v0.26.6, 2026-11-08 **[verified]** | — | Neon marks `pg_search` **deprecated, "do not add it for new projects"** ([Neon extensions](https://neon.com/docs/extensions/pg-extensions)) **[verified]**; not on Render's list **[verified]** | **Reject** for an on-prem product (AGPL). |
| [VectorChord-bm25](https://github.com/supervc-stack/VectorChord-bm25) (`vchord_bm25`) | **Dual AGPLv3 or Elastic License v2** (README) **[verified]** | 0.3.0, 2025-12-15 **[verified]**; repo moved from `tensorchord` to `supervc-stack` | — | Not on Render or Neon lists **[verified]** | **Reject**: AGPL, and ELv2 forbids offering it as a managed service; also needs a separate tokenizer extension. |
| [VectorChord](https://github.com/supervc-stack/VectorChord) (`vchord`, vectors) | Licence not detected by GitHub (`NOASSERTION`) **[verified]**; same vendor's dual AGPL/ELv2 model assumed **[unverified]** | 1.1.1, 2026-02-28 **[verified]** | — | — | Not needed: pgvector covers vectors. |
| Tiger Data / Timescale [`pg_textsearch`](https://github.com/timescale/pg_textsearch) | **PostgreSQL licence** ("Postgres OSS licensed") **[verified]** | v1.5.1, 2026-10-02 **[verified]**; ~4,000 stars | "supports PostgreSQL 17 and 18" (README) **[verified]** | Requires `shared_preload_libraries` (README) **[verified]**, so only on hosts that ship it or self-hosted. Not on Render's or Neon's extension lists **[verified]**. | **Best BM25 option** for self-hosted/on-prem installs. Block-Max WAND top-k; `<@>` operator; partitioned indexes. README says combining Boolean filters with BM25 ranking is "not yet" fully supported and other conditions become post-filters **[verified]**, which matters for tenant filters. |

### 3.3 Recommendation

1. **Default (all hosts): built-in FTS + `pg_trgm`, fused with dense results by RRF in one SQL query.** A stored generated
   `tsvector` column (`english` config for prose plus `simple` config for identifiers), a GIN index, `websearch_to_tsquery`,
   and `ts_rank_cd(..., 1|4)`. Add a `pg_trgm` GIN index on an `identifiers` text column for fuzzy GSTIN/PAN/invoice
   matching. This runs on Render, Neon, Supabase, Aiven and RDS (`pg_trgm` confirmed on Render
   ([extensions](https://render.com/docs/postgresql-extensions)) **[verified]**).
2. **BM25 upgrade path: `pg_textsearch`** behind the same retrieval interface, enabled only where the host allows it
   (self-hosted Docker or on-prem). This is what ADR-0002's ablation R1 should compare against FTS.
3. **Keep the in-process BM25 class, but only as an evaluation baseline**, not as a production index. The current
   per-tenant NumPy index is process-local and becomes wrong as soon as there is a separate worker process (ADR-0002's own
   reason). A useful small-case trick: run Postgres FTS to get the top ~200 candidates, then re-score those candidates
   with the existing Python BM25 using per-tenant document-frequency stats kept in a small table. That gives BM25-quality
   ranking without an extension, and is cheap at MindDoc's scale (thousands, not millions, of chunks per tenant).
4. **Licence rule:** no AGPL/GPL/ELv2 components in the database image shipped to customer sites. pgvector,
   `pg_textsearch`, `pg_trgm` and `btree_gist` pass.

## 4. Hosting options and their real limits

All prices and limits read on **2026-11-10**. USD, excluding tax.

### 4.1 Render (the current host)

- **PostgreSQL 18 is available and is the default** for new Render Postgres databases since 2025-11-13
  ([Render changelog](https://render.com/changelog/postgresql-18-is-now-available-for-render-postgres-databases))
  **[verified]**.
- **pgvector is supported** ("`CREATE EXTENSION vector;`", PG13+), as are `btree_gist` and `pg_trgm`
  ([Render extensions](https://render.com/docs/postgresql-extensions)) **[verified]**. The page does not state the pgvector
  version, and does not list `pg_search`, `vchord`, `pgmq` or `pg_cron` **[verified: absent]**.
- **Free Postgres:** 1 GB storage, 256 MB RAM, 0.1 CPU, 100 connections; **expires 30 days after creation**, then a 14-day
  grace period before deletion; **no backups**; one free database per workspace
  ([Render free tier](https://render.com/docs/free), [pricing](https://render.com/pricing)) **[verified]**.
- **Paid Postgres entry:** Basic-256mb **$6/month** (0.1 CPU, 256 MB RAM, 100 connections); Basic-1gb **$19/month**
  (0.5 CPU, 1 GB); Pro-4gb $55/month. Storage is extra at **$0.30 per GB**. Point-in-time recovery window is 3 days on the
  Hobby workspace and 7 days on Pro and above ([pricing](https://render.com/pricing)) **[verified]**.
- **Free web service:** 512 MB RAM, 0.1 CPU; **spins down after 15 minutes without inbound traffic**, about one minute to
  wake; 750 instance hours per workspace per month; no disks; local files lost on redeploy, restart or spin-down; Render
  "may restart" it at any time ([Render free tier](https://render.com/docs/free)) **[verified]**.
- **Background workers cannot be free.** The free-tier page says "Other service types don't support Free instances"
  ([Render free tier](https://render.com/docs/free)) **[verified]**. The cheapest background worker is **Starter, $7/month,
  512 MB, 0.5 CPU**; Standard is $25/month, 2 GB, 1 CPU ([pricing](https://render.com/pricing)) **[verified]**.
- **Pre-deploy command (for migrations) is paid-only:** "available for paid web services, private services, and background
  workers", 30-minute timeout ([Render deploys](https://render.com/docs/deploys)) **[verified]**.
- **Workspace plans:** Hobby $0 + compute; Pro **$25/month** + compute ([pricing](https://render.com/pricing))
  **[verified]**.
- **Regions:** Oregon, Ohio, Virginia, Frankfurt, **Singapore**. **No India region**
  ([Render regions](https://render.com/docs/regions)) **[verified]**.

**Can the free web service run a background worker thread?** Technically yes: nothing forbids a thread or a second
process inside the same container. In practice the instance sleeps 15 minutes after the last *inbound HTTP request*, so a
long OCR job started by an upload keeps running only while the instance is awake; a job queued just before spin-down
stalls until the next request wakes it. With a durable job table this is safe (the lease expires and the job is retried),
but it is not reliable throughput. Do not keep pinging the service to keep it awake: it burns the 750 free hours and is
against the spirit of the free tier. Conclusion: **for the demo, run the worker as a thread in the web process with a
durable Postgres queue; for any pilot, pay for a separate worker.**

### 4.2 Comparison table

| Host | PG18? | pgvector? | Free tier and its limits | Cheapest paid | India (Mumbai) region? |
|---|---|---|---|---|---|
| **Render Postgres** | Yes, default | Yes, version not stated | 1 GB, **expires after 30 days**, no backups | $6/month + $0.30/GB | **No** (Singapore nearest) — all per §4.1 **[verified]** |
| **Neon** | Yes; supports 14–18 ([version policy](https://neon.com/docs/postgresql/postgres-version-policy)) **[verified]** | Yes, 0.8.6 on PG18 ([extensions](https://neon.com/docs/extensions/pg-extensions)) **[verified]** | 1 GB per project, 100 CU-hours per project, scale-to-zero after 5 min (cannot disable), no expiry stated ([pricing](https://neon.com/pricing)) **[verified]** | Launch: pay-as-you-go, no minimum, $0.106/CU-hour, $0.35/GB-month ([pricing](https://neon.com/pricing)) **[verified]** | **No**; nearest Singapore `aws-ap-southeast-1` ([regions](https://neon.com/docs/introduction/regions)) **[verified]** |
| **Supabase** | **Not found.** Latest 30 image releases are 15.x and 17.x only ([supabase/postgres releases](https://github.com/supabase/postgres/releases)) **[verified]** | Yes, with HNSW ([docs](https://supabase.com/docs/guides/database/extensions/pgvector)) **[verified]** | 500 MB DB, 500 MB RAM shared CPU, **paused after 1 week of inactivity**, 2 active projects ([pricing](https://supabase.com/pricing)) **[verified]** | Pro from $25/month incl. $10 compute credit (Micro, 1 GB) ([pricing](https://supabase.com/pricing)) **[verified]** | **Yes**, `ap-south-1` Mumbai ([regions](https://supabase.com/docs/guides/platform/regions)) **[verified]** |
| **Aiven** | Yes, default for new services; 18.6 ([changelog](https://aiven.io/changelog/d5a0877d-f713-44e6-acc2-42e90ccc982a)) **[unverified: search snippet]** | Yes, `vector` 0.8.7 on PG18 ([extension list](https://aiven.io/docs/products/postgresql/reference/list-of-extensions-for-each-version)) **[unverified: search snippet]** | 1 GB RAM, 1 GB storage, cannot choose cloud or region, may be shut down if unused ([pricing](https://aiven.io/pricing)) **[verified]** | Developer $5/month (1 GB RAM, 8 GB, non-production); Hobbyist from $12/month; Startup from $75/month ([pricing](https://aiven.io/pricing)) **[verified]** | **Yes** on paid plans: `aws-ap-south-1` Mumbai, `aws-ap-south-2` Hyderabad, `google-asia-south1` Mumbai, `google-asia-south2` Delhi, Azure Central/South India ([clouds](https://aiven.io/docs/platform/reference/list_of_clouds)) **[verified]**. Which regions the $5/$12 tiers allow was not checked (Hobbyist lists DigitalOcean, Google Cloud, OVH). |
| **Crunchy Bridge** | Third-party listing says PG14–18 ([FitGap](https://us.fitgap.com/products/015701/crunchy-bridge)) **[unverified]** | Not checked | No free tier; "hobby-0" with a $5 minimum charge ([calculator](https://www.crunchydata.com/pricing/calculator)) **[verified]** | Not found | Not found (clouds: AWS, Azure, GCP) **[verified for clouds only]** |
| **AWS RDS for PostgreSQL** | Yes, since 2025-11-14 starting at 18.1 ([AWS news](https://aws.amazon.com/about-aws/whats-new/2025/11/amazon-rds-postgresql-major-version-18/)) **[verified]** | Yes; 0.8.1 at launch, 0.8.2 from 18.4 ([RDS release notes](https://docs.aws.amazon.com/AmazonRDS/latest/PostgreSQLReleaseNotes/postgresql-versions.html)) **[unverified: search snippet]** | 12-month free tier for new accounts (not checked for 2026 terms) **[unverified]** | Not checked (instance + storage + backup) | **Yes**, Mumbai `ap-south-1` and Hyderabad `ap-south-2` exist; PG18 availability per region not checked **[unverified]** |
| **Self-host (Docker)** | Official `postgres:18.6` image ([Docker Hub](https://hub.docker.com/_/postgres)) **[verified]** | `pgvector/pgvector:0.8.7-pg18` image ([Docker Hub](https://hub.docker.com/r/pgvector/pgvector)) **[verified]** | Free software; you pay for the VM and run backups yourself | Any VM | Wherever the VM is (any Indian cloud or the customer's own data centre) |

Notes on the table:

- **pgvector version matters.** pgvector 0.8.2 fixed a **buffer overflow in parallel HNSW index builds**, and 0.8.3 fixed
  "possible index corruption with HNSW vacuuming" ([pgvector CHANGELOG](https://github.com/pgvector/pgvector/blob/master/CHANGELOG.md))
  **[verified]**. Require **pgvector ≥ 0.8.3** in production and check it at startup
  (`SELECT extversion FROM pg_extension WHERE extname='vector'`). RDS 18.1 shipped 0.8.1.
- **Data residency for Indian lenders.** Render and Neon have no Indian region. Supabase (Mumbai), Aiven (Mumbai,
  Hyderabad, Delhi), AWS RDS (Mumbai, Hyderabad) and self-hosting do. Whether a given lender *requires* in-India storage
  depends on its regulator and contract; this research did not verify RBI rules.
- **Supabase on PG17** would allow `btree_gist` exclusion constraints for temporal data (availability of `btree_gist`
  on Supabase not checked **[unverified]**), but not the `WITHOUT OVERLAPS` / `PERIOD` syntax, which is new in PG18.

## 5. Row-Level Security with SQLAlchemy and FastAPI

### 5.1 Facts from the Postgres docs

From [Row Security Policies, PG18](https://www.postgresql.org/docs/18/ddl-rowsecurity.html) **[verified]**:

- "Superusers and roles with the `BYPASSRLS` attribute **always bypass** the row security system."
- "Table owners normally bypass row security as well", unless the table has `ALTER TABLE ... FORCE ROW LEVEL SECURITY`.
- With RLS enabled and no policy, a **default-deny** policy applies.
- **Referential integrity checks** (PK, unique, FK) "always bypass row security", so a unique constraint can leak the
  existence of another tenant's value ("covert channel"). Fix: include `tenant_id` in every unique key
  (e.g. `UNIQUE (tenant_id, sha256)`, which DATA_MODEL already does for sources).
- Policy expressions run **before** user query conditions, except for **`LEAKPROOF`** functions. Simple policies that
  only look at the current row are "the simplest and best-performing case".
- `row_security = off` does not bypass RLS; it **raises an error** if a query would be filtered. Useful as a guard in
  `pg_dump`/backup jobs.

From [CREATE FUNCTION](https://www.postgresql.org/docs/18/sql-createfunction.html) **[verified]**: `LEAKPROOF` "can only be
set by the superuser", so it is **not available on most managed hosts** for your own functions. `STABLE` means the result
is constant "within a single table scan" for the same arguments; `current_setting()` qualifies.

From [System Administration Functions](https://www.postgresql.org/docs/18/functions-admin.html) **[verified]**:
`set_config(name, value, is_local)` with `is_local = true` applies "only during the current transaction";
`current_setting(name, true)` returns NULL instead of an error when the setting does not exist.

### 5.2 The safe pattern

1. **Three roles.** `minddoc_owner` (owns tables, runs Alembic, `NOLOGIN` or used only by migrations);
   `minddoc_app` (the API and workers: `LOGIN`, `NOSUPERUSER`, `NOBYPASSRLS`, not the owner, only DML grants);
   optional `minddoc_ops` with `BYPASSRLS` for audited support tasks. The AWS write-up stresses that the shared app login
   "must not be the table owner or have BYPASSRLS"
   ([AWS Database Blog](https://aws.amazon.com/blogs/database/multi-tenant-data-isolation-with-postgresql-row-level-security/))
   **[unverified: search summary]**. Managed hosts usually hand you an owner/admin role first; create the app role yourself.
2. **`ENABLE` and `FORCE ROW LEVEL SECURITY`** on every tenant table, so a mistaken owner connection still filters.
3. **Transaction-scoped tenant context.** Set it with `set_config('app.tenant_id', :tid, true)` at the start of every
   transaction, never with session-level `SET`. A session `SET` survives on a pooled connection and leaks to the next
   request; `SET LOCAL`/`is_local=true` reverts at commit or rollback. This holds with PgBouncer in transaction mode too.
4. **Fail closed on missing context.** After a transaction-local value ends, the custom setting reads back as an
   **empty string**, not NULL, on that connection; `''::uuid` then raises SQLSTATE 22P02
   ([DEV write-up](https://dev.to/wenceslaudev/postgres-rls-multi-tenancy-two-traps-that-silently-disable-your-policies-5gn8))
   **[unverified: blog, consistent with known behaviour; add a test]**. Use
   `NULLIF(current_setting('app.tenant_id', true), '')::uuid` so missing context matches no rows.
5. **Wrap the setting in a sub-select** so the planner evaluates it once per statement (an InitPlan) instead of per row:
   `USING (tenant_id = (SELECT app.current_tenant()))`. Supabase documents this `initPlan` effect and recommends "an index
   on every column your policies filter on" ([Supabase RLS](https://supabase.com/docs/guides/database/postgres/row-level-security))
   **[verified]**. Their performance page gives no before/after numbers
   ([Supabase RLS performance](https://supabase.com/docs/guides/database/postgres/row-level-security-performance))
   **[verified]**, so measure our own.
6. **Indexes lead with `tenant_id`** on every RLS table (`(tenant_id, id)`, `(tenant_id, source_id)`), and the HNSW/GIN
   search queries still add an explicit `WHERE tenant_id = :tid`. RLS is defence in depth, not the only filter; AWS's SaaS
   series makes the same point (explicit tenant predicates plus RLS) **[unverified: search summary]**.
7. **Avoid LEAKPROOF dependence.** Because only superusers can mark functions `LEAKPROOF`, keep policies to plain column
   comparisons with built-in operators (which are already leakproof for `=` on `uuid`/`int`) **[unverified: operator
   leakproof status not checked]**.

SQLAlchemy 2 hook (uses `SessionEvents.after_begin`, which fires "after a transaction is begun on a connection"
([SQLAlchemy ORM events](https://docs.sqlalchemy.org/en/20/orm/events.html)) **[verified]**):

```python
from sqlalchemy import event, text
from sqlalchemy.orm import Session

@event.listens_for(Session, "after_begin")
def _set_tenant(session, transaction, connection):
    tid = session.info.get("tenant_id")          # set by the FastAPI dependency from the JWT
    if tid is None:
        return                                    # policies see NULL -> zero rows (fail closed)
    connection.execute(text("SELECT set_config('app.tenant_id', :t, true)"), {"t": str(tid)})
```

```sql
CREATE FUNCTION app.current_tenant() RETURNS uuid LANGUAGE sql STABLE
  AS $$ SELECT NULLIF(current_setting('app.tenant_id', true), '')::uuid $$;
ALTER TABLE claim ENABLE ROW LEVEL SECURITY;
ALTER TABLE claim FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON claim TO minddoc_app
  USING (tenant_id = (SELECT app.current_tenant()))
  WITH CHECK (tenant_id = (SELECT app.current_tenant()));
```

Workers must set the tenant per job (each job row carries `tenant_id`) inside the job's transaction. Cross-tenant
housekeeping (the dispatcher that claims jobs from all tenants) runs either on a non-RLS `job` table or as a
`SECURITY DEFINER` function owned by `minddoc_owner` with a pinned `search_path`.

### 5.3 Testing RLS

- A pytest fixture connects as `minddoc_app` (never the owner), creates tenants A and B, writes rows as A, and asserts
  that B sees zero rows for `SELECT`, gets zero rows affected for `UPDATE`/`DELETE`, and gets an error for `INSERT` with
  A's `tenant_id` (`WITH CHECK`).
- A "no context" test asserts zero rows (not an exception) when `app.tenant_id` was never set and after a previous
  transaction on the same pooled connection set it.
- A schema test queries `pg_class.relrowsecurity` and `relforcerowsecurity` and fails if any table with a `tenant_id`
  column lacks either flag, and asserts the app role has `rolbypassrls = false` and is not a table owner.

## 6. Job queue and transactional outbox in Postgres

### 6.1 Core facts

- `SKIP LOCKED` "can be used to avoid lock contention with multiple consumers accessing a queue-like table", and is "not
  suitable for general purpose work" because it gives an inconsistent view
  ([SELECT, PG18](https://www.postgresql.org/docs/18/sql-select.html)) **[verified]**. Use it only in the claim query.
- `NOTIFY` inside a transaction is delivered **only on commit**; payload must be under 8000 bytes; the queue (8 GB) can fill
  if a listener sits in a long transaction, and then `NOTIFY` fails at commit; identical notifications in one transaction
  are folded ([NOTIFY, PG18](https://www.postgresql.org/docs/18/sql-notify.html)) **[verified]**. So NOTIFY is a wake-up
  hint, never the source of truth.
- Committing a transaction that issued `NOTIFY` takes a **global lock**, which serialised commits at high write rates in
  Recall.ai's production system ([Recall.ai](https://recall.ai/blog/postgres-listen-notify-does-not-scale))
  **[unverified: search summary]**. At MindDoc's expected rate (well under ADR-0003's 200 events/s) this is acceptable;
  send one NOTIFY per transaction at most, or poll.
- `LISTEN` is bound to a server session, so it needs a **direct (non-pooled or session-mode) connection**; PgBouncer in
  transaction mode breaks it (general Postgres behaviour; the NOTIFY page does not discuss poolers) **[unverified]**.

### 6.2 Pattern (if built in-house)

```sql
CREATE TABLE job (
  id uuid PRIMARY KEY DEFAULT uuidv7(),
  tenant_id uuid NOT NULL, kind text NOT NULL, payload jsonb NOT NULL,
  idempotency_key text NOT NULL,                       -- sha256(type|subject|producer_version|input_hash)
  state text NOT NULL DEFAULT 'queued',                -- queued|running|succeeded|failed|dead
  priority smallint NOT NULL DEFAULT 0,
  run_after timestamptz NOT NULL DEFAULT now(),
  attempts int NOT NULL DEFAULT 0, max_attempts int NOT NULL DEFAULT 5,
  locked_by text, lease_until timestamptz, last_error text,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, kind, idempotency_key)
);
CREATE INDEX job_ready ON job (priority DESC, run_after) WHERE state = 'queued';

-- claim (one statement, one short transaction)
UPDATE job SET state='running', attempts=attempts+1, locked_by=:worker, lease_until=now()+interval '5 minutes'
WHERE id IN (SELECT id FROM job WHERE state='queued' AND run_after <= now()
             ORDER BY priority DESC, run_after FOR UPDATE SKIP LOCKED LIMIT 1)
RETURNING *;
```

- **Lease / visibility timeout:** `lease_until`; the worker extends it (heartbeat) during long OCR. A reaper resets
  `running` jobs whose lease expired to `queued`. Do the work **outside** the claim transaction; commit results and mark
  `succeeded` in a second transaction.
- **Retries with backoff:** on failure set `run_after = now() + backoff[attempts]` (EVENT_CATALOG uses 1 s, 5 s, 30 s, 2 m,
  10 m) plus jitter; after `max_attempts` set `state='dead'` (the dead-letter queue is a state, not a second table).
- **Idempotency:** the unique `(tenant_id, kind, idempotency_key)` makes enqueue an upsert (`ON CONFLICT DO NOTHING`); the
  handler writes with deterministic IDs and records `processed(event_id)` in the same transaction as its writes, as
  EVENT_CATALOG §4 already specifies.
- **Fairness:** per-tenant concurrency limits by counting `running` rows per tenant in the claim query, or by claiming
  round-robin over tenants.
- **Wake-up:** `NOTIFY job_ready` in the enqueue transaction; workers `LISTEN` on a dedicated direct connection and also
  poll every few seconds as a fallback.
- **Retention:** delete or partition old `succeeded` rows; dead rows are kept for the DLQ page.

**Outbox simplification.** When the job table lives in the **same database** as the state it reacts to, inserting the job
row in the business transaction *is* the transactional outbox: both commit or neither does. ADR-0003's two hops
(outbox row → dispatcher → job row) are only needed when the consumer is outside Postgres (Kafka later). Recommended: write
`job` rows directly now, and add an `outbox` table plus relay only when Step B (Kafka) starts. If the team wants the outbox
now for event history/replay, make the dispatcher the only writer of `job` and keep the outbox append-only.

### 6.3 Libraries (GitHub API, read 2026-11-10)

| Library | Licence | Latest release | Python | Model | Fit for "job table + outbox" |
|---|---|---|---|---|---|
| [Procrastinate](https://github.com/procrastinate-org/procrastinate) | MIT | 3.10.0, 2026-09-23 | Python 3.10+, sync and async, PostgreSQL 13+ ("periodic tasks, retries, arbitrary task locks") | Own tables, LISTEN/NOTIFY, worker heartbeats; stalled jobs are found via heartbeat and retried by a periodic task you write ([docs](https://procrastinate.readthedocs.io/en/stable/howto/production/retry_stalled_jobs.html)) | **Good.** Mature, Postgres-only. Check that `defer` can share the app's SQLAlchemy transaction (not verified: SQLAlchemy how-to page returned 404). |
| [PGQueuer](https://github.com/janbjorge/pgqueuer) | MIT | **v2.0.0, 2026-11-09** (major release one day old) | Python 3.11+, PostgreSQL 14+, asyncpg/psycopg | `FOR UPDATE SKIP LOCKED` claim, LISTEN/NOTIFY wake-up with polling fallback | Good design, but async-first and just went to 2.0; wait for 2.0.x to settle. |
| [Oban for Python (oban-py)](https://github.com/oban-bg/oban-py) | Apache-2.0 | v0.7.0, 2026-10-22 (pre-1.0) | Python 3.12+, PostgreSQL 14+, asyncio-native | Port of Elixir Oban: unique jobs, retries with backoff, orphan rescue, keeps job history; a paid "Oban Pro" exists | Promising, pre-1.0; repo has ~300 stars. Watch, do not adopt yet. |
| [pgmq](https://github.com/pgmq/pgmq) (formerly Tembo) | PostgreSQL licence | v1.13.1, 2026-10-20 | Python client [pgmq-py](https://github.com/pgmq/pgmq-py) | SQS-like queue: visibility timeout, archive instead of delete; "Supported on Postgres 14-18"; installs as an extension **or as plain SQL** for hosts without the extension | A queue primitive, not a job framework (no retry policy/scheduling). SQL-only install works on Render/Neon. Reasonable if we want SQS semantics and write our own runner. |
| [Hatchet](https://github.com/hatchet-dev/hatchet) | MIT | v0.114.2, 2026-10-26 | Python SDK | A separate orchestration **engine/server** that uses Postgres for durability; DAGs, rate limits, fair scheduling | **Overkill** for one engineer: another service to run and pay for. |
| [River](https://github.com/riverqueue/river) | MPL-2.0 | v0.51.2, 2026-11-09 | Go workers only; the Python package is **insert-only** ([riverqueue-python](https://github.com/riverqueue/riverqueue-python)) | Transactional enqueue in Postgres | **Does not fit** (Go runtime required). |
| [Chancy](https://github.com/TkTech/chancy) | MIT | v0.26.0, 2026-10-14 | Python | Postgres-backed job queue | Small project (~290 stars); not evaluated further. |

All licences above are permissive (MIT, Apache-2.0, PostgreSQL, MPL-2.0 file-level copyleft) **[verified via GitHub API
`spdx_id`]**; none is AGPL/GPL.

**Build vs adopt.** The core is ~200 lines of SQL and Python, and MindDoc needs things libraries handle differently:
tenant-scoped RLS context per job, idempotency keys from EVENT_CATALOG, a DLQ UI, per-tenant fairness, and later an outbox →
Kafka relay. Recommendation: **build a thin in-house job table** (pattern above) behind a small `jobs` interface, and keep
**Procrastinate** as the fallback if the in-house version grows past a few hundred lines or needs cron-like scheduling.

## 7. Alembic

**Versions.** Alembic **1.20.1** (released 2026-10-22, MIT) ([GitHub](https://github.com/sqlalchemy/alembic),
[docs](https://alembic.sqlalchemy.org/en/latest/autogenerate.html)) **[verified]**. `pgvector` Python package **0.5.1**
(MIT) provides SQLAlchemy types `VECTOR`, `HALFVEC`, `BIT`, `SPARSEVEC` and HNSW `Index(..., postgresql_using='hnsw')`
examples ([pgvector-python](https://github.com/pgvector/pgvector-python)) **[verified]**.

### 7.1 What autogenerate does not do

From [Alembic autogenerate docs](https://alembic.sqlalchemy.org/en/latest/autogenerate.html) **[verified]**:

- Detects: table and column add/remove, nullability, basic index, named-unique and FK changes. Column type changes are on by
  default; server defaults and named CHECK constraints are opt-in.
- **Cannot detect:** table renames, column renames, anonymously named constraints, some Enum cases.
- **Not yet:** sequences, and free-standing constraint changes including **PRIMARY KEY and EXCLUDE**. So temporal
  `WITHOUT OVERLAPS` keys and `EXCLUDE USING gist` constraints must be written by hand.
- The page does not mention **RLS policies, extensions, functions or triggers**; it points to the third-party
  `alembic_utils` for functions, views and triggers.

[`alembic_utils`](https://olirice.github.io/alembic_utils/) supports "functions, views, materialized views, triggers, and
policies" **[verified]**, MIT, PyPI 0.8.8, but the repo's last push was **2025-04-10**
([GitHub API](https://github.com/olirice/alembic_utils)) **[verified]**: low activity. Recommendation: **do not depend on
it**. Write these as explicit `op.execute()` blocks in hand-written migrations:

| Object | How |
|---|---|
| Extensions (`vector`, `btree_gist`, `pg_trgm`) | `op.execute("CREATE EXTENSION IF NOT EXISTS vector")` in the first migration; on managed hosts the migration role must be allowed to create them. |
| `ENABLE`/`FORCE ROW LEVEL SECURITY`, `CREATE POLICY` | Hand-written per table; a CI test (section 5.3) catches tables that were missed. |
| Functions (`app.current_tenant()`), triggers (audit hash chain) | `op.execute()` with `CREATE OR REPLACE`; keep the SQL in versioned files under `migrations/sql/`. |
| Temporal PK/UNIQUE `WITHOUT OVERLAPS`, `EXCLUDE`, `PERIOD` FKs | Hand-written `ALTER TABLE ... ADD CONSTRAINT`. Tell autogenerate to ignore them via `include_object` so it does not try to drop them. |
| HNSW / GIN indexes | `op.create_index(..., postgresql_using='hnsw', postgresql_with={'m':16,'ef_construction':64}, postgresql_ops={...})`; use `CREATE INDEX CONCURRENTLY` (in an `autocommit_block()`) once tables are large. |
| Roles and grants | Not in migrations (they are cluster-level). A separate idempotent `bootstrap.sql` run by an admin. |

### 7.2 Moving the existing SQLite data

The current app has no Alembic history and an ad-hoc column auto-adder. A clean path:

1. **Baseline revision** = the target Postgres schema (not the SQLite one). Remove the `ALTER TABLE` auto-migrator when
   Postgres becomes the default.
2. **One-off copy script** (Python, SQLAlchemy, two engines): read SQLite tables in primary-key order and bulk-insert into
   Postgres with type conversion:
   - `*_json` TEXT columns → `jsonb` (`json.loads` in Python, or `CAST(:v AS jsonb)`).
   - `document_chunks.embedding` TEXT (JSON list) → `halfvec(384)`. pgvector's text input format is `'[1,2,3]'`
     ([pgvector README](https://github.com/pgvector/pgvector)) **[verified]**, the same shape as a JSON array, so
     `CAST(:v AS halfvec)` usually works directly; whether it accepts the spaces Python's `json.dumps` writes was not
     tested **[unverified]**: normalise with `json.dumps(v, separators=(',', ':'))` to be safe.
   - Integer ids → keep as `bigint` for v2 tables, then **reset sequences** (`setval`) after the copy; new evidence-model
     tables use `uuid DEFAULT uuidv7()`.
   - `DateTime` naive UTC → `timestamptz` (attach UTC explicitly).
3. Verify row counts and a checksum per table, then re-embed if the embedding model changes.
4. Since Render's free disk is wiped on each deploy (`render.yaml` comment), the hosted demo has no data worth copying;
   the copy script matters for local and on-prem installs.

### 7.3 Running migrations on deploy

- Render's **pre-deploy command is for paid services only** (30-minute timeout)
  ([Render deploys](https://render.com/docs/deploys)) **[verified]**. On a paid plan: `preDeployCommand: alembic upgrade
  head`.
- On the **free** plan: run `alembic upgrade head` in the container start command before `uvicorn`, guarded by a Postgres
  advisory lock (`SELECT pg_advisory_lock(<const>)` in `env.py`) so two starting processes cannot migrate at once. Fail
  the start if the migration fails (the health check then keeps the old deploy).
- Only expand-then-contract migrations (add columns/tables, backfill, switch reads, drop later), because the old and new
  versions run side by side during a zero-downtime deploy.

### 7.4 Testing migrations in CI

- Run against a Postgres service container (section 9): `alembic upgrade head`, then `alembic downgrade base` (or at
  least `-1`), then `upgrade head` again.
- Run `alembic check` (fails if models and migrations differ; command exists in recent Alembic) **[unverified: command not
  re-checked on 1.20 docs]** with the `include_object` filter so hand-written constraints are ignored.
- Seed a v2-shaped SQLite file and run the copy script in CI once, so the migration path stays tested.

## 8. Bitemporal modelling in Postgres

### 8.1 Building blocks (all verified on postgresql.org)

- **Range types** `tstzrange` / `daterange`, half-open `[from, to)`; an omitted upper bound means "until further notice"
  (`[2026-01-01,)`), tested with `upper_inf()`. GiST indexes accelerate `&&`, `@>`, `<@` and friends
  ([Range Types](https://www.postgresql.org/docs/18/rangetypes.html)) **[verified]**.
- **Exclusion constraints** `EXCLUDE USING GIST (key WITH =, period WITH &&)`, with `btree_gist` for the scalar part
  ([Range Types §8.17.10](https://www.postgresql.org/docs/18/rangetypes.html)) **[verified]**.
- **PG18 `WITHOUT OVERLAPS` / `PERIOD`** (section 1): nicer syntax for the same thing, but **only one range column per
  key** (the last column), no empty ranges, and temporal FKs support only `NO ACTION` **[verified]**.
- **`UPDATE/DELETE ... FOR PORTION OF` is not available.** The UPDATE reference pages for
  [18](https://www.postgresql.org/docs/18/sql-update.html), [19 (RC)](https://www.postgresql.org/docs/19/sql-update.html)
  and [devel](https://www.postgresql.org/docs/devel/sql-update.html) contain no "PORTION" text (checked 2026-11-10)
  **[verified]**. A Better Stack guide claiming PG18 "added FOR PORTION OF"
  ([Better Stack](https://betterstack.com/community/guides/databases/postgres-temporal-constraints/)) is therefore wrong
  **[verified: contradicted by docs]**. Period splitting stays in application code.

### 8.2 Recommended pattern for MindDoc

DATA_MODEL already has `recorded_at` / `retracted_at` (system time) and `qualifiers.valid_from/valid_to` (valid time)
on claims. Make them first-class columns:

```sql
CREATE TABLE claim_version (
  tenant_id uuid NOT NULL,
  claim_id  uuid NOT NULL,                       -- stable identity of the assertion
  version_id uuid NOT NULL DEFAULT uuidv7(),
  ...,                                            -- subject, predicate, object, modality, status, extractor_version
  valid_period  tstzrange NOT NULL DEFAULT '(,)', -- unknown validity = unbounded, never empty
  recorded_at   timestamptz NOT NULL DEFAULT now(),
  retracted_at  timestamptz,                     -- NULL = current belief
  system_period tstzrange GENERATED ALWAYS AS (tstzrange(recorded_at, retracted_at)) STORED,
  PRIMARY KEY (version_id),
  -- one current belief per claim per valid-time slice (partial exclusion constraint)
  EXCLUDE USING gist (tenant_id WITH =, claim_id WITH =, valid_period WITH &&) WHERE (retracted_at IS NULL)
);
CREATE INDEX claim_current ON claim_version (tenant_id, claim_id) WHERE retracted_at IS NULL;   -- hot path
CREATE INDEX claim_asof    ON claim_version USING gist (tenant_id, system_period, valid_period); -- time travel
```

- **Single table, append-only**, rather than "current table + history table". Corrections close the old row
  (`SET retracted_at = now()`) and insert a new one in the same transaction; nothing else is ever updated. This matches
  ADR-0004's "append-only decisions" and EVENT_CATALOG replay scenario 1 ("old claims are retracted (system time), not
  deleted").
- **Why `EXCLUDE ... WHERE` and not `WITHOUT OVERLAPS`:** the rule is bitemporal (no overlap in valid time *among current
  rows*). `WITHOUT OVERLAPS` takes one range and no `WHERE` clause, so it cannot express this. Use `WITHOUT OVERLAPS` /
  `PERIOD` only for single-axis tables such as `relationship` validity or entity-identifier validity.
- **Important caveat:** different *claims* may legitimately overlap (two sources assert different directors for the same
  period). The constraint is per `claim_id` version chain, not per (subject, predicate). Contradictions are data, not
  constraint violations.
- **As-of queries:** "What did we believe on 1 March about who was director in 2024?" =
  `WHERE system_period @> '2026-03-01'::timestamptz AND valid_period && '[2024-01-01,2025-01-01)'`. Wrap the two common
  forms in SQL functions (`claims_as_of(ts)`, `claims_valid_at(ts)`) so application code never writes raw range logic.
- **Performance:** current-state reads use the partial B-tree (`retracted_at IS NULL`) and never touch history. GiST
  exclusion constraints make inserts slower than B-tree uniques; at ADR-0004's ~10M-claim revisit point, partition
  `claim_version` by `tenant_id` (list) or by `recorded_at` (range). No published benchmark for this exact schema was
  found; measure it.
- **`daterange` vs `tstzrange`:** documents usually give dates, not instants. Use `daterange` for valid time if all
  extractors emit day precision; keep `tstzrange` for system time.

### 8.3 Extensions: status

| Extension | Licence | Last activity (GitHub API) | Notes | Verdict |
|---|---|---|---|---|
| [temporal_tables](https://github.com/arkhipov/temporal_tables) (C) | BSD-2-Clause | last commit 2026-01-12, tag v1.2.2 **[verified]** | System-period versioning via trigger into a history table; README still says "requires PostgreSQL 9.2 or higher" **[verified]** | Not on Render's or Neon's extension lists **[verified]**; skip. |
| [nearform/temporal_tables](https://github.com/nearform/temporal_tables) | not detected (`NOASSERTION`) | last push 2025-11-24, tag v1.2.1 **[verified]** | PL/pgSQL rewrite "targeting AWS RDS, Google Cloud SQL, and Azure" where C extensions are not allowed **[verified]** | Usable anywhere, but we do not need a history table. |
| [periods](https://github.com/xocolatl/periods) | PostgreSQL | last commit 2025-10-08, tag v1.2.3 **[verified]** | SQL:2016 periods and `SYSTEM VERSIONING`; emulates `FOR PORTION OF` through a view with an `INSTEAD OF` trigger (table needs a primary key) **[verified: README]** | Not on Render/Neon lists **[verified]**; skip. |
| [pg_bitemporal](https://github.com/scalegenius/pg_bitemporal) | BSD-3-Clause | last push 2022-04-20 **[verified]** | Bitemporal library | Inactive; skip. |

Conclusion: **hand-roll with ranges, a partial exclusion constraint, PG18 temporal keys where they fit, and append-only
writes.** No temporal extension is needed or portable across hosts.

## 9. Testing against Postgres

- **GitHub Actions service containers** need a **Linux runner**; the documented setup is a `postgres` service with
  `pg_isready` health checks and port `5432:5432`
  ([GitHub Docs](https://docs.github.com/en/actions/tutorials/use-containerized-services/create-postgresql-service-containers))
  **[verified]**. The current `ci.yml` already uses `ubuntu-latest` and Python 3.11 (from the repo). Use the image
  `pgvector/pgvector:0.8.7-pg18` instead of plain `postgres` so `vector` is available
  ([Docker Hub](https://hub.docker.com/r/pgvector/pgvector)) **[verified]**.
- **testcontainers-python** v4.15.0 (2026-07-24, Apache-2.0)
  ([GitHub](https://github.com/testcontainers/testcontainers-python)) **[verified]** starts a throwaway Postgres from
  pytest. Good for local runs on a laptop with Docker; in CI the service container is simpler and faster to start.
- **Keep a SQLite path or not?** Recommendation: **no SQLite for anything that touches RLS, vectors, FTS, ranges or the
  job queue**, because none of these exist in SQLite and tests would pass on behaviour production never runs. Keep SQLite
  only for (a) pure unit tests that do not touch the DB and (b) the zero-dependency "try it locally" mode, behind a clear
  `DATABASE_URL` switch, until Postgres-only features land; then drop it. Today `tests/conftest.py` forces SQLite
  (`DATABASE_URL=sqlite:///...test.db`), so this is a real change to the test setup.
- **Speed tricks:** one database per test session, run `alembic upgrade head` once, wrap each test in a transaction
  rolled back at the end (SAVEPOINT pattern); mark tests that need commits (queue, NOTIFY, RLS-across-transactions) and
  give them a truncate-based fixture instead.
- **Must-have test suites:** RLS isolation (section 5.3), migration up/down (7.4), queue semantics (two workers never claim
  the same job; an expired lease is retried; idempotent re-delivery writes no duplicate rows, matching EVENT_CATALOG
  replay scenario 3), and a pgvector version check.

## 10. Recommendations

| Decision | Recommendation | Why (sections) |
|---|---|---|
| **(a) Hosting: free demo** | Render free web service (Oregon) **+ Neon Free Postgres 18 in `aws-us-west-2` (Oregon)**. Worker runs as a background thread/subprocess inside the web container, reading the Postgres job table. Migrations run in the start command under an advisory lock. | Render's free Postgres expires after 30 days with no backups; Neon Free has PG18, pgvector 0.8.6, 1 GB, no stated expiry, scale-to-zero after 5 minutes. Render's free tier has no workers and no pre-deploy command. Jobs simply pause while the instance sleeps and resume on wake-up (§4). |
| **(b) Hosting: first paying pilot in India** | Move compute and data to **one Indian region**. Default: **AWS Mumbai (`ap-south-1`)**: RDS for PostgreSQL 18 (minor with pgvector ≥ 0.8.3) plus the API and worker containers in the same region. Alternative: Aiven PostgreSQL 18 in `aws-ap-south-1` or `google-asia-south1` with compute on any Mumbai VM. For lenders that insist on on-prem: the same Docker Compose stack with `pgvector/pgvector:0.8.7-pg18`. | Render and Neon have no India region; Supabase has Mumbai but its images are still PG17 (no `WITHOUT OVERLAPS`/`PERIOD`). RDS and Aiven both run PG18 with pgvector and have Mumbai regions. RDS and Aiven prices for Mumbai were **not verified**; get quotes before committing. Budget at least a $7/month-class separate worker if staying on Render outside India (§4). |
| **RLS** | Separate non-owner `minddoc_app` role (`NOBYPASSRLS`); `ENABLE` + `FORCE ROW LEVEL SECURITY` on every tenant table; tenant set per transaction with `set_config('app.tenant_id', …, true)` from a SQLAlchemy `after_begin` hook; policies use `(SELECT app.current_tenant())` with `NULLIF(…, '')`; `tenant_id` leads every index and every unique key; queries still filter on `tenant_id` explicitly; CI tests prove isolation and fail-closed behaviour. | §5 |
| **Queue: build vs adopt** | **Build** a thin job table (`FOR UPDATE SKIP LOCKED`, lease + heartbeat, backoff, `dead` state, idempotency-key unique index, `NOTIFY` wake-up + polling). Insert jobs **directly in the business transaction**. Fall back to **Procrastinate** (MIT, 3.10.0, Sept 2026) if the home-grown version grows. Reject Hatchet (extra service), River (Go only), oban-py (pre-1.0, Python 3.12+ while CI uses 3.11), and wait on PGQueuer 2.0 (released one day before this research). | §6 |
| **Lexical search** | Built-in FTS (stored `tsvector`, GIN, `websearch_to_tsquery`, `ts_rank_cd`) + `pg_trgm` for identifiers, fused with dense results by RRF in SQL. Optional BM25 re-scoring of the FTS top-200 in Python using per-tenant document-frequency stats. `pg_textsearch` (PostgreSQL licence) is the BM25 option for self-hosted installs. **No ParadeDB `pg_search` (AGPL) or VectorChord-bm25 (AGPL/ELv2).** Keep the in-process BM25 class only as the evaluation baseline. | §3 |
| **Vectors** | `halfvec(384)`, pgvector ≥ 0.8.3 enforced at startup. Exact search per tenant while tenants are small; HNSW with `hnsw.iterative_scan` on a tenant partition when one grows; small `maintenance_work_mem` on small instances. | §2 |
| **Bitemporal** | One append-only `claim_version` table: `valid_period` range (never empty; `(,)` when unknown) + `recorded_at`/`retracted_at` with a stored `system_period`; partial `EXCLUDE USING gist (...) WHERE (retracted_at IS NULL)`; partial B-tree for current rows; as-of SQL functions. Use PG18 `WITHOUT OVERLAPS`/`PERIOD` only on single-axis tables. No temporal extension. Period splitting in application code (`FOR PORTION OF` does not exist in 18 or 19). | §8 |
| **Migrations and tests** | Alembic 1.20 with hand-written `op.execute()` for extensions, RLS, functions, triggers and temporal constraints (no `alembic_utils`); CI on `pgvector/pgvector:0.8.7-pg18` service container with upgrade/downgrade/upgrade, RLS, queue and migration-copy tests; SQLite kept only for DB-free unit tests and a temporary local "try it" mode. | §7, §9 |
| **IDs** | Native `uuid` with PG18 `uuidv7()` for new rows instead of ULID strings; content-derived deterministic IDs (DATA_MODEL §1.6) stay hash-based. | §1 |

## 11. Contradictions and tensions with the ADRs

1. **ADR-0003, outbox → dispatcher → job table.** When the job table is in the same database, writing the job row in the
   business transaction already gives the outbox guarantee. The extra outbox hop and dispatcher add a moving part with no
   benefit until Kafka (Step B). Suggest: jobs inserted directly now; outbox + relay introduced with Step B.
2. **ADR-0001/0003, "API process plus N worker processes" on today's hosting.** Render's free plan cannot run a
   background worker at all ("Other service types don't support Free instances"), and the free web service sleeps after
   15 minutes. The demo must run the worker in-process; real workers need a paid plan (Starter worker $7/month).
3. **ADR-0002, "benchmarked against a BM25 sidecar (ablation R1)".** The two well-known in-Postgres BM25 engines are
   AGPL (ParadeDB `pg_search`) or AGPL/ELv2 (VectorChord-bm25), both unacceptable for a product installed at customer
   sites, and neither is offered on Render or Neon (Neon has deprecated `pg_search`). The licence-clean comparator is
   `pg_textsearch` (self-host only) or Python BM25 re-scoring of FTS candidates. R1 should name these.
4. **ADR-0002, "pgvector (HNSW, halfvec)" as the default index.** pgvector's own README warns that one HNSW index shared
   across tenants hurts recall and speed for other tenants, and that filters are applied after the index scan. At current
   scale, exact per-tenant search is more accurate and cheaper; HNSW should be per tenant partition and need
   `iterative_scan`. The ADR should say so.
5. **ADR-0002, "PostgreSQL 18" vs hosting in India.** Of the managed hosts with a Mumbai region, Supabase is still on
   PG17, so choosing PG18 (and `WITHOUT OVERLAPS`) rules it out. The current host, Render, has no Indian region at all, so
   an Indian lender pilot means leaving Render (or accepting Singapore). The ADR does not mention hosting or residency.
6. **ADR-0002, "Alembic migrations" with the current deploy.** Render's pre-deploy command (the natural place for
   `alembic upgrade head`) is paid-only; on the free plan migrations must run at container start under an advisory lock.
7. **ADR-0002, RLS "defence in depth".** Consistent, with two cautions: `LEAKPROOF` is superuser-only, so it is not
   available for our own policy functions on managed hosts; and the managed host's default role is usually the table
   owner, which bypasses RLS unless `FORCE` is set and a separate app role is used.
8. **ADR-0004 (bitemporal), noted for completeness.** PG18's `WITHOUT OVERLAPS` covers one time axis only and
   `FOR PORTION OF` is absent from PG18 and PG19, so the bitemporal rule needs a partial `EXCLUDE` constraint and period
   splitting in application code. This is not a reason to change the ADR, but the implementation should not assume
   native bitemporal support.

Not contradicted: Postgres as system of record, one transaction across evidence + index + job rows, idempotent handlers
keyed by deterministic IDs, `SKIP LOCKED` consumption, retries with backoff and a DLQ, and Docker for local development.
