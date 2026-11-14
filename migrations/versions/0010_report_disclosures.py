"""Disclosure copies of frozen reports (R8; third-party data withheld with reasons)

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-14

`report_disclosures`: one row per copy given to a recipient (for example the borrower under SBI v. Amit Iron, 2026).
The disclosed content is canonical JSON with its SHA-256 and the SHA-256 of the frozen report it came from;
`withheld_internal` keeps, for the issuer only, the values that were withheld. Under FORCE row-level security; the
application role cannot change or delete a disclosure once made.
"""
import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

ROLE = "minddoc_app"
TENANT_EXPR = "NULLIF(current_setting('app.tenant_id', true), '')::integer"


def upgrade() -> None:
    op.create_table(
        "report_disclosures",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("report_id", sa.Integer(), sa.ForeignKey("reports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("recipient", sa.String(), nullable=False),
        sa.Column("subjects", sa.Text(), nullable=False),
        sa.Column("withheld_internal", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("base_hash", sa.String(64), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_report_disclosures_tenant_id", "report_disclosures", ["tenant_id"])
    op.create_index("ix_report_disclosures_report_id", "report_disclosures", ["report_id"])
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute(f"GRANT SELECT, INSERT ON report_disclosures TO {ROLE}")
    op.execute(f"GRANT USAGE, SELECT ON SEQUENCE report_disclosures_id_seq TO {ROLE}")
    op.execute(f"REVOKE UPDATE, DELETE ON report_disclosures FROM {ROLE}")
    op.execute(f"ALTER TABLE report_disclosures ALTER COLUMN tenant_id SET DEFAULT {TENANT_EXPR}")
    op.execute("ALTER TABLE report_disclosures ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE report_disclosures FORCE ROW LEVEL SECURITY")
    op.execute(f"""CREATE POLICY tenant_isolation ON report_disclosures
                   USING (tenant_id = (SELECT {TENANT_EXPR}))
                   WITH CHECK (tenant_id = (SELECT {TENANT_EXPR}))""")


def downgrade() -> None:
    op.drop_table("report_disclosures")
