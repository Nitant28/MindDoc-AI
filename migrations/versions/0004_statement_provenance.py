"""Statement provenance: source type, consent reference, payload hash, schema version; per-transaction source ids

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-11

Needed for Account Aggregator imports (ADR-0015): a statement records where it came from (`pdf_text` or
`aa_deposit`), the consent artefact reference supplied by the customer, the SHA-256 of the imported payload and the
ReBIT schema version; each transaction keeps its value date, reference, transaction id and mode. Additive only.
"""
import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("statements", sa.Column("source", sa.String(), nullable=False, server_default="pdf_text"))
    op.add_column("statements", sa.Column("source_ref", sa.String(), nullable=True))
    op.add_column("statements", sa.Column("payload_sha256", sa.String(64), nullable=True))
    op.add_column("statements", sa.Column("schema_version", sa.String(), nullable=True))
    op.add_column("statement_txns", sa.Column("value_date", sa.Date(), nullable=True))
    op.add_column("statement_txns", sa.Column("reference", sa.String(), nullable=True))
    op.add_column("statement_txns", sa.Column("external_id", sa.String(), nullable=True))
    op.add_column("statement_txns", sa.Column("mode", sa.String(), nullable=True))


def downgrade() -> None:
    for col in ("mode", "external_id", "reference", "value_date"):
        op.drop_column("statement_txns", col)
    for col in ("schema_version", "payload_sha256", "source_ref", "source"):
        op.drop_column("statements", col)
