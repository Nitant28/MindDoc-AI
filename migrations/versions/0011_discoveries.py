"""Discovery ledger and party tags (R7; INVESTIGATION_ENGINE §5)

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-14

* `discovery_runs`: one row per detector run on a case (parameters and detector versions used, counts).
* `discoveries`: leads found by deterministic detectors. A stable key per pattern lets a re-run update the same row;
  the analyst's disposition (pursue / dismissed, with a reason) survives re-runs. A lead that a later run no longer
  finds is kept and marked, never deleted. A discovery is a lead for review, never a verdict.
* `party_tags`: an analyst's mark that a party is related to the subject (used by the end-use detector).
All three are under FORCE row-level security.
"""
import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None

ROLE = "minddoc_app"
TENANT_EXPR = "NULLIF(current_setting('app.tenant_id', true), '')::integer"
TABLES = ["discovery_runs", "discoveries", "party_tags"]


def upgrade() -> None:
    op.create_table(
        "discovery_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("params", sa.Text(), nullable=False),
        sa.Column("versions", sa.Text(), nullable=False),
        sa.Column("n_transactions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("n_found", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("n_new", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("run_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_discovery_runs_tenant_id", "discovery_runs", ["tenant_id"])
    op.create_index("ix_discovery_runs_case_id", "discovery_runs", ["case_id"])
    op.create_table(
        "discoveries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("discovery_key", sa.String(64), nullable=False),
        sa.Column("detector", sa.String(), nullable=False),
        sa.Column("detector_version", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="open"),
        sa.Column("disposition_reason", sa.Text(), nullable=True),
        sa.Column("disposed_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("disposed_at", sa.DateTime(), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.Column("last_run_id", sa.Integer(), sa.ForeignKey("discovery_runs.id"), nullable=True),
        sa.Column("still_detected", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("case_id", "discovery_key", name="uq_discovery_key"),
    )
    for col in ("tenant_id", "case_id", "detector", "status"):
        op.create_index(f"ix_discoveries_{col}", "discoveries", [col])
    op.create_table(
        "party_tags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("party_id", sa.Integer(), sa.ForeignKey("parties.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tag", sa.String(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("set_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("set_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("case_id", "party_id", "tag", name="uq_party_tag"),
    )
    op.create_index("ix_party_tags_tenant_id", "party_tags", ["tenant_id"])
    op.create_index("ix_party_tags_case_id", "party_tags", ["case_id"])

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
    # leads are kept and marked, never deleted by the application
    op.execute(f"REVOKE DELETE ON discoveries, discovery_runs FROM {ROLE}")


def downgrade() -> None:
    op.drop_table("party_tags")
    op.drop_table("discoveries")
    op.drop_table("discovery_runs")
