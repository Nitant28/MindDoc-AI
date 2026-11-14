"""Case members with roles, organisation members and invitations (ADR-0012)

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-14

* `users.tenant_role` (admin | member) and `users.is_active`. Every existing user created their own workspace, so
  existing rows become admins.
* `case_members`: explicit membership of a case with a role (lead / analyst / reviewer / viewer), under FORCE
  row-level security. The default "General" case needs no rows: every active member of the organisation can use it.
* `tenant_invites`: single-use invitations to join an organisation. Only a SHA-256 of the token is stored. Not under
  row-level security, like `users` and `tenants`: an invitation is redeemed at registration, before any tenant
  context exists. The application always filters it by tenant and looks it up by token hash only.
"""
import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

ROLE = "minddoc_app"
TENANT_EXPR = "NULLIF(current_setting('app.tenant_id', true), '')::integer"


def upgrade() -> None:
    with op.batch_alter_table("users") as b:
        b.add_column(sa.Column("tenant_role", sa.String(), nullable=False, server_default="admin"))
        b.add_column(sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))

    op.create_table(
        "case_members",
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("cases.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("added_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("added_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_case_members_tenant_id", "case_members", ["tenant_id"])
    op.create_index("ix_case_members_user_id", "case_members", ["user_id"])

    op.create_table(
        "tenant_invites",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("tenant_role", sa.String(), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_tenant_invites_tenant_id", "tenant_invites", ["tenant_id"])

    # case creators become leads of the cases they created
    op.execute("""INSERT INTO case_members (case_id, user_id, tenant_id, role, added_by, added_at)
                  SELECT id, created_by, tenant_id, 'lead', created_by, coalesce(created_at, CURRENT_TIMESTAMP)
                  FROM cases WHERE created_by IS NOT NULL AND is_default IS NOT TRUE""")

    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON case_members TO {ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON tenant_invites TO {ROLE}")
    op.execute(f"REVOKE DELETE ON tenant_invites FROM {ROLE}")  # invitations are revoked, never deleted
    op.execute(f"GRANT USAGE, SELECT ON SEQUENCE tenant_invites_id_seq TO {ROLE}")
    op.execute(f"ALTER TABLE case_members ALTER COLUMN tenant_id SET DEFAULT {TENANT_EXPR}")
    op.execute("ALTER TABLE case_members ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE case_members FORCE ROW LEVEL SECURITY")
    op.execute(f"""CREATE POLICY tenant_isolation ON case_members
                   USING (tenant_id = (SELECT {TENANT_EXPR}))
                   WITH CHECK (tenant_id = (SELECT {TENANT_EXPR}))""")


def downgrade() -> None:
    op.drop_table("tenant_invites")
    op.drop_table("case_members")
    with op.batch_alter_table("users") as b:
        b.drop_column("is_active")
        b.drop_column("tenant_role")
