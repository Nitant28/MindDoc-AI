import os
import json
import numpy as np
import faiss
from app.database.models import DocumentChunk, Document
from sqlalchemy.orm import Session

FAISS_INDEX_PATH = os.path.join(os.path.dirname(__file__), '..', 'indexes', 'faiss.index')
FAISS_META_PATH = os.path.join(os.path.dirname(__file__), '..', 'indexes', 'faiss_meta.json')


def ensure_indexes_dir():
    root = os.path.dirname(FAISS_INDEX_PATH)
    os.makedirs(root, exist_ok=True)


from typing import Optional


def build_faiss_index(db: Session, tenant_id: int, document_id: Optional[int] = None):
    ensure_indexes_dir()

    query = db.query(DocumentChunk).join(Document).filter(Document.tenant_id == tenant_id)
    if document_id:
        query = query.filter(Document.id == document_id)
    chunks = query.all()

    if not chunks:
        return False

    vectors = []
    ids = []
    meta = {}

    for i, chunk in enumerate(chunks):
        try:
            emb = json.loads(str(chunk.embedding))
            if isinstance(emb, list) and all(isinstance(x, (float, int)) for x in emb):
                vec = np.array(emb, dtype=np.float32)
                vectors.append(vec)
                ids.append(i)
                meta[i] = {
                    'chunk_id': chunk.id,
                    'document_id': chunk.document_id,
                    'text': chunk.chunk_text,
                }
        except Exception:
            continue

    if not vectors:
        return False

    dim = vectors[0].shape[0]
    matrix = np.vstack(vectors)
    faiss.normalize_L2(matrix)

    index = faiss.IndexFlatIP(dim)
    id_index = faiss.IndexIDMap(index)
    id_index.add_with_ids(matrix, np.array(ids, dtype=np.int64))

    faiss.write_index(id_index, FAISS_INDEX_PATH)
    with open(FAISS_META_PATH, 'w', encoding='utf-8') as f:
        json.dump(meta, f)

    return True


def load_faiss_index():
    if not os.path.exists(FAISS_INDEX_PATH) or not os.path.exists(FAISS_META_PATH):
        return None, None

    index = faiss.read_index(FAISS_INDEX_PATH)
    with open(FAISS_META_PATH, 'r', encoding='utf-8') as f:
        meta = json.load(f)
    return index, meta


def faiss_search(query_embedding, top_k=20):
    index, meta = load_faiss_index()
    if index is None or meta is None:
        return []

    vec = np.array(query_embedding, dtype=np.float32).reshape(1, -1)
    faiss.normalize_L2(vec)
    dists, ids = index.search(vec, top_k)

    results = []
    for dist, idx in zip(dists[0], ids[0]):
        if idx == -1:
            continue
        item = meta.get(str(int(idx))) if isinstance(meta, dict) else meta.get(idx)
        if item:
            results.append((item, float(dist)))
    return results
