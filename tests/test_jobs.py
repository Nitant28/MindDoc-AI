"""Durable jobs and asynchronous ingestion (ADR-0003, design G §5). Runs on SQLite and on PostgreSQL (TEST_DB=postgres).

Covers: async upload → worker → completed; idempotent re-upload; worker crash (lease expiry) → re-claim without
duplicate rows; retries with backoff → dead-letter; permanent failure → document marked failed and visible; claim
exclusivity under concurrent workers (PostgreSQL); worker runs inside the job's tenant.
"""
import io
import json
import threading
from datetime import datetime, timedelta

import pytest
from sqlalchemy import text

from app.database import models
from app.database.models import Document, DocumentChunk, Job, SessionLocal
from app.database.tenancy import set_tenant
from app.jobs import queue
from app.jobs.worker import HANDLERS, handler, run_one

import app.jobs.handlers  # noqa: F401  (registers ingest_document)

DOC = ("SERVICE AGREEMENT. Orbit Realty LLP will provide warehouse services to Kaveri Agro Foods Ltd for a monthly "
       "fee of Rs. 3,25,000. Either party may terminate with three months' notice. ") * 3


def _register(client, email):
    r = client.post("/api/auth/register", json={"email": email, "password": "correct-horse-1"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _drain(max_jobs=20):
    n = 0
    while n < max_jobs and run_one("test-worker"):
        n += 1
    return n


def test_async_upload_is_queued_then_processed(client):
    h = _register(client, "jobs-a@example.com")
    r = client.post("/api/documents/upload", headers=h,
                    files={"file": ("lease.txt", io.BytesIO(DOC.encode()), "text/plain")})
    assert r.status_code == 202, r.text
    body = r.json()
    doc_id = body["document_id"]
    assert body["status"] == "queued" and body["analysis"] is None
    s = client.get(f"/api/documents/{doc_id}/status", headers=h).json()
    assert s["status"] == "queued" and s["job"]["state"] == "queued"

    assert _drain() >= 1
    s = client.get(f"/api/documents/{doc_id}/status", headers=h).json()
    assert s["status"] == "completed" and s["job"]["state"] == "succeeded", s
    detail = client.get(f"/api/documents/{doc_id}", headers=h).json()
    assert detail["doc_type"] and detail["stats"]["chunks"] >= 1

    # idempotent: the same bytes again → same document, no second job
    r2 = client.post("/api/documents/upload", headers=h,
                     files={"file": ("lease-copy.txt", io.BytesIO(DOC.encode()), "text/plain")})
    assert r2.status_code == 200 and r2.json()["document_id"] == doc_id
    db = SessionLocal()
    tid = db.get(Document, doc_id).tenant_id if not models.IS_POSTGRES else None
    db.close()
    if tid is not None:
        db = SessionLocal()
        assert db.query(Job).filter(Job.subject_id == doc_id).count() == 1
        db.close()


def test_worker_crash_lease_expiry_requeues_without_duplicates(client):
    h = _register(client, "jobs-b@example.com")
    r = client.post("/api/documents/upload", headers=h,
                    files={"file": ("crash.txt", io.BytesIO((DOC + " crash").encode()), "text/plain")})
    doc_id = r.json()["document_id"]
    job = queue.claim("doomed-worker", kinds=["ingest_document"])
    assert job and job["payload"]["document_id"] == doc_id and job["attempts"] == 1
    # the worker "dies": its lease expires without completion
    db = SessionLocal()
    db.execute(text("UPDATE jobs SET lease_until = :t WHERE id = :i"),
               {"t": datetime.utcnow() - timedelta(minutes=1), "i": job["id"]})
    db.commit()
    db.close()
    assert queue.reap_expired() >= 1
    assert _drain() >= 1
    s = client.get(f"/api/documents/{doc_id}/status", headers=h).json()
    assert s["status"] == "completed" and s["job"]["attempts"] == 2
    # running the job again (at-least-once delivery) must not duplicate chunks
    db = SessionLocal()
    set_tenant(db, s and _tenant_of(h, client))
    n_before = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).count()
    from app.services import ingestion
    ingestion.process_document(db, doc_id)
    db.commit()
    assert db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).count() == n_before > 0
    db.close()


def _tenant_of(h, client):
    me = client.get("/api/auth/me", headers=h).json()
    db = SessionLocal()
    tid = db.execute(text("SELECT tenant_id FROM users WHERE id = :i"), {"i": me["id"]}).scalar()
    db.close()
    return tid


def test_retry_backoff_then_dead_letter(client):
    calls = []

    @handler("flaky_test_job")
    def flaky(db, job):
        calls.append(job["attempts"])
        raise RuntimeError("transient failure")

    try:
        h = _register(client, "jobs-c@example.com")
        tid = _tenant_of(h, client)
        db = SessionLocal()
        set_tenant(db, tid)
        job = queue.enqueue(db, tid, "flaky_test_job", {}, idempotency_key="flaky-1", max_attempts=2)
        db.commit()
        jid = job.id
        db.close()
        assert _drain() == 1  # attempt 1 fails → re-queued with backoff (not immediately runnable)
        db = SessionLocal()
        j = db.get(Job, jid)
        assert j.state == "queued" and j.attempts == 1 and j.run_after > datetime.utcnow() - timedelta(seconds=1)
        j.run_after = datetime.utcnow() - timedelta(seconds=1)
        db.commit()
        db.close()
        assert _drain() == 1  # attempt 2 fails → dead (max_attempts=2)
        db = SessionLocal()
        state, err = db.execute(text("SELECT state, last_error FROM jobs WHERE id = :i"), {"i": jid}).one()
        db.close()
        assert state == "dead" and "transient failure" in err and calls == [1, 2]
    finally:
        HANDLERS.pop("flaky_test_job", None)


def test_permanent_failure_marks_document_failed(client):
    h = _register(client, "jobs-d@example.com")
    r = client.post("/api/documents/upload", headers=h,
                    files={"file": ("empty.txt", io.BytesIO(b"   \n  "), "text/plain")})
    doc_id = r.json()["document_id"]
    assert _drain() >= 1
    s = client.get(f"/api/documents/{doc_id}/status", headers=h).json()
    assert s["status"] == "failed" and s["job"]["state"] == "dead" and s["job"]["attempts"] == 1
    assert "extract text" in (s["detail"] or "").lower()
    # visible in the document list, and recoverable by reprocessing
    lst = client.get("/api/documents/list", headers=h).json()
    assert any(d["id"] == doc_id and d["status"] == "failed" for d in lst)
    rp = client.post(f"/api/documents/{doc_id}/reprocess", headers=h)
    assert rp.status_code == 200 and rp.json()["status"] == "queued"


@pytest.mark.skipif(not models.IS_POSTGRES, reason="SKIP LOCKED concurrency needs PostgreSQL")
def test_concurrent_claims_never_duplicate(client):
    seen, lock = [], threading.Lock()

    @handler("noop_test_job")
    def noop(db, job):
        with lock:
            seen.append(job["id"])

    try:
        h = _register(client, "jobs-e@example.com")
        tid = _tenant_of(h, client)
        db = SessionLocal()
        set_tenant(db, tid)
        for i in range(24):
            queue.enqueue(db, tid, "noop_test_job", {"i": i}, idempotency_key=f"noop-{i}")
        db.commit()
        db.close()

        def work(n):
            while run_one(f"w{n}"):
                pass

        threads = [threading.Thread(target=work, args=(n,)) for n in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(60)
        assert len(seen) == 24 and len(set(seen)) == 24
    finally:
        HANDLERS.pop("noop_test_job", None)


def test_worker_runs_inside_job_tenant(client):
    """A job only sees its own tenant's rows (RLS on PostgreSQL; explicit filters everywhere)."""
    got = {}

    @handler("peek_test_job")
    def peek(db, job):
        got["docs"] = [d.tenant_id for d in db.query(Document).all()] if models.IS_POSTGRES else None
        got["ctx"] = db.info.get("tenant_id")

    try:
        h = _register(client, "jobs-f@example.com")
        tid = _tenant_of(h, client)
        db = SessionLocal()
        set_tenant(db, tid)
        queue.enqueue(db, tid, "peek_test_job", {}, idempotency_key="peek-1")
        db.commit()
        db.close()
        _drain()  # other tests may have left jobs queued; drain until ours has run
        assert got.get("ctx") == tid
        if models.IS_POSTGRES:
            assert all(t == tid for t in got["docs"])
    finally:
        HANDLERS.pop("peek_test_job", None)


def test_job_payload_is_json(client):
    db = SessionLocal()
    rows = db.execute(text("SELECT payload FROM jobs")).all()
    db.close()
    for (p,) in rows:
        json.loads(p)
