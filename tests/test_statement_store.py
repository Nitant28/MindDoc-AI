"""Persisted statement analysis (ADR-0011): stored once per document, refreshed on demand, removed with the document,
and analysed automatically after ingestion of a statement-like PDF."""
import random
from datetime import date

import pytest
from sqlalchemy import text

from app.database.models import Document, ReconciliationCheck, SessionLocal, Statement, StatementTxn
from app.database.tenancy import set_tenant
from app.jobs.worker import run_one

pytest.importorskip("reportlab", reason="StatementBench generator needs reportlab (requirements-dev.txt)")

import app.jobs.handlers  # noqa: E402,F401  (registers job handlers)


def _pdf(tmp_path, seed, n=25):
    from benchmarks.statements.generator import LAYOUTS, make_history, render
    rng = random.Random(seed)
    opening, txns = make_history(rng, LAYOUTS["C"]["od"], n, date(2024, 4, 1))
    meta = {"bank": "Meridian Bank Ltd", "branch": "Andheri", "ifsc": "MERI0123456", "holder": "Store Test",
            "account_masked": "XXXXXXXX9876", "account_type": "SAVINGS", "period": ["01-04-2024", "30-06-2024"]}
    pdf = tmp_path / f"store-{seed}.pdf"
    render(pdf, meta, opening, txns, LAYOUTS["C"])
    return pdf.read_bytes(), txns


def _register(client, email):
    r = client.post("/api/auth/register", json={"email": email, "password": "correct-horse-1"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _tenant(client, h):
    me = client.get("/api/auth/me", headers=h).json()
    db = SessionLocal()
    tid = db.execute(text("SELECT tenant_id FROM users WHERE id = :i"), {"i": me["id"]}).scalar()
    db.close()
    return tid


def _counts(tid, doc_id):
    db = SessionLocal()
    set_tenant(db, tid)
    ids = [s.id for s in db.query(Statement).filter(Statement.document_id == doc_id).all()]
    out = (len(ids),
           db.query(StatementTxn).filter(StatementTxn.statement_id.in_(ids)).count() if ids else 0,
           db.query(ReconciliationCheck).filter(ReconciliationCheck.statement_id.in_(ids)).count() if ids else 0)
    db.close()
    return out


def test_statement_is_stored_reused_refreshed_and_deleted(client, tmp_path):
    h = _register(client, "statement-store@example.com")
    tid = _tenant(client, h)
    data, txns = _pdf(tmp_path, 501)
    doc_id = client.post("/api/documents/upload?wait=true", headers=h,
                         files={"file": ("store.pdf", data, "application/pdf")}).json()["document_id"]

    first = client.get(f"/api/documents/{doc_id}/statement", headers=h).json()
    assert first["is_statement"] and first["summary"]["transactions"] == len(txns)
    assert first["period"] == {"start": txns[0].date.isoformat(), "end": txns[-1].date.isoformat()}
    assert _counts(tid, doc_id)[:2] == (1, len(txns))
    assert client.get(f"/api/documents/{doc_id}", headers=h).json()["doc_type"] == "bank_statement"

    again = client.get(f"/api/documents/{doc_id}/statement", headers=h).json()
    assert again["analysed_at"] == first["analysed_at"] and again["transactions"] == first["transactions"]
    fresh = client.get(f"/api/documents/{doc_id}/statement?refresh=true", headers=h).json()
    assert fresh["transactions"] == first["transactions"] and _counts(tid, doc_id)[:2] == (1, len(txns))

    assert client.delete(f"/api/documents/delete/{doc_id}", headers=h).status_code == 200
    assert _counts(tid, doc_id) == (0, 0, 0)


def test_statement_like_upload_is_analysed_by_a_background_job(client, tmp_path):
    h = _register(client, "statement-job@example.com")
    tid = _tenant(client, h)
    data, txns = _pdf(tmp_path, 502)
    doc_id = client.post("/api/documents/upload", headers=h,
                         files={"file": ("job.pdf", data, "application/pdf")}).json()["document_id"]
    for _ in range(10):  # ingest, then the statement job it enqueues
        if not run_one("test-worker"):
            break
    assert _counts(tid, doc_id)[:2] == (1, len(txns))
    db = SessionLocal()
    set_tenant(db, tid)
    assert db.get(Document, doc_id).doc_type == "bank_statement"
    db.close()


def test_non_statement_pdf_is_not_queued_for_statement_analysis(client):
    from app.services.statements import looks_like_statement
    assert looks_like_statement("Txn Date  Description  Debit  Credit  Balance\n01-04-2024 NEFT 100.00 0.00 900.00")
    assert not looks_like_statement("Master services agreement. Either party may terminate with 60 days notice.")
