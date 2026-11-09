import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.ai.extraction import extract_fields
from app.api.deps import enforce_rate, get_current_user
from app.core.config import settings
from app.core.security import query_limiter, upload_limiter
from app.database.models import Document, DocumentChunk, SavedItem, get_db
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
def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db), user=Depends(get_current_user)):
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
            "characters_extracted": len(doc.content or ""), "preview": (doc.content or "")[:200],
            "analysis": ingestion.document_detail(db, doc)}


@router.get("/list")
def list_documents(db: Session = Depends(get_db), user=Depends(get_current_user)):
    counts = dict(db.query(DocumentChunk.document_id, func.count(DocumentChunk.id))
                  .join(Document, Document.id == DocumentChunk.document_id)
                  .filter(Document.tenant_id == user.tenant_id).group_by(DocumentChunk.document_id).all())
    docs = db.query(Document).filter(Document.tenant_id == user.tenant_id).order_by(Document.id.desc()).all()
    return [{"id": d.id, "filename": d.filename, "created_at": d.created_at, "doc_type": d.doc_type,
             "summary": (d.summary or "")[:300] or None, "pages": d.pages, "chunk_count": counts.get(d.id, 0),
             "quality_score": d.quality_score, "pii_count": (d.pii or {}).get("count", 0)} for d in docs]


@router.get("/{doc_id}")
def get_document(doc_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    doc = _own_doc(db, doc_id, user)
    ingestion.backfill_insights(db, doc)
    return ingestion.document_detail(db, doc)


@router.get("/{doc_id}/page/{page}/image")
def page_image(doc_id: int, page: int, chunk_id: Optional[int] = None, db: Session = Depends(get_db),
               user=Depends(get_current_user)):
    """Rendered page with the cited chunk highlighted (pixel-level citation)."""
    doc = _own_doc(db, doc_id, user)
    src = Path(doc.source_path) if doc.source_path else None
    if not src or not src.is_file() or src.suffix.lower() != ".pdf":
        raise HTTPException(status_code=404, detail="Original page not available for this document")
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
