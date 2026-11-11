"""Claims with evidence: versioned TRANSFERRED_TO / RECEIVED_FROM assertions over statement rows (ADR-0004)

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-12

`claims` holds versions of a logical claim (`claim_key`). System time is `[recorded_at, superseded_at)`, and at most
one version per key is current: a partial unique index, portable to SQLite and PostgreSQL 16+. `claim_evidence`
copies the page region, so superseded versions keep resolving to the exact rows they relied on. Both tables are
under FORCE row-level security.
"""
import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

ROLE = "minddoc_app"
TENANT_EXPR = "NULLIF(current_setting('app.tenant_id', true), '')::integer"
TABLES = ["claims", "claim_evidence"]


def upgrade() -> None:
    op.create_table(
        "claims",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_key", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("subject_document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("subject_label", sa.String(), nullable=True),
        sa.Column("object_party_id", sa.Integer(), sa.ForeignKey("parties.id", ondelete="SET NULL"), nullable=True),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("valid_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("method", sa.String(), nullable=False),
        sa.Column("supersedes_id", sa.Integer(), sa.ForeignKey("claims.id"), nullable=True),
        sa.Column("recorded_at", sa.DateTime(), nullable=False),
        sa.Column("superseded_at", sa.DateTime(), nullable=True),
        sa.Column("supersede_reason", sa.String(), nullable=True),
    )
    op.create_index("ix_claims_tenant_id", "claims", ["tenant_id"])
    op.create_index("ix_claims_case_id", "claims", ["case_id"])
    op.create_index("ix_claims_claim_key", "claims", ["claim_key"])
    op.create_index("ix_claims_recorded_at", "claims", ["recorded_at"])
    op.create_index("ix_claims_superseded_at", "claims", ["superseded_at"])
    op.create_index("uq_claims_current_version", "claims", ["case_id", "claim_key"], unique=True,
                    postgresql_where=sa.text("superseded_at IS NULL"), sqlite_where=sa.text("superseded_at IS NULL"))

    op.create_table(
        "claim_evidence",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("claim_id", sa.Integer(), sa.ForeignKey("claims.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("statement_txn_id", sa.Integer(), nullable=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=True),
        sa.Column("page", sa.Integer(), nullable=True),
        sa.Column("seq", sa.Integer(), nullable=True),
        sa.Column("box_x0", sa.Integer(), nullable=True),
        sa.Column("box_top", sa.Integer(), nullable=True),
        sa.Column("box_x1", sa.Integer(), nullable=True),
        sa.Column("box_bottom", sa.Integer(), nullable=True),
        sa.Column("quote", sa.Text(), nullable=True),
        sa.Column("external_id", sa.String(), nullable=True),
    )
    op.create_index("ix_claim_evidence_tenant_id", "claim_evidence", ["tenant_id"])
    op.create_index("ix_claim_evidence_claim_id", "claim_evidence", ["claim_id"])
    op.create_index("ix_claim_evidence_document_id", "claim_evidence", ["document_id"])

    if op.get_bind().dialect.name != "postgresql":
        return
    for t in TABLES:
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {t} TO {ROLE}")
        op.execute(f"GRANT USAGE, SELECT ON SEQUENCE {t}_id_seq TO {ROLE}")
        op.execute(f"ALTER TABLE {t} ALTER COLUMN tenant_id SET DEFAULT {TENANT_EXPR}")
        op.execute(f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {t} FORCE ROW LEVEL SECURITY")
        op.execute(f"""CREATE POLICY tenant_isolation ON {t}
                       USING (tenant_id = (SELECT {TENANT_EXPR}))
                       WITH CHECK (tenant_id = (SELECT {TENANT_EXPR}))""")
    # claim versions are closed (superseded_at) but never otherwise edited or deleted by the application
    op.execute(f"REVOKE DELETE ON claims, claim_evidence FROM {ROLE}")
    op.execute(f"REVOKE UPDATE ON claim_evidence FROM {ROLE}")


def downgrade() -> None:
    op.drop_table("claim_evidence")
    op.drop_index("uq_claims_current_version", table_name="claims")
    op.drop_table("claims")
