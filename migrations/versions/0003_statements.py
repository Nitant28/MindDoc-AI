"""Bank statements: analysed statement, transactions and reconciliation checks, all under RLS (ADR-0011, ADR-0010)

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-11

Amounts are integer minor units (BIGINT) with an ISO currency on the statement. One `statements` row per document
holds the latest engine run (re-analysis replaces it). `statement_txns.box_*` is the row's position on its page in
tenths of a point (top-left origin), so a transaction can be shown on the original page.
"""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

ROLE = "minddoc_app"
TENANT_EXPR = "NULLIF(current_setting('app.tenant_id', true), '')::integer"
TABLES = ["statements", "statement_txns", "reconciliation_checks"]


def upgrade() -> None:
    op.create_table(
        "statements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("engine_version", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("ifsc", sa.String(), nullable=True),
        sa.Column("account_masked", sa.String(), nullable=True),
        sa.Column("opening_minor", sa.BigInteger(), nullable=True),
        sa.Column("closing_minor", sa.BigInteger(), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("pages", sa.Integer(), nullable=True),
        sa.Column("n_txns", sa.Integer(), nullable=False),
        sa.Column("total_debit_minor", sa.BigInteger(), nullable=False),
        sa.Column("total_credit_minor", sa.BigInteger(), nullable=False),
        sa.Column("failed_checks", sa.Integer(), nullable=False),
        sa.Column("inferred_directions", sa.Integer(), nullable=False),
        sa.Column("warnings", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("document_id", name="uq_statement_document"),
    )
    op.create_index("ix_statements_tenant_id", "statements", ["tenant_id"])

    op.create_table(
        "statement_txns",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("statement_id", sa.Integer(), sa.ForeignKey("statements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("txn_date", sa.Date(), nullable=False),
        sa.Column("narration", sa.Text(), nullable=True),
        sa.Column("debit_minor", sa.BigInteger(), nullable=False),
        sa.Column("credit_minor", sa.BigInteger(), nullable=False),
        sa.Column("balance_minor", sa.BigInteger(), nullable=True),
        sa.Column("page", sa.Integer(), nullable=False),
        sa.Column("box_x0", sa.Integer(), nullable=True),
        sa.Column("box_top", sa.Integer(), nullable=True),
        sa.Column("box_x1", sa.Integer(), nullable=True),
        sa.Column("box_bottom", sa.Integer(), nullable=True),
        sa.Column("direction_source", sa.String(), nullable=False),
        sa.Column("amount_raw", sa.String(), nullable=True),
        sa.Column("balance_raw", sa.String(), nullable=True),
        sa.UniqueConstraint("statement_id", "seq", name="uq_statement_txn_seq"),
    )
    op.create_index("ix_statement_txns_tenant_id", "statement_txns", ["tenant_id"])
    op.create_index("ix_statement_txns_statement_id", "statement_txns", ["statement_id"])
    op.create_index("ix_statement_txns_txn_date", "statement_txns", ["txn_date"])

    op.create_table(
        "reconciliation_checks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("statement_id", sa.Integer(), sa.ForeignKey("statements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scope", sa.String(), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column("expected_minor", sa.BigInteger(), nullable=True),
        sa.Column("observed_minor", sa.BigInteger(), nullable=True),
        sa.Column("hypotheses", sa.Text(), nullable=True),
    )
    op.create_index("ix_reconciliation_checks_tenant_id", "reconciliation_checks", ["tenant_id"])
    op.create_index("ix_reconciliation_checks_statement_id", "reconciliation_checks", ["statement_id"])

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


def downgrade() -> None:
    for t in reversed(TABLES):
        op.drop_table(t)
