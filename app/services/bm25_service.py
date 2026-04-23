import os
import json
from app.database.models import DocumentChunk, Document
from sqlalchemy.orm import Session

BM25_INDEX_PATH = os.path.join(os.path.dirname(__file__), '..', 'indexes', 'bm25.json')


def tokenize(text):
    return text.lower().split()


from typing import Optional


def build_bm25_index(db: Session, tenant_id: int, document_id: Optional[int] = None):
    query = db.query(DocumentChunk).join(Document).filter(Document.tenant_id == tenant_id)
    if document_id:
        query = query.filter(Document.id == document_id)
    chunks = query.all()

    if not chunks:
        return False

    docs = [chunk.chunk_text for chunk in chunks]
    tokens = [tokenize(d) for d in docs]

    try:
        from rank_bm25 import BM25Okapi
    except ImportError:
        return False

    bm25 = BM25Okapi(tokens)
    serializable = {
        'documents': docs,
        'doc_ids': [chunk.id for chunk in chunks],
        'tokenized': tokens,
    }
    with open(BM25_INDEX_PATH, 'w', encoding='utf-8') as f:
        json.dump(serializable, f)
    return True


def load_bm25_index():
    if not os.path.exists(BM25_INDEX_PATH):
        return None
    with open(BM25_INDEX_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    try:
        from rank_bm25 import BM25Okapi
    except ImportError:
        return None
    bm25 = BM25Okapi(data['tokenized'])
    return bm25, data['doc_ids'], data['documents']


def bm25_search(query, top_k=20):
    loaded = load_bm25_index()
    if not loaded:
        return []
    bm25, doc_ids, docs = loaded
    if bm25 is None:
        return []
    query_tokens = tokenize(query)
    scores = bm25.get_scores(query_tokens)
    ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:top_k]
    results = []
    for idx, score in ranked:
        results.append(({
            'chunk_id': doc_ids[idx],
            'text': docs[idx],
        }, float(score)))
    return results
