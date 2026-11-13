"""Ingestion orchestrator: parse → chunk → embed → analyse → graph → index."""
from __future__ import annotations

import hashlib
from datetime import datetime
import json
import logging
import re
import time
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.ai import guardrails, knowledge
from app.core.config import settings
from app.database.models import Case, CaseDocument, Document, DocumentChunk
from app.ml import embeddings as emb
from app.ml import insights, retrieval
from app.services import statements
from app.services.document_service import ParsedDocument, parse_document, validate_upload

logger = logging.getLogger(__name__)


_V1_PAGE = re.compile(r"--- Page (\d+)")


class IngestionError(ValueError):
    pass


def _store_original(tenant_id: int, doc_id: int, filename: str, data: bytes) -> str:
    folder = Path(settings.storage_dir) / str(tenant_id)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{doc_id}{Path(filename).suffix.lower()[:10]}"
    path.write_bytes(data)
    return str(path)


def ensure_default_case(db: Session, tenant_id: int) -> Case:
    """Every tenant has a default "General" case so existing flows keep working (ADR-0012)."""
    case = db.query(Case).filter(Case.tenant_id == tenant_id, Case.is_default.is_(True)).first()
    if case is None:
        case = Case(tenant_id=tenant_id, title="General", is_default=True, status="open")
        db.add(case)
        db.flush()
    return case


def _link_case(db: Session, tenant_id: int, doc_id: int, case_id: Optional[int] = None) -> None:
    case_id = case_id or ensure_default_case(db, tenant_id).id
    if not db.get(CaseDocument, (case_id, doc_id)):
        db.add(CaseDocument(case_id=case_id, document_id=doc_id, tenant_id=tenant_id))


def ingest_bytes(db: Session, data: bytes, filename: str, tenant_id: int, owner_id: Optional[int] = None) -> Document:
    """Synchronous ingestion (used with ?wait=true and by tests): parse and index inside the request."""
    digest = hashlib.sha256(data).hexdigest()
    existing = db.query(Document).filter(Document.tenant_id == tenant_id, Document.content_hash == digest).first()
    if existing and existing.status == "completed":
        logger.info("Duplicate upload of %s -> document %s", filename, existing.id)
        return existing
    parsed = parse_document(data, filename)
    doc = ingest_parsed(db, parsed, filename, tenant_id, owner_id, digest, doc=existing)
    try:  # keep the original so citations can be shown on the actual page
        doc.source_path = _store_original(tenant_id, doc.id, filename, data)
        _link_case(db, tenant_id, doc.id)
        db.commit()
    except OSError as e:
        logger.warning("could not store original for doc %s: %s", doc.id, e)
    return doc


def register_upload(db: Session, data: bytes, filename: str, tenant_id: int, owner_id: Optional[int] = None,
                    case_id: Optional[int] = None) -> tuple[Document, bool]:
    """Asynchronous ingestion, step 1 (in the request): validate cheaply, de-duplicate, store the original and enqueue
    the processing job in the same transaction as the document row. Returns (document, newly_created)."""
    from app.jobs import queue
    digest = hashlib.sha256(data).hexdigest()
    existing = db.query(Document).filter(Document.tenant_id == tenant_id, Document.content_hash == digest).first()
    if existing:
        return existing, False
    validate_upload(data, filename)
    doc = Document(filename=filename, tenant_id=tenant_id, owner_id=owner_id, content_hash=digest,
                   status="queued", status_detail="waiting for a worker")
    db.add(doc)
    db.flush()
    doc.source_path = _store_original(tenant_id, doc.id, filename, data)
    _link_case(db, tenant_id, doc.id, case_id)
    queue.enqueue(db, tenant_id, "ingest_document", {"document_id": doc.id}, idempotency_key=f"ingest:{digest}",
                  subject_id=doc.id)
    db.commit()
    return doc, True


def process_document(db: Session, doc_id: int, job_id: Optional[int] = None) -> Document:
    """Asynchronous ingestion, step 2 (in a worker, tenant-bound session). Safe to repeat."""
    from app.jobs import queue
    doc = db.get(Document, doc_id)
    if doc is None:
        raise FileNotFoundError(f"document {doc_id} not found for this tenant")
    if doc.status == "completed" and db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).count():
        return doc  # a repeated job after a crash between commit and completion
    doc.status, doc.status_detail = "processing", "parsing"
    db.commit()
    if job_id:
        queue.set_progress(job_id, "parsing", doc.filename)
    if not doc.source_path or not Path(doc.source_path).exists():
        raise FileNotFoundError("original file is missing; upload it again")
    data = Path(doc.source_path).read_bytes()
    parsed = parse_document(data, doc.filename)
    if job_id:
        queue.set_progress(job_id, "indexing", f"{len(parsed.pages)} pages")
    return ingest_parsed(db, parsed, doc.filename, doc.tenant_id, doc.owner_id, doc.content_hash, doc=doc)


def ingest_parsed(db: Session, parsed: ParsedDocument, filename: str, tenant_id: int,
                  owner_id: Optional[int] = None, content_hash: Optional[str] = None,
                  doc: Optional[Document] = None) -> Document:
    """Analyse and index a parsed document. With `doc`, fills that existing row (async path), replacing any partial
    results from an earlier attempt so a retried job never duplicates chunks or graph rows."""
    t0 = time.perf_counter()
    text = parsed.text
    if len(text.strip()) < 10:
        raise IngestionError("Could not extract text from document. Try a higher quality file.")

    chunks = insights.chunk_pages([(p.number, p.text) for p in parsed.pages])
    vectors, model_name = emb.embed([c for _, c in chunks])

    plain = "\n\n".join(p.text for p in parsed.pages if p.text.strip())  # no page markers for analytics
    doc_type, doc_conf = insights.classify_document(plain)
    summary = insights.llm_summary(plain) or insights.extractive_summary(plain)
    keywords = insights.extract_keywords([c for _, c in chunks])
    pii = guardrails.pii_summary(text)
    flags = guardrails.detect_injection(text)
    vision = parsed.vision
    stats = insights.text_stats(text, len(parsed.pages), len(chunks))

    fields = dict(filename=filename, content=text, tenant_id=tenant_id, owner_id=owner_id,
                  content_hash=content_hash, pages=len(parsed.pages), doc_type=doc_type,
                  doc_type_confidence=doc_conf, summary=summary, quality_score=vision.get("overall_quality"),
                  keywords_json=json.dumps(keywords), stats_json=json.dumps(stats),
                  vision_json=json.dumps(vision), pii_json=json.dumps(pii), security_json=json.dumps(flags),
                  status="completed", status_detail=None)
    if doc is None:
        doc = Document(**fields)
        db.add(doc)
        db.flush()
    else:
        knowledge.remove_document(db, tenant_id, doc.id)
        db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).delete(synchronize_session=False)
        statements.clear(db, doc.id)  # re-processing invalidates the stored statement analysis
        for k, v in fields.items():
            setattr(doc, k, v)
        db.flush()

    rows = []
    for i, ((page, chunk_text), vec) in enumerate(zip(chunks, vectors)):
        row = DocumentChunk(document_id=doc.id, chunk_text=chunk_text, page=page, chunk_index=i,
                            embedding=json.dumps([round(float(x), 6) for x in vec]), embedding_model=model_name)
        db.add(row)
        rows.append(row)
    db.commit()

    try:
        g = knowledge.build_graph_for_document(db, tenant_id, doc.id, rows, text)
        logger.info("Graph for doc %s: %s", doc.id, g)
    except Exception as e:
        db.rollback()
        logger.warning("Graph extraction failed for doc %s: %s", doc.id, e)

    if filename.lower().endswith(".pdf") and statements.looks_like_statement(plain):
        _queue_statement_analysis(db, doc)

    retrieval.invalidate(tenant_id)
    logger.info("Ingested %s (%d pages, %d chunks, type=%s) in %.0f ms", filename, len(parsed.pages), len(chunks),
                doc_type, (time.perf_counter() - t0) * 1000)
    return doc


def _queue_statement_analysis(db: Session, doc: Document) -> None:
    """Statement-like PDFs get a background statement analysis (ADR-0011); failures never fail the ingestion."""
    from app.jobs import queue
    try:
        queue.enqueue(db, doc.tenant_id, "analyse_statement", {"document_id": doc.id},
                      idempotency_key=f"statement:{doc.id}:{doc.content_hash}:{statements.engine_version()}",
                      subject_id=doc.id, max_attempts=2)
        db.commit()
    except Exception as e:  # pragma: no cover - queueing is best-effort here
        db.rollback()
        logger.warning("could not queue statement analysis for doc %s: %s", doc.id, e)


def delete_document(db: Session, doc: Document):
    if doc.source_path:
        try:
            Path(doc.source_path).unlink(missing_ok=True)
        except OSError:
            pass
    knowledge.remove_document(db, doc.tenant_id, doc.id)
    db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).delete(synchronize_session=False)
    statements.clear(db, doc.id)
    from app.database.models import Claim, PartyMention
    db.query(PartyMention).filter(PartyMention.document_id == doc.id).delete(synchronize_session=False)
    # claims built on this document stop being current; their versions stay in the history (ADR-0004)
    db.query(Claim).filter(Claim.subject_document_id == doc.id, Claim.superseded_at.is_(None)).update(
        {Claim.superseded_at: datetime.utcnow(), Claim.supersede_reason: "source document deleted"},
        synchronize_session=False)
    db.delete(doc)
    db.commit()
    retrieval.invalidate(doc.tenant_id)


def document_detail(db: Session, doc: Document) -> dict:
    stats = doc.stats or {}
    if not stats:
        n_chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).count()
        stats = insights.text_stats(doc.content or "", doc.pages or 1, n_chunks)
    return {
        "id": doc.id, "filename": doc.filename, "created_at": doc.created_at,
        "doc_type": doc.doc_type, "doc_type_confidence": doc.doc_type_confidence,
        "summary": doc.summary, "keywords": doc.keywords,
        "entities": knowledge.document_entities(db, doc.id),
        "pii": doc.pii, "security_flags": doc.security_flags, "vision": doc.vision,
        "stats": stats, "preview": (doc.content or "")[:1000], "pages": doc.pages,
        "quality_score": doc.quality_score,
    }


def backfill_insights(db: Session, doc: Document) -> bool:
    """Compute v2 analytics for a document uploaded before v2 (cheap, no LLM calls)."""
    if doc.doc_type:
        return False
    text = doc.content or ""
    chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).order_by(DocumentChunk.id).all()
    current_page = 1
    for i, c in enumerate(chunks):
        if c.chunk_index is None:
            c.chunk_index = i
        if c.page is None:  # infer pages from v1 "--- Page N ---" markers so citations get page numbers
            marks = [int(m) for m in _V1_PAGE.findall(c.chunk_text or "")]
            starts_with_mark = bool(_V1_PAGE.match((c.chunk_text or "").lstrip()))
            c.page = marks[0] if marks and starts_with_mark else current_page
            if marks:
                current_page = marks[-1]
    doc.doc_type, doc.doc_type_confidence = insights.classify_document(text)
    doc.summary = doc.summary or insights.extractive_summary(text)
    doc.keywords_json = json.dumps(insights.extract_keywords([c.chunk_text or "" for c in chunks]))
    doc.pii_json = json.dumps(guardrails.pii_summary(text))
    doc.security_json = json.dumps(guardrails.detect_injection(text))
    pages = max(1, text.count("--- Page "))
    doc.pages = doc.pages or pages
    doc.stats_json = json.dumps(insights.text_stats(text, doc.pages, len(chunks)))
    db.commit()
    try:
        knowledge.build_graph_for_document(db, doc.tenant_id, doc.id, chunks, text, use_llm=False)
    except Exception as e:
        db.rollback()
        logger.warning("graph backfill failed for %s: %s", doc.id, e)
    return True
