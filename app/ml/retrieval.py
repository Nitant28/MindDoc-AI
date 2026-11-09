"""Hybrid retrieval engine.

Pipeline:  BM25 (lexical)  +  dense cosine (semantic)
           → Reciprocal Rank Fusion (RRF, k=60)
           → optional cross-encoder rerank
           → Maximal Marginal Relevance (MMR) for diverse, non-redundant context.

The per-workspace index is built in memory and cached; it rebuilds automatically when the
workspace's chunk set changes (fingerprint = count + max id), so no manual invalidation.
Chunks missing a vector (or embedded by a different model) are re-embedded and persisted
during the build: the index is self-healing.
"""
from __future__ import annotations

import json
import logging
import math
import re
import threading
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.models import Document, DocumentChunk
from app.ml import embeddings as emb

logger = logging.getLogger(__name__)

STOPWORDS = set("""a an and are as at be but by for from has have he her his i if in into is it its
me my no not of on or our she so than that the their them then there these they this to was we were
what when where which who why will with you your about above after again all also am any because been
before being below between both can could did do does doing down during each few further had having
here how just more most nor now off once only other ought out over own same should some such through
too under until up very would yes yet""".split())

_WORD = re.compile(r"[a-z0-9][a-z0-9\-\.]*[a-z0-9]|[a-z0-9]")


def _stem(w: str) -> str:
    for suf in ("ization", "ational", "fulness", "iveness", "ations", "ments", "ingly", "ation", "ness",
                "ment", "ings", "ies", "ing", "ers", "ed", "es", "ly", "er", "s"):
        if len(w) > len(suf) + 3 and w.endswith(suf):
            return w[: -len(suf)] + ("y" if suf == "ies" else "")
    return w


def tokenize(text: str) -> list[str]:
    return [_stem(w) for w in _WORD.findall(text.lower()) if w not in STOPWORDS and len(w) > 1]


@dataclass
class ChunkRecord:
    id: int
    document_id: int
    filename: str
    page: Optional[int]
    text: str


@dataclass
class Hit:
    chunk: ChunkRecord
    score: float
    dense: float = 0.0
    bm25: float = 0.0
    rerank: Optional[float] = None
    ranks: dict = field(default_factory=dict)


class BM25:
    def __init__(self, docs_tokens: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.n = len(docs_tokens)
        self.lengths = np.array([len(t) for t in docs_tokens], dtype=np.float32)
        self.avgdl = float(self.lengths.mean()) if self.n else 0.0
        self.postings: dict[str, list[tuple[int, int]]] = defaultdict(list)
        for i, toks in enumerate(docs_tokens):
            for term, tf in Counter(toks).items():
                self.postings[term].append((i, tf))
        self.idf = {t: math.log(1 + (self.n - len(p) + 0.5) / (len(p) + 0.5)) for t, p in self.postings.items()}

    def scores(self, query_tokens: list[str]) -> np.ndarray:
        s = np.zeros(self.n, dtype=np.float32)
        if not self.n:
            return s
        for term in set(query_tokens):
            idf = self.idf.get(term)
            if idf is None:
                continue
            for i, tf in self.postings[term]:
                denom = tf + self.k1 * (1 - self.b + self.b * self.lengths[i] / (self.avgdl or 1))
                s[i] += idf * tf * (self.k1 + 1) / denom
        return s


class WorkspaceIndex:
    def __init__(self, records: list[ChunkRecord], vectors: Optional[np.ndarray], model_name: str):
        self.records = records
        self.vectors = vectors  # (n, d) normalised, rows of zeros for missing vectors
        self.model_name = model_name
        self.bm25 = BM25([tokenize(r.text) for r in records])
        self.by_doc: dict[int, list[int]] = defaultdict(list)
        for i, r in enumerate(records):
            self.by_doc[r.document_id].append(i)

    def _mask(self, document_ids: Optional[list[int]]) -> Optional[np.ndarray]:
        if not document_ids:
            return None
        m = np.zeros(len(self.records), dtype=bool)
        for d in document_ids:
            m[self.by_doc.get(d, [])] = True
        return m

    def dense_scores(self, query: str) -> Optional[np.ndarray]:
        if self.vectors is None or not len(self.records):
            return None
        q = emb.embed_query(query, self.model_name)
        if q is None:
            return None
        return self.vectors @ q

    def search(self, query: str, k: int = 8, document_ids: Optional[list[int]] = None,
               candidates: Optional[int] = None, use_rerank: bool = True, use_mmr: bool = True,
               strategy: str = "hybrid") -> list[Hit]:
        n = len(self.records)
        if not n:
            return []
        candidates = candidates or settings.retrieval_candidates
        mask = self._mask(document_ids)
        if mask is not None and not mask.any():
            return []

        bm = self.bm25.scores(tokenize(query)) if strategy in ("hybrid", "bm25") else np.zeros(n, np.float32)
        dense = self.dense_scores(query) if strategy in ("hybrid", "dense") else None
        if dense is None:
            dense = np.zeros(n, dtype=np.float32)
        if mask is not None:
            bm = np.where(mask, bm, -np.inf)
            dense = np.where(mask, dense, -np.inf)

        # Reciprocal Rank Fusion of the two rankings (rank-based, so scales don't matter).
        fused = np.zeros(n, dtype=np.float64)
        ranks: dict[int, dict] = defaultdict(dict)
        for name, s in (("bm25", bm), ("dense", dense)):
            valid = np.isfinite(s) & (s > 0)
            order = np.argsort(-np.where(valid, s, -np.inf))[: max(candidates, k)]
            for r, i in enumerate(order):
                if not valid[i]:
                    break
                fused[i] += 1.0 / (60 + r + 1)
                ranks[int(i)][name] = r + 1
        cand = [i for i in np.argsort(-fused)[:candidates] if fused[i] > 0]
        if not cand:  # nothing matched lexically or semantically: fall back to document order
            pool = np.where(mask)[0] if mask is not None else np.arange(n)
            cand = list(pool[:k])

        hits = [Hit(chunk=self.records[i], score=float(fused[i]),
                    dense=float(dense[i]) if np.isfinite(dense[i]) else 0.0,
                    bm25=float(bm[i]) if np.isfinite(bm[i]) else 0.0, ranks=ranks.get(int(i), {}))
                for i in cand]

        if use_rerank and len(hits) > 1:
            rr = emb.rerank_scores(query, [h.chunk.text for h in hits])
            if rr is not None:
                for h, s in zip(hits, rr):
                    h.rerank = float(s)
                    h.score = float(s)
                hits.sort(key=lambda h: h.score, reverse=True)

        # Normalised relevance in [0,1] for the UI / confidence model.
        if hits and hits[0].rerank is None:
            top = max(h.score for h in hits) or 1.0
            for h in hits:
                h.score = 0.5 * (h.score / top) + 0.5 * max(0.0, h.dense)

        if use_mmr and self.vectors is not None and len(hits) > k:
            hits = self._mmr(hits, k)
        return hits[:k]

    def _mmr(self, hits: list[Hit], k: int, lam: float = 0.75) -> list[Hit]:
        idx = {r.id: i for i, r in enumerate(self.records)}
        vecs = np.stack([self.vectors[idx[h.chunk.id]] for h in hits])
        selected: list[int] = []
        rest = list(range(len(hits)))
        while rest and len(selected) < k:
            if not selected:
                best = rest[0]
            else:
                sim = vecs[rest] @ vecs[selected].T
                mmr = [lam * hits[r].score - (1 - lam) * float(sim[j].max()) for j, r in enumerate(rest)]
                best = rest[int(np.argmax(mmr))]
            selected.append(best)
            rest.remove(best)
        return [hits[i] for i in selected]


# --------------------------------------------------------------------------------------------
# Index cache
# --------------------------------------------------------------------------------------------

_cache: dict[int, tuple[tuple, WorkspaceIndex]] = {}
_cache_lock = threading.Lock()


def _fingerprint(db: Session, tenant_id: int) -> tuple:
    row = (db.query(func.count(DocumentChunk.id), func.max(DocumentChunk.id))
           .join(Document, Document.id == DocumentChunk.document_id)
           .filter(Document.tenant_id == tenant_id).one())
    return (int(row[0] or 0), int(row[1] or 0), emb.active_model_name())


def get_index(db: Session, tenant_id: int) -> WorkspaceIndex:
    fp = _fingerprint(db, tenant_id)
    cached = _cache.get(tenant_id)
    if cached and cached[0] == fp:
        return cached[1]
    with _cache_lock:
        cached = _cache.get(tenant_id)
        if cached and cached[0] == fp:
            return cached[1]
        t0 = time.perf_counter()
        index = _build(db, tenant_id)
        _cache[tenant_id] = (_fingerprint(db, tenant_id), index)
        logger.info("Built index for tenant %s: %d chunks in %.0f ms", tenant_id, len(index.records),
                    (time.perf_counter() - t0) * 1000)
        return index


def invalidate(tenant_id: int):
    _cache.pop(tenant_id, None)


def _parse_vec(raw: Optional[str]) -> Optional[np.ndarray]:
    if not raw:
        return None
    try:
        v = np.asarray(json.loads(raw), dtype=np.float32)
    except (TypeError, ValueError):
        return None
    if v.ndim != 1 or not np.all(np.isfinite(v)):
        return None
    n = np.linalg.norm(v)
    return v / n if n > 0 else None


def _build(db: Session, tenant_id: int) -> WorkspaceIndex:
    rows = (db.query(DocumentChunk, Document.filename)
            .join(Document, Document.id == DocumentChunk.document_id)
            .filter(Document.tenant_id == tenant_id)
            .order_by(DocumentChunk.document_id, DocumentChunk.chunk_index, DocumentChunk.id).all())
    model_name = emb.active_model_name()
    records, vecs, missing = [], [], []
    for chunk, filename in rows:
        records.append(ChunkRecord(chunk.id, chunk.document_id, filename or "document", chunk.page,
                                   chunk.chunk_text or ""))
        v = _parse_vec(chunk.embedding)
        same_model = (chunk.embedding_model or settings.embedding_model) == model_name
        if v is None or not same_model:
            missing.append((len(vecs), chunk))
            vecs.append(None)
        else:
            vecs.append(v)

    if missing:  # self-heal: embed and persist vectors that are absent or stale
        try:
            new, used = emb.embed([c.chunk_text or "" for _, c in missing])
            for (pos, chunk), v in zip(missing, new):
                vecs[pos] = v
                chunk.embedding = json.dumps([round(float(x), 6) for x in v])
                chunk.embedding_model = used
            db.commit()
            logger.info("Re-embedded %d chunks with %s", len(missing), used)
        except Exception as e:
            db.rollback()
            logger.warning("Re-embedding failed: %s", e)

    dims = {v.shape[0] for v in vecs if v is not None}
    matrix = None
    if records and len(dims) == 1:
        d = dims.pop()
        matrix = np.vstack([v if v is not None else np.zeros(d, np.float32) for v in vecs]).astype(np.float32)
    return WorkspaceIndex(records, matrix, model_name)
