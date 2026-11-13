"""Retrieval inside PostgreSQL (migration 0007): backend selection, parity with the in-process index, the vector
trigger, tenant isolation and fallback. PostgreSQL-only; skipped on SQLite."""
import io
import json

import pytest
from sqlalchemy import text

from app.database.models import IS_POSTGRES, SessionLocal, User
from app.database.tenancy import set_tenant
from app.ml import retrieval
from tests.conftest import _auth

pytestmark = pytest.mark.skipif(not IS_POSTGRES, reason="PostgreSQL retrieval path")

DOCS = {
    "lease.txt": "Orbit Realty LLP leases warehouse unit B-14 in Bhiwandi to Kaveri Agro Foods Ltd for five years. "
                 "Monthly rent is Rs 3,25,000, rising by 5% every year. The tenant paid a refundable security deposit.",
    "sanction.txt": "Meridian Bank sanctioned a cash credit limit of Rs 4.5 crore to Shreeji Polymers. Interest is "
                    "10.25% per annum, payable monthly, secured by a first charge on stock and book debts.",
    "insurance.txt": "Policy FP-55120 covers the stock at the Silvassa plant against fire and flood for a sum insured "
                     "of Rs 6 crore. Theft is not covered. Meridian Bank is named as loss payee.",
}


def _upload(client, headers, name, body):
    r = client.post("/api/documents/upload?wait=true", headers=headers,
                    files={"file": (name, io.BytesIO(body.encode()), "text/plain")})
    assert r.status_code == 200, r.text
    return r.json()["document_id"]


@pytest.fixture(scope="module")
def tenant(client):
    headers = _auth(client, "pg-retrieval@example.com")
    ids = {name: _upload(client, headers, name, body) for name, body in DOCS.items()}
    db = SessionLocal()
    tid = db.query(User).filter(User.email == "pg-retrieval@example.com").one().tenant_id
    db.close()
    return {"headers": headers, "tenant_id": tid, "docs": ids}


def _session(tid):
    db = SessionLocal()
    set_tenant(db, tid)
    return db


def test_postgres_backend_is_used_and_vectors_are_filled(client, tenant):
    db = _session(tenant["tenant_id"])
    try:
        index = retrieval.get_index(db, tenant["tenant_id"])
        assert index.backend == "postgres"
        missing = db.execute(text("SELECT count(*) FROM document_chunks WHERE embedding_vec IS NULL")).scalar()
        assert missing == 0
        assert index.size == db.execute(text("SELECT count(*) FROM document_chunks")).scalar() >= 3
    finally:
        db.close()
    r = client.get("/api/intel/overview", headers=tenant["headers"])
    assert r.status_code == 200 and r.json()["retrieval_backend"] == "postgres"


def test_postgres_search_matches_the_in_process_index(tenant):
    db = _session(tenant["tenant_id"])
    try:
        pg = retrieval.get_index(db, tenant["tenant_id"])
        mem = retrieval.memory_index(db, tenant["tenant_id"])
        for q in ("security deposit for the warehouse", "interest rate on the cash credit limit",
                  "is theft covered by the policy"):
            a = [h.chunk.id for h in pg.search(q, k=3, strategy="dense", use_rerank=False, use_mmr=False)]
            b = [h.chunk.id for h in mem.search(q, k=3, strategy="dense", use_rerank=False, use_mmr=False)]
            assert a == b, q  # exact cosine scan: same ranking as NumPy
            top = pg.search(q, k=3, use_rerank=False)[0].chunk
            assert top.id == mem.search(q, k=3, use_rerank=False)[0].chunk.id, q
        hit = pg.search("theft", k=2, strategy="fts", use_rerank=False, use_mmr=False)
        assert hit and "Theft" in hit[0].chunk.text
        only = pg.search("rent", k=5, document_ids=[tenant["docs"]["sanction.txt"]], use_rerank=False)
        assert {h.chunk.document_id for h in only} == {tenant["docs"]["sanction.txt"]}
        cov = pg.coverage_sample([tenant["docs"]["lease.txt"]], 4)
        assert cov and {h.chunk.document_id for h in cov} == {tenant["docs"]["lease.txt"]}
        assert set(pg.document_vectors()) == set(tenant["docs"].values())
    finally:
        db.close()


def test_other_tenants_chunks_are_never_returned(client, tenant):
    other = _auth(client, "pg-retrieval-other@example.com")
    _upload(client, other, "secret.txt", "Confidential: the warehouse security deposit is held in escrow by Zeta Bank.")
    db = _session(tenant["tenant_id"])
    try:
        index = retrieval.get_index(db, tenant["tenant_id"])
        hits = index.search("Zeta Bank escrow security deposit", k=10, use_rerank=False, use_mmr=False)
        assert hits and all(h.chunk.document_id in tenant["docs"].values() for h in hits)
    finally:
        db.close()


def test_trigger_keeps_vectors_in_step_and_bad_vectors_fall_back(tenant):
    db = _session(tenant["tenant_id"])
    try:
        cid = db.execute(text("SELECT min(id) FROM document_chunks")).scalar()
        db.execute(text("UPDATE document_chunks SET embedding = :e WHERE id = :i"), {"e": json.dumps([0.1, 0.2]), "i": cid})
        db.commit()
        assert db.execute(text("SELECT embedding_vec IS NULL FROM document_chunks WHERE id = :i"), {"i": cid}).scalar()
        retrieval.invalidate(tenant["tenant_id"])
        # a 2-d vector is not the active model's: the chunk is re-embedded, the trigger refills the vector
        index = retrieval.get_index(db, tenant["tenant_id"])
        assert index.backend == "postgres"
        assert not db.execute(text("SELECT embedding_vec IS NULL FROM document_chunks WHERE id = :i"),
                              {"i": cid}).scalar()
    finally:
        db.close()


def test_awkward_queries_and_database_errors_do_not_fail_search(tenant, monkeypatch):
    db = _session(tenant["tenant_id"])
    try:
        index = retrieval.get_index(db, tenant["tenant_id"])
        for q in ("O'Brien's deposit", "C:\path\to\rent", "rate: 10.25% | & ! ( )", "", "   "):
            index.search(q, k=3, use_rerank=False)
        bm = index.search("interest rate cash credit", k=1, strategy="bm25", use_rerank=False, use_mmr=False)
        assert bm and bm[0].chunk.document_id == tenant["docs"]["sanction.txt"]

        def broken(*a, **kw):
            raise RuntimeError("simulated database failure")
        monkeypatch.setattr(retrieval.PgIndex, "_bm25_ids", broken)
        hits = index.search("security deposit warehouse", k=2, use_rerank=False)
        assert hits and hits[0].chunk.document_id == tenant["docs"]["lease.txt"]  # served by the in-process index
    finally:
        db.close()
