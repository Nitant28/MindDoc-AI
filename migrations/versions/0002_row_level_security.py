"""Row-level security: non-owner application role, tenant policies, append-only audit (ADR-0002, design G §4)

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-10

* `minddoc_app` is a NOLOGIN, non-owner, non-BYPASSRLS role. Application connections `SET ROLE minddoc_app`
  (app/database/models.py), so policies apply even when the login user owns the tables. Production should log in as a
  dedicated role that is only a member of `minddoc_app` (docs/DEPLOYMENT.md).
* Every content table gets ENABLE + FORCE ROW LEVEL SECURITY and one policy comparing `tenant_id` with the
  transaction-local setting `app.tenant_id`. A missing setting reads as NULL → no rows (fail closed).
* `tenants`, `users` (authentication lookups happen before the tenant is known) and `jobs` (claimed across tenants by
  workers; payloads hold ids only) are deliberately not under RLS; application code filters them explicitly.
* `audit_events` is append-only for the application role (no UPDATE/DELETE).
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

ROLE = "minddoc_app"
RLS_TABLES = ["documents", "document_chunks", "entities", "entity_mentions", "relations", "chat_sessions",
              "chat_messages", "saved_items", "query_logs", "cases", "case_documents", "audit_events"]
TENANT_EXPR = "NULLIF(current_setting('app.tenant_id', true), '')::integer"


def upgrade() -> None:
    op.execute(f"""
    DO $$
    BEGIN
      IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{ROLE}') THEN
        CREATE ROLE {ROLE} NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
      END IF;
    END $$;
    """)
    # the migrating/owner login must be able to SET ROLE to the application role
    op.execute(f"GRANT {ROLE} TO CURRENT_USER")
    op.execute(f"GRANT USAGE ON SCHEMA public TO {ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {ROLE}")
    op.execute(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {ROLE}")
    op.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {ROLE}")
    op.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO {ROLE}")
    op.execute(f"REVOKE UPDATE, DELETE ON audit_events FROM {ROLE}")
    op.execute(f"REVOKE SELECT, INSERT, UPDATE, DELETE ON alembic_version FROM {ROLE}")
    for t in RLS_TABLES:
        op.execute(f"ALTER TABLE {t} ALTER COLUMN tenant_id SET DEFAULT {TENANT_EXPR}")
        op.execute(f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {t} FORCE ROW LEVEL SECURITY")
        op.execute(f"""CREATE POLICY tenant_isolation ON {t}
                       USING (tenant_id = (SELECT {TENANT_EXPR}))
                       WITH CHECK (tenant_id = (SELECT {TENANT_EXPR}))""")


def downgrade() -> None:
    for t in RLS_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {t}")
        op.execute(f"ALTER TABLE {t} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {t} DISABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {t} ALTER COLUMN tenant_id DROP DEFAULT")
    op.execute(f"REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {ROLE}")
    op.execute(f"REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM {ROLE}")
    op.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM {ROLE}")
    op.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM {ROLE}")
    op.execute(f"REVOKE USAGE ON SCHEMA public FROM {ROLE}")
