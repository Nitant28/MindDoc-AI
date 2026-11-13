"""Row-level security on the real application role (PostgreSQL only; run with TEST_DB=postgres).

These tests deliberately bypass the application's own tenant filters and query tables directly, so they prove the
database itself enforces isolation (defence in depth), including on reused pooled connections.
"""
import pytest
from sqlalchemy import text

from app.database import models
from app.database.models import Document, SessionLocal, Tenant
from app.database.tenancy import set_tenant

pytestmark = pytest.mark.skipif(not models.IS_POSTGRES, reason="row-level security needs PostgreSQL (TEST_DB=postgres)")

EXEMPT = {"tenants", "users", "jobs", "alembic_version"}


@pytest.fixture(scope="module")
def tenants(client):  # client fixture runs the app lifespan → migrations
    db = SessionLocal()
    a, b = Tenant(name="rls-a"), Tenant(name="rls-b")
    db.add_all([a, b])
    db.commit()
    ids = (a.id, b.id)
    db.close()
    return ids


def _session(tid):
    db = SessionLocal()
    if tid is not None:
        set_tenant(db, tid)
    return db


def test_connections_run_as_non_owner_app_role(client):
    db = SessionLocal()
    role, sup, bypass = db.execute(text(
        "SELECT current_user, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user")).one()
    db.close()
    assert role == "minddoc_app" and not sup and not bypass and models.RLS_ACTIVE["value"]


def test_every_tenant_table_has_forced_rls(client):
    db = SessionLocal()
    rows = db.execute(text("""
        SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity
        FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind = 'r'
          AND EXISTS (SELECT 1 FROM information_schema.columns
                      WHERE table_name = c.relname AND column_name = 'tenant_id')""")).all()
    db.close()
    missing = [r[0] for r in rows if r[0] not in EXEMPT and not (r[1] and r[2])]
    assert rows and not missing, f"tables without forced RLS: {missing}"


def test_isolation_select_update_delete_insert(tenants):
    a, b = tenants
    db = _session(a)
    doc = Document(filename="secret-a.txt", content="tenant A only", tenant_id=a, status="completed")
    db.add(doc)
    db.commit()
    doc_id = doc.id
    db.close()

    db = _session(b)  # tenant B: raw SQL, no application filter
    assert db.execute(text("SELECT count(*) FROM documents WHERE id = :i"), {"i": doc_id}).scalar() == 0
    assert db.execute(text("UPDATE documents SET content = 'x' WHERE id = :i"), {"i": doc_id}).rowcount == 0
    assert db.execute(text("DELETE FROM documents WHERE id = :i"), {"i": doc_id}).rowcount == 0
    db.commit()
    with pytest.raises(Exception):  # WITH CHECK: B cannot write a row claiming tenant A
        db.execute(text("INSERT INTO documents (filename, tenant_id, status) VALUES ('forged', :a, 'completed')"),
                   {"a": a})
        db.commit()
    db.rollback()
    db.close()

    db = _session(a)
    assert db.execute(text("SELECT content FROM documents WHERE id = :i"), {"i": doc_id}).scalar() == "tenant A only"
    db.close()


def test_missing_context_fails_closed_and_does_not_leak_through_pool(tenants):
    a, _ = tenants
    db = _session(a)
    assert db.execute(text("SELECT count(*) FROM documents")).scalar() >= 1
    db.commit()  # transaction-local setting ends here; the connection returns to the pool
    db.close()
    for _ in range(3):  # likely reuses the same pooled connection
        db = _session(None)
        assert db.execute(text("SELECT count(*) FROM documents")).scalar() == 0
        db.close()


def test_child_rows_inherit_tenant_and_audit_is_append_only(tenants):
    a, _ = tenants
    db = _session(a)
    db.execute(text("INSERT INTO audit_events (verb, object_type, payload_hash) VALUES ('test', 'doc', 'h')"))
    db.commit()
    assert db.execute(text("SELECT tenant_id FROM audit_events ORDER BY id DESC LIMIT 1")).scalar() == a
    with pytest.raises(Exception):
        db.execute(text("UPDATE audit_events SET verb = 'tampered'"))
        db.commit()
    db.rollback()
    db.close()
