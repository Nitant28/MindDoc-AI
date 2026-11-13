"""Job worker: embedded threads in the web process (demo hosts) or a standalone process (`python -m app.worker`).

Each job runs in a fresh session bound to the job's tenant (row-level security applies). A heartbeat thread extends
the lease while a long job (OCR) runs; if the process dies the lease expires and another worker re-claims the job.
"""
from __future__ import annotations

import logging
import os
import socket
import threading
import traceback
import uuid
from typing import Callable

from app.database.models import SessionLocal
from app.database.tenancy import set_tenant
from app.jobs import queue

logger = logging.getLogger(__name__)
HANDLERS: dict[str, Callable] = {}


def handler(kind: str):
    def deco(fn):
        HANDLERS[kind] = fn
        return fn
    return deco


def run_one(worker_id: str) -> bool:
    """Claim and run at most one job. Returns True if a job was processed (success or failure)."""
    job = queue.claim(worker_id, kinds=list(HANDLERS) or None)
    if not job:
        return False
    fn = HANDLERS.get(job["kind"])
    stop_beat = threading.Event()

    def beat():
        while not stop_beat.wait(60):
            try:
                queue.heartbeat(job["id"], worker_id)
            except Exception as e:  # a missed heartbeat only shortens the lease
                logger.warning("heartbeat failed for job %s: %s", job["id"], e)

    threading.Thread(target=beat, daemon=True, name=f"beat-{job['id']}").start()
    db = SessionLocal()
    try:
        if fn is None:
            raise queue.PermanentJobError(f"no handler for job kind {job['kind']!r}")
        set_tenant(db, job["tenant_id"])
        fn(db, job)
        db.commit()
        queue.complete(job["id"])
        logger.info("job %s (%s) succeeded", job["id"], job["kind"])
    except Exception as e:
        db.rollback()
        permanent = isinstance(e, queue.PermanentJobError)
        state = queue.fail(job["id"], job["attempts"], job["max_attempts"],
                           f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=3)}", permanent=permanent)
        logger.warning("job %s (%s) failed -> %s: %s", job["id"], job["kind"], state, e)
        try:
            on_fail = HANDLERS.get(job["kind"] + ":failed")
            if on_fail and state == "dead":
                fdb = SessionLocal()
                try:
                    set_tenant(fdb, job["tenant_id"])
                    on_fail(fdb, job, str(e))
                    fdb.commit()
                finally:
                    fdb.close()
        except Exception as e2:
            logger.warning("failure hook for job %s failed: %s", job["id"], e2)
    finally:
        stop_beat.set()
        db.close()
    return True


class Worker:
    def __init__(self, threads: int = 1, poll_seconds: float = 2.0):
        self.threads = max(1, threads)
        self.poll = poll_seconds
        self.stop_event = threading.Event()
        self.id = f"{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:6]}"
        self._threads: list[threading.Thread] = []

    def _loop(self, n: int):
        wid = f"{self.id}-{n}"
        while not self.stop_event.is_set():
            try:
                if n == 0:
                    reaped = queue.reap_expired()
                    if reaped:
                        logger.info("re-queued %d jobs with expired leases", reaped)
                if run_one(wid):
                    continue
            except Exception as e:  # never let the loop die
                logger.warning("worker loop error: %s", e)
            self.stop_event.wait(self.poll)

    def start(self):
        import app.jobs.handlers  # noqa: F401  (registers handlers)
        for n in range(self.threads):
            t = threading.Thread(target=self._loop, args=(n,), daemon=True, name=f"minddoc-worker-{n}")
            t.start()
            self._threads.append(t)
        logger.info("worker %s started with %d thread(s)", self.id, self.threads)
        return self

    def stop(self, timeout: float = 30.0):
        self.stop_event.set()
        for t in self._threads:
            t.join(timeout)
        logger.info("worker %s stopped", self.id)
