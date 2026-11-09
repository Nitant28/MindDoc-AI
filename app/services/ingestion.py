"""Ingestion orchestrator: parse → chunk → embed → analyse → graph → index."""
from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.ai import guardrails, knowledge
from app.core.config import settings
from app.database.models import Document, DocumentChunk
from app.ml import embeddings as emb
from app.ml import insights, retrieval
from app.services.document_service import ParsedDocument, parse_document

logger = logging.getLogger(__name__)


_V1_PAGE = re.compile(r"--- Page (\d+)")


class IngestionError(ValueError):
    pass


def ingest_bytes(db: Session, data: bytes, filename: str, tenant_id: int, owner_id: Optional[int] = None) -> Document:
    digest = hashlib.sha256(data).hexdigest()
    existing = db.query(Document).filter(Document.tenant_id == tenant_id, Document.content_hash == digest).first()
    if existing:
        logger.info("Duplicate upload of %s -> document %s", filename, existing.id)
        return existing
    parsed = parse_document(data, filename)
    doc = ingest_parsed(db, parsed, filename, tenant_id, owner_id, digest)
    try:  # keep the original so citations can be shown on the actual page
        folder = Path(settings.storage_dir) / str(tenant_id)
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{doc.id}{Path(filename).suffix.lower()[:10]}"
        path.write_bytes(data)
        doc.source_path = str(path)
        db.commit()
    except OSError as e:
        logger.warning("could not store original for doc %s: %s", doc.id, e)
    return doc


def ingest_parsed(db: Session, parsed: ParsedDocument, filename: str, tenant_id: int,
                  owner_id: Optional[int] = None, content_hash: Optional[str] = None) -> Document:
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

    doc = Document(filename=filename, content=text, tenant_id=tenant_id, owner_id=owner_id,
                   content_hash=content_hash, pages=len(parsed.pages), doc_type=doc_type,
                   doc_type_confidence=doc_conf, summary=summary, quality_score=vision.get("overall_quality"),
                   keywords_json=json.dumps(keywords), stats_json=json.dumps(stats),
                   vision_json=json.dumps(vision), pii_json=json.dumps(pii), security_json=json.dumps(flags))
    db.add(doc)
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

    retrieval.invalidate(tenant_id)
    logger.info("Ingested %s (%d pages, %d chunks, type=%s) in %.0f ms", filename, len(parsed.pages), len(chunks),
                doc_type, (time.perf_counter() - t0) * 1000)
    return doc


def delete_document(db: Session, doc: Document):
    if doc.source_path:
        try:
            Path(doc.source_path).unlink(missing_ok=True)
        except OSError:
            pass
    knowledge.remove_document(db, doc.tenant_id, doc.id)
    db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).delete(synchronize_session=False)
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
