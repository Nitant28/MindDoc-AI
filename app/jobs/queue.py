"""Durable job queue on the `jobs` table (ADR-0003, design G §5).

Guarantees:
* **Exactly one claimant at a time.** PostgreSQL claims with `FOR UPDATE SKIP LOCKED` in one short statement; SQLite
  (single-user dev fallback) claims under a process-wide lock.
* **At-least-once with idempotent handlers.** A worker that dies leaves a `running` job whose lease expires; the reaper
  re-queues it. Handlers must be safe to repeat (ingestion replaces a document's derived rows).
* **Enqueue is idempotent** per (tenant, kind, idempotency_key) and joins the caller's transaction, so the job exists
  if and only if the state change that needs it was committed (the job row *is* the outbox).
* Retries back off (1 s, 5 s, 30 s, 2 min, 10 min + jitter); after `max_attempts` the job is `dead` (dead-letter state,
  visible in the UI). `PermanentJobError` skips retries for deterministic failures (e.g. an unreadable file).
"""
from __future__ import annotations

import json
import random
import threading
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.models import IS_POSTGRES, Job, SessionLocal

BACKOFF_S = [1, 5, 30, 120, 600]
LEASE = timedelta(minutes=5)
_sqlite_claim_lock = threading.Lock()


class PermanentJobError(Exception):
    """A failure that will not change on retry (bad input, limits exceeded)."""


def _now() -> datetime:
    return datetime.utcnow()


def enqueue(db: Session, tenant_id: int, kind: str, payload: dict, idempotency_key: str, *, priority: int = 0,
            max_attempts: int = 5, subject_id: Optional[int] = None) -> Job:
    """Add a job in the caller's transaction (caller commits). Returns the existing job for a repeated key."""
    existing = db.query(Job).filter(Job.tenant_id == tenant_id, Job.kind == kind,
                                    Job.idempotency_key == idempotency_key).first()
    if existing:
        return existing
    job = Job(tenant_id=tenant_id, kind=kind, subject_id=subject_id, payload=json.dumps(payload),
              idempotency_key=idempotency_key,
              priority=priority, max_attempts=max_attempts, state="queued", run_after=_now())
    db.add(job)
    db.flush()
    if IS_POSTGRES:
        db.execute(text("SELECT pg_notify('minddoc_jobs', :k)"), {"k": kind})  # wake-up hint, delivered on commit
    return job


def claim(worker_id: str, kinds: Optional[list[str]] = None) -> Optional[dict]:
    """Claim the next runnable job. Returns a plain dict (no session attached) or None."""
    now = _now()
    kinds_sql = "AND kind = ANY(:kinds)" if (kinds and IS_POSTGRES) else ("AND kind IN :kinds" if kinds else "")
    params = {"w": worker_id, "now": now, "lease": now + LEASE}
    if kinds:
        params["kinds"] = list(kinds) if IS_POSTGRES else tuple(kinds)
    db = SessionLocal()
    try:
        if IS_POSTGRES:
            row = db.execute(text(f"""
                UPDATE jobs SET state = 'running', attempts = attempts + 1, locked_by = :w, lease_until = :lease,
                                updated_at = :now
                WHERE id = (SELECT id FROM jobs WHERE state = 'queued' AND run_after <= :now {kinds_sql}
                            ORDER BY priority DESC, run_after, id FOR UPDATE SKIP LOCKED LIMIT 1)
                RETURNING id, tenant_id, kind, payload, attempts, max_attempts"""), params).mappings().first()
            db.commit()
        else:
            with _sqlite_claim_lock:
                from sqlalchemy import bindparam
                stmt = text(f"""SELECT id FROM jobs WHERE state = 'queued' AND run_after <= :now {kinds_sql}
                                ORDER BY priority DESC, run_after, id LIMIT 1""")
                if kinds:
                    stmt = stmt.bindparams(bindparam("kinds", expanding=True))
                jid = db.execute(stmt, params).scalar()
                if jid is None:
                    return None
                db.execute(text("""UPDATE jobs SET state = 'running', attempts = attempts + 1, locked_by = :w,
                                   lease_until = :lease, updated_at = :now WHERE id = :id AND state = 'queued'"""),
                           {**params, "id": jid})
                db.commit()
                row = db.execute(text("SELECT id, tenant_id, kind, payload, attempts, max_attempts FROM jobs "
                                      "WHERE id = :id"), {"id": jid}).mappings().first()
        if not row:
            return None
        out = dict(row)
        out["payload"] = json.loads(out["payload"] or "{}")
        return out
    finally:
        db.close()


def _update(job_id: int, **fields) -> None:
    db = SessionLocal()
    try:
        fields["updated_at"] = _now()
        sets = ", ".join(f"{k} = :{k}" for k in fields)
        db.execute(text(f"UPDATE jobs SET {sets} WHERE id = :id"), {**fields, "id": job_id})
        db.commit()
    finally:
        db.close()


def heartbeat(job_id: int, worker_id: str) -> None:
    db = SessionLocal()
    try:
        db.execute(text("UPDATE jobs SET lease_until = :l WHERE id = :id AND locked_by = :w AND state = 'running'"),
                   {"l": _now() + LEASE, "id": job_id, "w": worker_id})
        db.commit()
    finally:
        db.close()


def set_progress(job_id: int, stage: str, detail: str = "") -> None:
    _update(job_id, progress=json.dumps({"stage": stage, "detail": detail, "at": _now().isoformat()}))


def complete(job_id: int) -> None:
    _update(job_id, state="succeeded", locked_by=None, lease_until=None, last_error=None)


def fail(job_id: int, attempts: int, max_attempts: int, error: str, permanent: bool = False) -> str:
    """Record a failure; returns the new state ('queued' for a retry, or 'dead')."""
    if permanent or attempts >= max_attempts:
        _update(job_id, state="dead", locked_by=None, lease_until=None, last_error=error[:4000])
        return "dead"
    delay = BACKOFF_S[min(attempts - 1, len(BACKOFF_S) - 1)] * (1 + random.random() * 0.25)
    _update(job_id, state="queued", locked_by=None, lease_until=None, last_error=error[:4000],
            run_after=_now() + timedelta(seconds=delay))
    return "queued"


def reap_expired() -> int:
    """Re-queue jobs whose worker vanished (lease expired). Returns how many were re-queued."""
    db = SessionLocal()
    try:
        n = db.execute(text("""UPDATE jobs SET state = 'queued', locked_by = NULL, lease_until = NULL,
                               last_error = COALESCE(last_error, '') || ' [lease expired; re-queued]'
                               WHERE state = 'running' AND lease_until < :now"""), {"now": _now()}).rowcount
        db.commit()
        return n or 0
    finally:
        db.close()


def cancel(db: Session, job: Job) -> bool:
    if job.state != "queued":
        return False
    job.state = "cancelled"
    db.commit()
    return True
