"""Job handlers. Each receives a tenant-bound session and the claimed job dict; it must be safe to run twice."""
from __future__ import annotations

from app.jobs import queue
from app.jobs.worker import handler


@handler("ingest_document")
def ingest_document(db, job):
    from app.services import ingestion
    doc_id = job["payload"]["document_id"]
    try:
        ingestion.process_document(db, doc_id, job_id=job["id"])
    except (ingestion.IngestionError, ValueError, FileNotFoundError) as e:
        raise queue.PermanentJobError(str(e)) from e


@handler("ingest_document:failed")
def ingest_failed(db, job, error):
    from app.database.models import Document
    doc = db.get(Document, job["payload"]["document_id"])
    if doc is not None:
        doc.status = "failed"
        doc.status_detail = error[:2000]


@handler("analyse_statement")
def analyse_statement(db, job):
    from app.database.models import Document
    from app.services import statements
    doc = db.get(Document, job["payload"]["document_id"])
    if doc is None:
        return  # deleted meanwhile
    try:
        statements.analyse(db, doc)
    except (ValueError, FileNotFoundError) as e:
        raise queue.PermanentJobError(str(e)) from e
