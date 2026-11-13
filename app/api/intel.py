import json
from typing import Optional

import numpy as np
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.ai import knowledge, llm
from app.api.deps import enforce_rate, get_current_user
from app.core.security import eval_limiter
from app.core.config import settings
from app.database.models import CoMention, Document, Entity, QueryLog, Relation, get_db
from app.ml import embeddings as emb
from app.ml import evaluation, insights
from app.ml.retrieval import get_index
from app.vision import cv

router = APIRouter()


@router.get("/graph")
def graph(document_id: Optional[int] = None, limit: int = 150, db: Session = Depends(get_db),
          user=Depends(get_current_user)):
    return knowledge.graph(db, user.tenant_id, document_id, max(10, min(limit, 500)))


@router.get("/overview")
def overview(db: Session = Depends(get_db), user=Depends(get_current_user)):
    tid = user.tenant_id
    docs = db.query(Document).filter(Document.tenant_id == tid).all()
    index = get_index(db, tid)
    doc_types: dict[str, int] = {}
    for d in docs:
        doc_types[d.doc_type or "unclassified"] = doc_types.get(d.doc_type or "unclassified", 0) + 1

    topics = []
    if index.has_vectors and len(docs) >= 3:
        content = {d.id: d.content or "" for d in docs}
        doc_vecs = index.document_vectors()
        ids = list(doc_vecs)
        if len(ids) >= 3:
            topics = insights.discover_topics(ids, np.vstack([doc_vecs[i] for i in ids]),
                                              [content.get(i, "") for i in ids])

    q = db.query(QueryLog).filter(QueryLog.tenant_id == tid)
    agg = q.with_entities(func.count(QueryLog.id), func.avg(QueryLog.latency_ms), func.avg(QueryLog.confidence)).one()
    recent = q.order_by(QueryLog.id.desc()).limit(10).all()
    return {
        "documents": len(docs), "chunks": index.size, "retrieval_backend": index.backend,
        "entities": db.query(func.count(Entity.id)).filter(Entity.tenant_id == tid).scalar() or 0,
        "relations": db.query(func.count(Relation.id)).filter(Relation.tenant_id == tid,
                                                              Relation.relation != "co_occurs").scalar() or 0,
        "co_mentions": db.query(func.count(CoMention.id)).filter(CoMention.tenant_id == tid).scalar() or 0,
        "queries": int(agg[0] or 0), "avg_latency_ms": int(agg[1] or 0),
        "avg_confidence": round(float(agg[2]), 3) if agg[2] is not None else None,
        "pii_total": sum((d.pii or {}).get("count", 0) for d in docs),
        "doc_types": doc_types, "topics": topics,
        "recent_queries": [{"query": r.query, "confidence": r.confidence, "latency_ms": r.latency_ms,
                            "provider": r.provider, "grounded": bool(r.grounded), "created_at": r.created_at}
                           for r in recent],
    }


@router.get("/timeline")
def timeline(document_id: Optional[int] = None, upcoming_days: Optional[int] = None, db: Session = Depends(get_db),
             user=Depends(get_current_user)):
    return knowledge.timeline(db, user.tenant_id, document_id, upcoming_days)


@router.get("/audit")
def audit(limit: int = 50, db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = (db.query(QueryLog).filter(QueryLog.tenant_id == user.tenant_id)
            .order_by(QueryLog.id.desc()).limit(max(1, min(limit, 500))).all())
    out = []
    for r in rows:
        try:
            chunk_ids = json.loads(r.chunk_ids_json) if r.chunk_ids_json else []
        except ValueError:
            chunk_ids = []
        out.append({"id": r.id, "created_at": r.created_at, "user_id": r.user_id, "query": r.query, "mode": r.mode,
                    "provider": r.provider, "model": r.model, "latency_ms": r.latency_ms, "confidence": r.confidence,
                    "grounded": bool(r.grounded), "n_citations": r.n_citations, "prompt_hash": r.prompt_hash,
                    "chunk_ids": chunk_ids})
    return out


class EvalRequest(BaseModel):
    sample_size: int = 20
    use_llm: bool = True


@router.post("/eval")
def run_eval(request: Optional[EvalRequest] = None, db: Session = Depends(get_db), user=Depends(get_current_user)):
    enforce_rate(eval_limiter, user)
    request = request or EvalRequest()
    return evaluation.evaluate(db, user.tenant_id, max(3, min(request.sample_size, 100)), request.use_llm)


@router.get("/capabilities")
def capabilities():
    return {
        "llm_providers": llm.available_providers(),
        "embeddings": emb.active_model_name() + ("" if emb.active_model_name() != emb.HASHING_MODEL_NAME
                                                  else " (offline fallback)"),
        "reranker": emb.reranker_available(), "reranker_model": settings.reranker_model if settings.enable_reranker else None,
        "opencv": cv.CV2, "ocr_engines": cv.ocr_engines(), "vision_llm": llm.has_vision_llm(),
        "retrieval": "hybrid BM25 + dense, RRF fusion, cross-encoder rerank, MMR, GraphRAG-lite",
    }
