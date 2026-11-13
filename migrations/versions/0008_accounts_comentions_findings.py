"""Bank accounts, co-mentions out of relationships, findings and frozen reports (R5; design F §2.3, §4, §7; ADR-0005)

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-13

* `bank_accounts`: one row per account seen in the tenant's statements, keyed by IFSC + keyed hash of the number;
  only the masked number is stored. `statements.bank_account_id` links a statement to its account. Any full number
  already stored in `statements.account_masked` is masked here (rows visible to the migration role; the statement
  engine version bump re-analyses the rest).
* `co_mentions`: "named in the same passage" moves out of `relations` (ADR-0005 amendment: a weak signal, never a
  relationship). Existing `co_occurs` relation rows are moved.
* `findings` / `finding_support`: versioned analyst findings pinned to claim versions; one current version per key.
* `reports` / `report_findings`: frozen reports with a canonical JSON snapshot and its SHA-256.
All new tables are under FORCE row-level security. The application role cannot delete findings or support rows,
and cannot update or delete reports or their pinned findings.
"""
import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

ROLE = "minddoc_app"
TENANT_EXPR = "NULLIF(current_setting('app.tenant_id', true), '')::integer"
TABLES = ["bank_accounts", "co_mentions", "findings", "finding_support", "reports", "report_findings"]


def upgrade() -> None:
    op.create_table(
        "bank_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("account_key", sa.String(), nullable=False),
        sa.Column("ifsc", sa.String(), nullable=True),
        sa.Column("account_masked", sa.String(), nullable=False),
        sa.Column("account_hash", sa.String(64), nullable=False),
        sa.Column("hash_basis", sa.String(), nullable=False),
        sa.Column("account_type", sa.String(), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("holder_name", sa.String(), nullable=True),
        sa.Column("holder_source", sa.String(), nullable=True),
        sa.Column("holder_set_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("holder_set_at", sa.DateTime(), nullable=True),
        sa.Column("first_document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("tenant_id", "account_key", name="uq_bank_account_key"),
    )
    op.create_index("ix_bank_accounts_tenant_id", "bank_accounts", ["tenant_id"])
    with op.batch_alter_table("statements") as b:
        b.add_column(sa.Column("bank_account_id", sa.Integer(), nullable=True))
        b.create_foreign_key("fk_statements_bank_account", "bank_accounts", ["bank_account_id"], ["id"],
                             ondelete="SET NULL")
        b.create_index("ix_statements_bank_account_id", ["bank_account_id"])

    op.create_table(
        "co_mentions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("a_entity_id", sa.Integer(), sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("b_entity_id", sa.Integer(), sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunks", sa.Integer(), nullable=False),
    )
    for col in ("tenant_id", "document_id", "a_entity_id", "b_entity_id"):
        op.create_index(f"ix_co_mentions_{col}", "co_mentions", [col])

    op.create_table(
        "findings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("finding_key", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("method", sa.String(), nullable=False),
        sa.Column("evidence_snapshot_at", sa.DateTime(), nullable=False),
        sa.Column("supersedes_id", sa.Integer(), sa.ForeignKey("findings.id"), nullable=True),
        sa.Column("change_note", sa.String(), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("superseded_at", sa.DateTime(), nullable=True),
    )
    for col in ("tenant_id", "case_id", "finding_key", "superseded_at"):
        op.create_index(f"ix_findings_{col}", "findings", [col])
    op.create_index("uq_findings_current_version", "findings", ["case_id", "finding_key"], unique=True,
                    postgresql_where=sa.text("superseded_at IS NULL"), sqlite_where=sa.text("superseded_at IS NULL"))
    op.create_table(
        "finding_support",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("finding_id", sa.Integer(), sa.ForeignKey("findings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.Integer(), sa.ForeignKey("claims.id"), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
    )
    for col in ("tenant_id", "finding_id", "claim_id"):
        op.create_index(f"ix_finding_support_{col}", "finding_support", [col])
    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("frozen_at", sa.DateTime(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("snapshot", sa.Text(), nullable=False),
        sa.Column("issued_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_reports_tenant_id", "reports", ["tenant_id"])
    op.create_index("ix_reports_case_id", "reports", ["case_id"])
    op.create_table(
        "report_findings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("report_id", sa.Integer(), sa.ForeignKey("reports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("finding_id", sa.Integer(), sa.ForeignKey("findings.id"), nullable=False),
    )
    for col in ("tenant_id", "report_id", "finding_id"):
        op.create_index(f"ix_report_findings_{col}", "report_findings", [col])

    # co-occurrence leaves the relationship table (rows the migration role can see; the app treats any left-over
    # co_occurs relation as a co-mention too)
    op.execute("""INSERT INTO co_mentions (tenant_id, document_id, a_entity_id, b_entity_id, chunks)
                  SELECT tenant_id, document_id, source_id, target_id, CAST(round(weight) AS INTEGER)
                  FROM relations WHERE relation = 'co_occurs' AND tenant_id IS NOT NULL AND document_id IS NOT NULL""")
    op.execute("DELETE FROM relations WHERE relation = 'co_occurs' AND tenant_id IS NOT NULL "
               "AND document_id IS NOT NULL")

    if op.get_bind().dialect.name != "postgresql":
        return
    # no full account numbers at rest: keep the last four digits of anything stored before this migration
    op.execute(r"""UPDATE statements SET account_masked =
                   regexp_replace(left(account_masked, greatest(length(account_masked) - 4, 0)), '\d', 'X', 'g')
                   || right(account_masked, 4)
                   WHERE account_masked ~ '\d{5,}'""")
    for t in TABLES:
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {t} TO {ROLE}")
        op.execute(f"GRANT USAGE, SELECT ON SEQUENCE {t}_id_seq TO {ROLE}")
        op.execute(f"ALTER TABLE {t} ALTER COLUMN tenant_id SET DEFAULT {TENANT_EXPR}")
        op.execute(f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {t} FORCE ROW LEVEL SECURITY")
        op.execute(f"""CREATE POLICY tenant_isolation ON {t}
                       USING (tenant_id = (SELECT {TENANT_EXPR}))
                       WITH CHECK (tenant_id = (SELECT {TENANT_EXPR}))""")
    # finding versions are closed, never deleted; issued reports and their pins are immutable
    op.execute(f"REVOKE DELETE ON findings, finding_support FROM {ROLE}")
    op.execute(f"REVOKE UPDATE ON finding_support, reports, report_findings FROM {ROLE}")
    op.execute(f"REVOKE DELETE ON reports, report_findings FROM {ROLE}")


def downgrade() -> None:
    op.execute("""INSERT INTO relations (tenant_id, document_id, source_id, target_id, relation, weight)
                  SELECT tenant_id, document_id, a_entity_id, b_entity_id, 'co_occurs', chunks FROM co_mentions""")
    op.drop_table("report_findings")
    op.drop_table("reports")
    op.drop_table("finding_support")
    op.drop_index("uq_findings_current_version", table_name="findings")
    op.drop_table("findings")
    op.drop_table("co_mentions")
    with op.batch_alter_table("statements") as b:
        b.drop_index("ix_statements_bank_account_id")
        b.drop_constraint("fk_statements_bank_account", type_="foreignkey")
        b.drop_column("bank_account_id")
    op.drop_table("bank_accounts")
