"""Standalone worker process: `python -m app.worker` (production topology, ADR-0013). Stops cleanly on SIGINT/SIGTERM."""
import logging
import signal
import sys
import threading

from app.core.config import settings
from app.database.models import create_tables
from app.jobs.worker import Worker

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s", stream=sys.stdout)
    create_tables()
    w = Worker(threads=settings.worker_threads).start()
    done = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, lambda *_: done.set())
        except (ValueError, OSError):
            pass
    done.wait()
    w.stop()
