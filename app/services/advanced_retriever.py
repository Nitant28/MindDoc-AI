import json
import logging
from typing import Optional, List, Tuple, Dict

import numpy as np

from app.services.faiss_service import faiss_search, build_faiss_index
from app.services.bm25_service import bm25_search, build_bm25_index
from app.database.models import DocumentChunk, Document
from sqlalchemy.orm import Session


logger = logging.getLogger(__name__)


class DocumentProxy:
    def __init__(self, page_content: str, chunk_id: int, score: float = 0.0, source: str = 'hybrid'):
        self.page_content = page_content
        self.chunk_id = chunk_id
        self.score = score
        self.source = source


class AdvancedRetriever:
    def __init__(self, db: Optional[Session] = None, tenant_id: Optional[int] = None, document_id: Optional[int] = None,
                 embedding_model_name: str = 'all-MiniLM-L6-v2', cross_encoder_name: str = 'cross-encoder/ms-marco-MiniLM-L-6-v2'):
        self.db = db
        self.tenant_id = tenant_id
        self.document_id = document_id
        self.embedding_model_name = embedding_model_name
        self.cross_encoder_name = cross_encoder_name

        self.embedding_model = None
        self.cross_encoder = None

        self._init_models()

    def _init_models(self):
        try:
            from sentence_transformers import SentenceTransformer
            self.embedding_model = SentenceTransformer(self.embedding_model_name)
            logger.info(f"Loaded embedding model: {self.embedding_model_name}")
        except Exception as e:
            logger.warning(f"Could not load embedding model {self.embedding_model_name}: {e}")
            self.embedding_model = None

        try:
            from sentence_transformers import CrossEncoder
            self.cross_encoder = CrossEncoder(self.cross_encoder_name)
            logger.info(f"Loaded cross-encoder model: {self.cross_encoder_name}")
        except Exception as e:
            logger.warning(f"Could not load cross-encoder model {self.cross_encoder_name}: {e}")
            self.cross_encoder = None

    def as_retriever(self):
        return self

    def build_indexes(self):
        if self.db is None or self.tenant_id is None:
            return False
        faiss_ok = build_faiss_index(self.db, self.tenant_id, self.document_id)
        bm25_ok = build_bm25_index(self.db, self.tenant_id, self.document_id)
        return bool(faiss_ok or bm25_ok)

    def _get_db_chunks(self) -> List[DocumentChunk]:
        if not self.db or not self.tenant_id:
            return []
        query = self.db.query(DocumentChunk).join(Document).filter(Document.tenant_id == self.tenant_id)
        if self.document_id:
            query = query.filter(Document.id == self.document_id)
        return query.all()

    def _merge_candidates(self, faiss_res, bm25_res, query_text: Optional[str] = None, top_k: int = 20, alpha: float = 0.6):
        hybrid = {}

        for item, score in faiss_res:
            chunk_id = int(item.get('chunk_id')) if item and item.get('chunk_id') is not None else -1
            if chunk_id < 0:
                continue
            try:
                score_val = float(score)
            except Exception:
                score_val = 0.0
            hybrid[chunk_id] = {'score': score_val, 'text': item.get('text', ''), 'source': 'faiss'}

        for item, score in bm25_res:
            chunk_id = int(item.get('chunk_id')) if item and item.get('chunk_id') is not None else -1
            if chunk_id < 0:
                continue
            if chunk_id in hybrid:
                existing_score = hybrid[chunk_id].get('score', 0.0)
                try:
                    existing_score = float(existing_score)
                except Exception:
                    existing_score = 0.0
                try:
                    score_val = float(score)
                except Exception:
                    score_val = 0.0
                hybrid[chunk_id]['score'] = float(alpha * existing_score + (1 - alpha) * score_val)
                hybrid[chunk_id]['source'] = 'hybrid'
            else:
                try:
                    score_val = float(score)
                except Exception:
                    score_val = 0.0
                hybrid[chunk_id] = {'score': score_val, 'text': item.get('text', ''), 'source': 'bm25'}

        merged = []
        for k, v in hybrid.items():
            score_value = v.get('score', 0.0)
            try:
                score_value = float(score_value)
            except Exception:
                score_value = 0.0
            merged.append({
                'chunk_id': int(k),
                'text': str(v.get('text', '')),
                'score': score_value,
                'source': str(v.get('source', 'hybrid'))
            })

        merged.sort(key=lambda x: x['score'], reverse=True)
        merged = merged[:top_k]

        if self.cross_encoder and merged and query_text:
            pair_list = [[query_text, d['text']] for d in merged]
            try:
                rerank_scores = self.cross_encoder.predict(pair_list)
                for d, s in zip(merged, rerank_scores):
                    d['score'] = float(s)
                merged.sort(key=lambda x: x['score'], reverse=True)
            except Exception as e:
                logger.warning(f"Cross-encoder reranking failed: {e}")

        return [DocumentProxy(d['text'], int(d['chunk_id']), score=float(d['score']), source=d['source']) for d in merged]


    def get_relevant_documents(self, query_embedding=None, k: int = 20):
        # Accept string query, embedding vector, or None
        query_text = None
        q_emb = None

        if query_embedding is None:
            query_text = ""
        elif isinstance(query_embedding, (str, np.str_)):
            query_text = str(query_embedding).strip()
        elif isinstance(query_embedding, (list, tuple, np.ndarray)):
            q_emb = np.array(query_embedding, dtype=np.float32)
        else:
            try:
                q_emb = np.array(query_embedding, dtype=np.float32)
            except Exception:
                query_text = str(query_embedding)

        if query_text is not None and query_text == "":
            # Return top k by order or token overlap
            chunks = self._get_db_chunks()
            if not chunks:
                return []
            return [DocumentProxy(str(getattr(c, 'chunk_text', '')), int(getattr(c, 'id', 0)), score=0.0, source='db') for c in chunks[:k]]

        # BM25 candidates for text queries
        bm25_results = []
        if query_text:
            bm25_results = bm25_search(query_text, top_k=max(k * 3, 50))

        # FAISS candidates via embeddings
        faiss_results = []
        if q_emb is None and query_text and self.embedding_model is not None:
            try:
                query_embedding_val = self.embedding_model.encode([query_text], show_progress_bar=False)[0]
                q_emb = np.array(query_embedding_val, dtype=np.float32)
            except Exception as e:
                logger.warning(f"Embedding generation for query failed: {e}")
                q_emb = None

        if q_emb is not None:
            faiss_results = faiss_search(q_emb, top_k=max(k * 3, 50))

        if not bm25_results and not faiss_results:
            # fallback token overlap on DB
            chunks = self._get_db_chunks()
            scored = []
            if query_text:
                q_tokens = set(query_text.lower().split())
                for chunk in chunks:
                    overlap = len(q_tokens.intersection(set(str(chunk.chunk_text).lower().split())))
                    scored.append((chunk, overlap))
                sorted_docs = sorted(scored, key=lambda x: x[1], reverse=True)[:k]
                docs_out = []
                for c, s in sorted_docs:
                    chunk_id = getattr(c, 'id', None)
                    if chunk_id is None:
                        chunk_id = 0
                    elif not isinstance(chunk_id, int):
                        try:
                            chunk_id = int(chunk_id)
                        except Exception:
                            chunk_id = 0
                    docs_out.append(DocumentProxy(str(getattr(c, 'chunk_text', '')), chunk_id, score=float(s), source='token_overlap'))
                return [d for d in docs_out if d.score > 0]
            docs_out = []
            for c in chunks[:k]:
                chunk_id = getattr(c, 'id', None)
                if chunk_id is None:
                    chunk_id = 0
                elif not isinstance(chunk_id, int):
                    try:
                        chunk_id = int(chunk_id)
                    except Exception:
                        chunk_id = 0
                docs_out.append(DocumentProxy(str(getattr(c, 'chunk_text', '')), chunk_id, score=0.0, source='db'))
            return docs_out

        return self._merge_candidates(faiss_results, bm25_results, query_text=query_text, top_k=k)

