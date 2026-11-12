"""Retrieval on PostgreSQL: full-text search column and pgvector embeddings for document chunks (ADR-0002)

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-13

* `document_chunks.chunk_tsv`: a stored generated `tsvector` (English configuration) with a GIN index, for
  full-text candidates. Always created.
* `document_chunks.embedding_vec vector(384)`: created only when the `vector` extension is installed or can be
  installed. A trigger keeps it equal to the JSON `embedding` text whenever that is written (384 values, otherwise
  NULL), so every write path (ingestion, re-embedding) stays in step without application changes. Existing rows are
  backfilled here when row-level security allows it; the application also fills any rows still missing at first use.
* No HNSW index: one shared approximate index degrades per-tenant recall under filtering (ADR-0002 amendment), and
  case-sized corpora are scanned exactly. A per-tenant partial index is the documented next step for large tenants.

Both embedding models in use produce 384 dimensions (MiniLM-L6 and the 384-d hashing fallback); queries always filter
on `embedding_model`, because vectors from different models are not comparable.
"""
import logging

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

log = logging.getLogger("alembic.runtime.migration")
DIM = 384

TRIGGER_FN = f"""
CREATE OR REPLACE FUNCTION minddoc_chunk_vector() RETURNS trigger AS $$
BEGIN
    NEW.embedding_vec := NULL;
    IF NEW.embedding IS NOT NULL THEN
        BEGIN
            IF json_array_length(NEW.embedding::json) = {DIM} THEN
                NEW.embedding_vec := NEW.embedding::vector({DIM});
            END IF;
        EXCEPTION WHEN others THEN
            NEW.embedding_vec := NULL;  -- a malformed vector never blocks the write
        END;
    END IF;
    RETURN NEW;
END
$$ LANGUAGE plpgsql
"""


def _vector_available(conn) -> bool:
    if conn.execute(sa.text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")).first():
        return True
    if not conn.execute(sa.text("SELECT 1 FROM pg_available_extensions WHERE name = 'vector'")).first():
        log.warning("pgvector is not available on this server: chunk vectors stay in JSON (in-process search)")
        return False
    try:
        with conn.begin_nested():
            conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))
        return True
    except sa.exc.DBAPIError as e:  # no privilege to create it
        log.warning("could not create the vector extension (%s): chunk vectors stay in JSON", e.__class__.__name__)
        return False


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    op.execute("ALTER TABLE document_chunks ADD COLUMN chunk_tsv tsvector "
               "GENERATED ALWAYS AS (to_tsvector('english', coalesce(chunk_text, ''))) STORED")
    op.execute("CREATE INDEX ix_document_chunks_chunk_tsv ON document_chunks USING gin (chunk_tsv)")
    if _vector_available(conn):
        op.execute(f"ALTER TABLE document_chunks ADD COLUMN embedding_vec vector({DIM})")
        op.execute(TRIGGER_FN)
        op.execute("CREATE TRIGGER trg_document_chunks_vector BEFORE INSERT OR UPDATE OF embedding "
                   "ON document_chunks FOR EACH ROW EXECUTE FUNCTION minddoc_chunk_vector()")
        # Backfill what row-level security lets the migration role see (all rows for a superuser); the application
        # fills the rest per tenant on first search.
        op.execute("UPDATE document_chunks SET embedding = embedding WHERE embedding IS NOT NULL")


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    op.execute("DROP TRIGGER IF EXISTS trg_document_chunks_vector ON document_chunks")
    op.execute("DROP FUNCTION IF EXISTS minddoc_chunk_vector()")
    op.execute("ALTER TABLE document_chunks DROP COLUMN IF EXISTS embedding_vec")
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_chunk_tsv")
    op.execute("ALTER TABLE document_chunks DROP COLUMN IF EXISTS chunk_tsv")
