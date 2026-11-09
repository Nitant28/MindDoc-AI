"""v1 compatibility shim. New code should use app.ai.rag directly."""
from sqlalchemy.orm import Session

from app.ai import rag
from app.ml.retrieval import get_index


def load_vector_store(db: Session, tenant_id: int, document_id: int = None):
    return {"db": db, "tenant_id": tenant_id, "document_ids": [document_id] if document_id else [],
            "index": get_index(db, tenant_id)}


def query_rag(vector_store, query: str, use_tools: bool = False) -> str:
    if not vector_store:
        raise ValueError("vector_store is required (use load_vector_store)")
    final = rag.answer(vector_store["db"], tenant_id=vector_store["tenant_id"], user_id=0, query=query,
                       document_ids=vector_store["document_ids"])
    return final.get("answer") or final.get("detail", "")
