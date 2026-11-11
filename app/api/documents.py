import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.ai.extraction import extract_fields
from app.api.deps import enforce_rate, get_current_user
from app.core.config import settings
from app.core.security import query_limiter, upload_limiter
from app.database.models import Case, Document, DocumentChunk, Job, SavedItem, get_db
from app.services import ingestion
from app.services.document_service import ALLOWED_EXT
from app.vision import highlight

router = APIRouter()
logger = logging.getLogger(__name__)


def _own_doc(db: Session, doc_id: int, user) -> Document:
    doc = db.query(Document).filter(Document.id == doc_id, Document.tenant_id == user.tenant_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.post("/upload")
def upload_document(response: Response, file: UploadFile = File(...), wait: bool = False,
                    case_id: Optional[int] = None, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Upload a document. Default: validated, stored and queued (HTTP 202) — poll GET /{id}/status. With
    ?wait=true (or ASYNC_INGESTION=false) it is processed inside the request and the analysis is returned."""
    enforce_rate(upload_limiter, user)
    filename = file.filename or "uploaded"
    if not filename.lower().endswith(ALLOWED_EXT):
        raise HTTPException(status_code=400,
                            detail=f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXT)}. Got: {filename}")
    data = file.file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.max_upload_mb} MB")
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if case_id is not None and not db.query(Case).filter(Case.id == case_id, Case.tenant_id == user.tenant_id).first():
        raise HTTPException(status_code=404, detail="Case not found")
    if settings.async_ingestion and not wait:
        try:
            doc, created = ingestion.register_upload(db, data, filename, user.tenant_id, user.id, case_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        response.status_code = 202 if doc.status != "completed" else 200
        return {"message": "Document queued for processing" if created else "Document already uploaded",
                "document_id": doc.id, "filename": doc.filename, "status": doc.status,
                "status_url": f"/api/documents/{doc.id}/status",
                "analysis": ingestion.document_detail(db, doc) if doc.status == "completed" else None}
    try:
        doc = ingestion.ingest_bytes(db, data, filename, user.tenant_id, user.id)
    except ingestion.IngestionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Ingestion failed for %s: %s", filename, e)
        raise HTTPException(status_code=500, detail="Failed to process document")
    return {"message": "Document uploaded successfully", "document_id": doc.id, "filename": doc.filename,
            "status": doc.status, "characters_extracted": len(doc.content or ""),
            "preview": (doc.content or "")[:200], "analysis": ingestion.document_detail(db, doc)}


@router.post("/import-aa")
def import_account_aggregator(file: UploadFile = File(...), consent_ref: Optional[str] = Form(None),
                              db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Import a decrypted Account Aggregator deposit FI payload (ReBIT schema, JSON or XML) that the customer already
    holds (ADR-0015). MindDoc does not request consent or fetch data from an AA. `consent_ref` records the consent
    artefact reference for provenance. Invalid payloads are rejected with the schema reason (HTTP 400)."""
    from app.finance.aa import AAError
    from app.services import statements
    enforce_rate(upload_limiter, user)
    filename = file.filename or "aa-deposit.json"
    if not filename.lower().endswith(statements.AA_EXT):
        raise HTTPException(status_code=400, detail="Account Aggregator data must be a .json or .xml file")
    data = file.file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.max_upload_mb} MB")
    ref = (consent_ref or "").strip()[:200] or None
    try:
        doc, created = statements.import_aa(db, data, filename, user.tenant_id, user.id, ref)
    except AAError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Not a valid ReBIT deposit payload: {e}")
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    stmt = statements.get_or_analyse(db, doc)
    return {"message": "Imported" if created else "This payload was already imported", "document_id": doc.id,
            "created": created, "status": stmt.status, "transactions": stmt.n_txns,
            "warnings": json.loads(stmt.warnings or "[]")}


@router.get("/{doc_id}/status")
def document_status(doc_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Processing state for the Upload page and Processing Monitor."""
    doc = _own_doc(db, doc_id, user)
    job = (db.query(Job).filter(Job.tenant_id == user.tenant_id, Job.kind == "ingest_document",
                                Job.subject_id == doc.id).order_by(Job.id.desc()).first())
    return {"document_id": doc.id, "filename": doc.filename, "status": doc.status, "detail": doc.status_detail,
            "job": None if job is None else {
                "id": job.id, "state": job.state, "attempts": job.attempts, "max_attempts": job.max_attempts,
                "progress": json.loads(job.progress) if job.progress else None,
                "last_error": (job.last_error or "").split("\n")[0][:500] or None,
                "updated_at": job.updated_at}}


@router.get("/{doc_id}/statement")
def statement_analysis(doc_id: int, refresh: bool = False, db: Session = Depends(get_db),
                       user=Depends(get_current_user)):
    """Bank-statement view (ADR-0011): transactions, reconciliation checks and diagnoses for a text-layer PDF.

    Served from the stored analysis; computed on first request (or `refresh=true`, or after an engine upgrade).
    Values are never altered to make balances reconcile."""
    from app.services import statements
    enforce_rate(query_limiter, user)
    doc = _own_doc(db, doc_id, user)
    try:
        stmt = statements.get_or_analyse(db, doc, refresh=refresh)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.exception("statement analysis failed for %s: %s", doc_id, e)
        raise HTTPException(status_code=500, detail="Statement analysis failed")
    return statements.payload(db, stmt)


@router.get("/{doc_id}/identifiers")
def document_identifiers(doc_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """PAN, GSTIN and IFSC values found in the document, each with a structural check against the official layout
    (sources cited per identifier). Check digits the official sources do not publish are listed as not verified."""
    from app.finance.identifiers import find_identifiers
    doc = _own_doc(db, doc_id, user)
    return {"document_id": doc.id, "identifiers": find_identifiers(doc.content or ""),
            "note": "Structure only: a well-formed identifier is not proof that it was issued or belongs to the named "
                    "party; a malformed one is a data-quality signal for review."}


@router.post("/{doc_id}/reprocess")
def reprocess_document(doc_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Queue a fresh processing run (e.g. after a failure or a parser upgrade)."""
    from app.jobs import queue
    enforce_rate(upload_limiter, user)
    doc = _own_doc(db, doc_id, user)
    if (doc.filename or "").lower().endswith((".json", ".xml")):
        raise HTTPException(status_code=422, detail="Imported Account Aggregator data is not re-parsed; "
                                                    "use statement refresh to re-run reconciliation")
    if doc.status in ("queued", "processing"):
        raise HTTPException(status_code=409, detail=f"Document is already {doc.status}")
    doc.status, doc.status_detail = "queued", "reprocessing requested"
    job = queue.enqueue(db, user.tenant_id, "ingest_document", {"document_id": doc.id},
                        idempotency_key=f"reprocess:{doc.id}:{datetime.utcnow().isoformat()}", subject_id=doc.id)
    db.commit()
    return {"document_id": doc.id, "status": doc.status, "job_id": job.id}


@router.get("/list")
def list_documents(db: Session = Depends(get_db), user=Depends(get_current_user)):
    counts = dict(db.query(DocumentChunk.document_id, func.count(DocumentChunk.id))
                  .join(Document, Document.id == DocumentChunk.document_id)
                  .filter(Document.tenant_id == user.tenant_id).group_by(DocumentChunk.document_id).all())
    docs = db.query(Document).filter(Document.tenant_id == user.tenant_id).order_by(Document.id.desc()).all()
    return [{"id": d.id, "filename": d.filename, "created_at": d.created_at, "doc_type": d.doc_type,
             "summary": (d.summary or "")[:300] or None, "pages": d.pages, "chunk_count": counts.get(d.id, 0),
             "quality_score": d.quality_score, "pii_count": (d.pii or {}).get("count", 0),
             "status": d.status or "completed", "status_detail": d.status_detail} for d in docs]


@router.get("/{doc_id}")
def get_document(doc_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    doc = _own_doc(db, doc_id, user)
    ingestion.backfill_insights(db, doc)
    return ingestion.document_detail(db, doc)


@router.get("/{doc_id}/page/{page}/image")
def page_image(doc_id: int, page: int, chunk_id: Optional[int] = None, box: Optional[str] = None,
               db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Rendered page with the cited chunk highlighted (pixel-level citation). `box=x0,top,x1,bottom` (tenths of a
    point, as returned by /statement) highlights an exact region instead, e.g. one transaction row."""
    doc = _own_doc(db, doc_id, user)
    src = Path(doc.source_path) if doc.source_path else None
    if not src or not src.is_file() or src.suffix.lower() != ".pdf":
        raise HTTPException(status_code=404, detail="Original page not available for this document")
    if box:
        try:
            x0, top, x1, bottom = (int(v) for v in box.split(","))
        except ValueError:
            raise HTTPException(status_code=422, detail="box must be four integers: x0,top,x1,bottom")
        try:
            png, n = highlight.render_pdf_page_boxes(str(src), page, [(x0 / 10, top / 10, x1 / 10, bottom / 10)])
        except IndexError:
            raise HTTPException(status_code=404, detail="Page not found")
        return Response(content=png, media_type="image/png",
                        headers={"X-Highlight-Boxes": str(n), "Access-Control-Expose-Headers": "X-Highlight-Boxes",
                                 "Cache-Control": "private, max-age=300"})
    passage = None
    if chunk_id:
        chunk = db.query(DocumentChunk).filter(DocumentChunk.id == chunk_id,
                                               DocumentChunk.document_id == doc.id).first()
        passage = chunk.chunk_text if chunk else None
    try:
        png, n = highlight.render_pdf_page(str(src), page, passage)
    except IndexError:
        raise HTTPException(status_code=404, detail="Page not found")
    return Response(content=png, media_type="image/png",
                    headers={"X-Highlight-Boxes": str(n), "Access-Control-Expose-Headers": "X-Highlight-Boxes",
                             "Cache-Control": "private, max-age=300"})


class ExtractRequest(BaseModel):
    fields: dict[str, str]


@router.post("/{doc_id}/extract")
def extract(doc_id: int, request: ExtractRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    enforce_rate(query_limiter, user)
    doc = _own_doc(db, doc_id, user)
    if not request.fields or len(request.fields) > 30:
        raise HTTPException(status_code=400, detail="Provide 1-30 fields")
    try:
        return extract_fields(db, doc, request.fields)
    except Exception as e:
        logger.exception("extraction failed: %s", e)
        raise HTTPException(status_code=502, detail=f"Extraction failed: {e}")


@router.delete("/delete/{doc_id}")
def delete_document(doc_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    ingestion.delete_document(db, _own_doc(db, doc_id, user))
    return {"message": "Document deleted"}


@router.put("/edit/{doc_id}")
def edit_document(doc_id: int, filename: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    doc = _own_doc(db, doc_id, user)
    doc.filename = filename.strip()[:255] or doc.filename
    db.commit()
    return {"id": doc.id, "filename": doc.filename}


@router.post("/save/{doc_id}")
def save_document(doc_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    doc = _own_doc(db, doc_id, user)
    db.add(SavedItem(user_id=user.id, item_type="document", title=doc.filename,
                     content=(doc.summary or doc.content or "")[:1000]))
    db.commit()
    return {"message": "Document saved"}
