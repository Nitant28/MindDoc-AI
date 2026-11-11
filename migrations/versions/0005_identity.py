"""Identity layer: party records, identifiers, mentions, append-only identity events, review queue (ADR-0009)

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-12

All five tables carry tenant_id under FORCE row-level security. `identity_events` is append-only for the
application role (no UPDATE/DELETE): an unmerge is a new event that reverses a merge, so the identity state at any
past time can be replayed.
"""
import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

ROLE = "minddoc_app"
TENANT_EXPR = "NULLIF(current_setting('app.tenant_id', true), '')::integer"
TABLES = ["parties", "party_identifiers", "party_mentions", "identity_events", "party_reviews"]


def upgrade() -> None:
    op.create_table(
        "parties",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("name_norm", sa.String(), nullable=False),
        sa.Column("signature", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("case_id", "signature", name="uq_party_signature"),
    )
    op.create_index("ix_parties_tenant_id", "parties", ["tenant_id"])
    op.create_index("ix_parties_case_id", "parties", ["case_id"])

    op.create_table(
        "party_identifiers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("party_id", sa.Integer(), sa.ForeignKey("parties.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scheme", sa.String(), nullable=False),
        sa.Column("value", sa.String(), nullable=False),
        sa.Column("valid_structure", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_party_identifiers_tenant_id", "party_identifiers", ["tenant_id"])
    op.create_index("ix_party_identifiers_party_id", "party_identifiers", ["party_id"])

    op.create_table(
        "party_mentions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("party_id", sa.Integer(), sa.ForeignKey("parties.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=True),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("channel", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_party_mentions_tenant_id", "party_mentions", ["tenant_id"])
    op.create_index("ix_party_mentions_party_id", "party_mentions", ["party_id"])
    op.create_index("ix_party_mentions_document_id", "party_mentions", ["document_id"])

    op.create_table(
        "identity_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("a_party_id", sa.Integer(), sa.ForeignKey("parties.id", ondelete="CASCADE"), nullable=False),
        sa.Column("b_party_id", sa.Integer(), sa.ForeignKey("parties.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reverses_event_id", sa.Integer(), sa.ForeignKey("identity_events.id"), nullable=True),
        sa.Column("method", sa.String(), nullable=False),
        sa.Column("probability_bp", sa.Integer(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("features", sa.Text(), nullable=True),
        sa.Column("decided_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("decided_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_identity_events_tenant_id", "identity_events", ["tenant_id"])
    op.create_index("ix_identity_events_case_id", "identity_events", ["case_id"])
    op.create_index("ix_identity_events_decided_at", "identity_events", ["decided_at"])

    op.create_table(
        "party_reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("a_party_id", sa.Integer(), sa.ForeignKey("parties.id", ondelete="CASCADE"), nullable=False),
        sa.Column("b_party_id", sa.Integer(), sa.ForeignKey("parties.id", ondelete="CASCADE"), nullable=False),
        sa.Column("method", sa.String(), nullable=False),
        sa.Column("probability_bp", sa.Integer(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("features", sa.Text(), nullable=True),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("decided_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("case_id", "a_party_id", "b_party_id", name="uq_party_review_pair"),
    )
    op.create_index("ix_party_reviews_tenant_id", "party_reviews", ["tenant_id"])
    op.create_index("ix_party_reviews_case_id", "party_reviews", ["case_id"])

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
    op.execute(f"REVOKE UPDATE, DELETE ON identity_events FROM {ROLE}")


def downgrade() -> None:
    for t in reversed(TABLES):
        op.drop_table(t)
