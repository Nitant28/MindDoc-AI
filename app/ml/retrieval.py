"""Hybrid retrieval engine.

Pipeline:  lexical (BM25 in process, or PostgreSQL full-text search)  +  dense cosine (semantic)
           → Reciprocal Rank Fusion (RRF, k=60)
           → optional cross-encoder rerank
           → Maximal Marginal Relevance (MMR) for diverse, non-redundant context.

Two interchangeable backends (ADR-0002):
* `PgIndex` (PostgreSQL, migration 0007): candidates come from SQL — an exact cosine scan over `embedding_vec`
  (pgvector) and full-text search over `chunk_tsv` — filtered by tenant, embedding model and document. The lexical
  ranking is BM25 over PostgreSQL's lexemes with document frequencies from the tenant's chunks (ADR-0002 amendment:
  FTS for candidates, BM25 for ranking); `ts_rank_cd` alone ranked far worse on RetrievalBench. Nothing is held in
  process memory, so every worker sees the same index.
* `WorkspaceIndex` (in process): BM25 + a NumPy matrix, built per tenant and cached; rebuilt when the tenant's chunk
  set changes (fingerprint = count + max id + model). Used on SQLite, when pgvector is unavailable, when a tenant's
  vectors are not all present for the active model, or with RETRIEVAL_BACKEND=memory.
Fusion, reranking, score normalisation and MMR are shared, so the two backends differ only in candidate generation.
Chunks missing a vector (or embedded by a different model) are re-embedded and persisted on first use: the index is
self-healing in both backends.
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
from sqlalchemy import bindparam, func, text
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
PG_DIM = 384  # vector(384) in migration 0007


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


# ------------------------------------------------------------------------------------------- shared steps

def _rrf(rankings: list[tuple[str, list[int]]], depth: int) -> tuple[dict[int, float], dict[int, dict]]:
    """Reciprocal Rank Fusion of ranked id lists (rank-based, so score scales don't matter)."""
    fused: dict[int, float] = defaultdict(float)
    ranks: dict[int, dict] = defaultdict(dict)
    for name, ids in rankings:
        for r, cid in enumerate(ids[:depth]):
            fused[cid] += 1.0 / (60 + r + 1)
            ranks[cid][name] = r + 1
    return fused, ranks


def _finish(hits: list[Hit], query: str, k: int, use_rerank: bool, use_mmr: bool, mmr) -> list[Hit]:
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
    if use_mmr and len(hits) > k:
        hits = mmr(hits, k)
    return hits[:k]


def _mmr_select(hits: list[Hit], vecs: np.ndarray, k: int, lam: float = 0.75) -> list[Hit]:
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


def _even(ids: list, per: int) -> list:
    step = max(1, len(ids) // per)
    return ids[::step][:per]


# ------------------------------------------------------------------------------------------ in process

class WorkspaceIndex:
    backend = "memory"

    def __init__(self, records: list[ChunkRecord], vectors: Optional[np.ndarray], model_name: str):
        self.records = records
        self.vectors = vectors  # (n, d) normalised, rows of zeros for missing vectors
        self.model_name = model_name
        self.bm25 = BM25([tokenize(r.text) for r in records])
        self.by_doc: dict[int, list[int]] = defaultdict(list)
        for i, r in enumerate(records):
            self.by_doc[r.document_id].append(i)
        self._pos = {r.id: i for i, r in enumerate(records)}

    @property
    def size(self) -> int:
        return len(self.records)

    @property
    def has_vectors(self) -> bool:
        return self.vectors is not None

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

        rankings = []
        for name, s in (("bm25", bm), ("dense", dense)):
            valid = np.isfinite(s) & (s > 0)
            order = np.argsort(-np.where(valid, s, -np.inf), kind="stable")[: max(candidates, k)]
            rankings.append((name, [self.records[i].id for i in order if valid[i]]))
        fused, ranks = _rrf(rankings, max(candidates, k))
        cand_ids = [cid for cid, _ in sorted(fused.items(), key=lambda kv: (-kv[1], kv[0]))][:candidates]
        if not cand_ids:  # nothing matched lexically or semantically: fall back to document order
            pool = np.where(mask)[0] if mask is not None else np.arange(n)
            cand_ids = [self.records[i].id for i in pool[:k]]

        hits = []
        for cid in cand_ids:
            i = self._pos[cid]
            hits.append(Hit(chunk=self.records[i], score=float(fused.get(cid, 0.0)),
                            dense=float(dense[i]) if np.isfinite(dense[i]) else 0.0,
                            bm25=float(bm[i]) if np.isfinite(bm[i]) else 0.0, ranks=ranks.get(cid, {})))
        return _finish(hits, query, k, use_rerank, use_mmr and self.vectors is not None, self.mmr)

    def mmr(self, hits: list[Hit], k: int, lam: float = 0.75) -> list[Hit]:
        if self.vectors is None:
            return hits[:k]
        vecs = np.stack([self.vectors[self._pos[h.chunk.id]] for h in hits])
        return _mmr_select(hits, vecs, k, lam)

    _mmr = mmr  # backwards-compatible name

    def chunks(self, ids) -> dict[int, ChunkRecord]:
        return {cid: self.records[self._pos[cid]] for cid in ids if cid in self._pos}

    def coverage_sample(self, document_ids: Optional[list[int]], k: int) -> list[Hit]:
        """For summary-style questions: evenly spaced chunks across each document (coverage > similarity)."""
        pools = []
        doc_ids = document_ids or list(self.by_doc)[:3]
        for d in doc_ids:
            idxs = self.by_doc.get(d, [])
            if idxs:
                per = max(2, k // max(1, len(doc_ids)))
                pools += [Hit(chunk=self.records[i], score=0.7) for i in _even(idxs, per)]
        return pools[: max(k, 4)]

    def document_vectors(self) -> dict[int, np.ndarray]:
        """Mean chunk vector per document (normalised), for topic discovery."""
        out = {}
        if self.vectors is None:
            return out
        for did, rows in self.by_doc.items():
            v = self.vectors[rows].mean(axis=0)
            n = np.linalg.norm(v)
            if n > 0:
                out[did] = v / n
        return out


# ------------------------------------------------------------------------------------------- PostgreSQL

def _vec_literal(v: np.ndarray) -> str:
    return "[" + ",".join(f"{float(x):.6f}" for x in v) + "]"


def _parse_pg_vec(raw: Optional[str]) -> Optional[np.ndarray]:
    if not raw:
        return None
    v = np.asarray(json.loads(raw), dtype=np.float32)
    n = np.linalg.norm(v)
    return v / n if n > 0 else None


_TSV_ITEM = re.compile(r"'((?:[^']|'')*)'(?::([0-9A-D,]+))?")


def fts_query(query: str) -> str:
    """OR of the query's terms for to_tsquery (BM25-like 'any term' matching; Postgres applies stemming)."""
    terms = []
    for w in re.findall(r"[a-z0-9]+", query.lower()):
        if w not in STOPWORDS and len(w) > 1 and w not in terms:
            terms.append(w)
    return " | ".join(terms[:32])


class PgIndex:
    """Hybrid search inside PostgreSQL for one tenant, bound to the request's session (row-level security applies;
    the tenant and model filters are explicit as well)."""
    backend = "postgres"
    has_vectors = True

    def __init__(self, db: Session, tenant_id: int, model_name: str, size: int):
        self.db, self.tenant_id, self.model_name, self.size = db, tenant_id, model_name, size

    def _where(self, document_ids, params: dict) -> tuple[str, list]:
        params["t"] = self.tenant_id
        if document_ids:
            params["docs"] = [int(d) for d in document_ids]
            return " AND c.document_id IN :docs", [bindparam("docs", expanding=True)]
        return "", []

    def _dense_ids(self, query: str, n: int, document_ids) -> tuple[list[int], dict[int, float]]:
        q = emb.embed_query(query, self.model_name)
        if q is None or q.shape[0] != PG_DIM:
            return [], {}
        params = {"q": _vec_literal(q), "m": self.model_name, "n": n}
        extra, binds = self._where(document_ids, params)
        sql = text(f"""SELECT c.id, 1 - (c.embedding_vec <=> CAST(:q AS vector)) AS sim
            FROM document_chunks c JOIN documents d ON d.id = c.document_id
            WHERE d.tenant_id = :t AND c.embedding_model = :m AND c.embedding_vec IS NOT NULL{extra}
            ORDER BY c.embedding_vec <=> CAST(:q AS vector), c.id LIMIT :n""").bindparams(*binds)
        rows = self.db.execute(sql, params).all()
        return [r[0] for r in rows if r[1] > 0], {r[0]: float(r[1]) for r in rows}

    def _fts_ids(self, query: str, n: int, document_ids) -> tuple[list[int], dict[int, float]]:
        tsq = fts_query(query)
        if not tsq:
            return [], {}
        params = {"tsq": tsq, "n": n}
        extra, binds = self._where(document_ids, params)
        sql = text(f"""SELECT c.id, ts_rank_cd(c.chunk_tsv, q) AS r
            FROM document_chunks c JOIN documents d ON d.id = c.document_id, to_tsquery('english', :tsq) AS q
            WHERE d.tenant_id = :t AND c.chunk_tsv @@ q{extra}
            ORDER BY r DESC, c.id LIMIT :n""").bindparams(*binds)
        rows = self.db.execute(sql, params).all()
        return [r[0] for r in rows], {r[0]: float(r[1]) for r in rows}

    def _bm25_ids(self, query: str, n: int, document_ids) -> tuple[list[int], dict[int, float]]:
        """BM25 over PostgreSQL's own lexemes (english configuration): full-text search supplies candidates (any
        query lexeme), and term frequencies, document frequencies and lengths come from `chunk_tsv`, so rare names
        and figures weigh more, as in the in-process BM25. Document length = number of distinct lexemes."""
        params: dict = {"query": query, "cap": max(200, 5 * n)}
        extra, binds = self._where(document_ids, params)
        scope = f"""d AS (SELECT c.id, c.chunk_tsv FROM document_chunks c JOIN documents dd ON dd.id = c.document_id
                      WHERE dd.tenant_id = :t{extra})"""
        # lexemes with a quote or backslash cannot be written safely as tsquery literals: they are left out
        q = ("q AS (SELECT DISTINCT lex FROM unnest(tsvector_to_array(to_tsvector('english', :query))) AS lex "
             "WHERE position(chr(39) in lex) = 0 AND position(chr(92) in lex) = 0)")
        stats = self.db.execute(text(f"""WITH {q}, {scope},
            df AS (SELECT q.lex, count(d.id) AS df FROM q LEFT JOIN d ON d.chunk_tsv @@ quote_literal(q.lex)::tsquery
                   GROUP BY q.lex)
            SELECT (SELECT count(*) FROM d), (SELECT avg(length(chunk_tsv)) FROM d),
                   coalesce((SELECT json_object_agg(lex, df) FROM df), '{{}}'::json)""").bindparams(*binds), params).one()
        total, avgdl, df = int(stats[0] or 0), float(stats[1] or 0.0), stats[2]
        df = json.loads(df) if isinstance(df, str) else (df or {})
        if not total or not df:
            return [], {}
        rows = self.db.execute(text(f"""WITH {q}, {scope},
            tq AS (SELECT string_agg(quote_literal(lex), ' | ')::tsquery AS t FROM q)
            SELECT d.id, d.chunk_tsv::text FROM d, tq WHERE tq.t IS NOT NULL AND d.chunk_tsv @@ tq.t
            ORDER BY ts_rank_cd(d.chunk_tsv, tq.t) DESC, d.id LIMIT :cap""").bindparams(*binds), params).all()
        k1, b = 1.5, 0.75
        idf = {lex: math.log(1 + (total - c + 0.5) / (c + 0.5)) for lex, c in df.items() if c}
        scores = {}
        for cid, tsv in rows:
            terms = {m.group(1).replace("''", "'"): (len(m.group(2).split(",")) if m.group(2) else 1)
                     for m in _TSV_ITEM.finditer(tsv or "")}
            dl = len(terms) or 1
            sc = 0.0
            for lex, w in idf.items():
                tf = terms.get(lex)
                if tf:
                    sc += w * tf * (k1 + 1) / (tf + k1 * (1 - b + b * dl / (avgdl or 1)))
            if sc > 0:
                scores[cid] = sc
        ranked = sorted(scores, key=lambda c: (-scores[c], c))[:n]
        return ranked, {c: scores[c] for c in ranked}

    def _records(self, ids, with_vectors: bool = False) -> tuple[dict[int, ChunkRecord], dict[int, np.ndarray]]:
        ids = [int(i) for i in ids]
        if not ids:
            return {}, {}
        sql = text("""SELECT c.id, c.document_id, d.filename, c.page, c.chunk_text,
                   CASE WHEN c.embedding_model = :m THEN c.embedding_vec::text END
            FROM document_chunks c JOIN documents d ON d.id = c.document_id
            WHERE d.tenant_id = :t AND c.id IN :ids""").bindparams(bindparam("ids", expanding=True))
        recs, vecs = {}, {}
        for cid, did, fn, page, txt, vec in self.db.execute(sql, {"t": self.tenant_id, "ids": ids, "m": self.model_name}):
            recs[cid] = ChunkRecord(cid, did, fn or "document", page, txt or "")
            if with_vectors and vec:
                v = _parse_pg_vec(vec)
                if v is not None:
                    vecs[cid] = v
        return recs, vecs

    def search(self, query: str, k: int = 8, document_ids: Optional[list[int]] = None,
               candidates: Optional[int] = None, use_rerank: bool = True, use_mmr: bool = True,
               strategy: str = "hybrid") -> list[Hit]:
        if not self.size:
            return []
        try:
            return self._search(query, k, document_ids, candidates, use_rerank, use_mmr, strategy)
        except Exception as e:  # a database error must not fail the answer: roll back, search in process
            self.db.rollback()
            logger.warning("PostgreSQL search failed (%s); using the in-process index for this query", e)
            return memory_index(self.db, self.tenant_id).search(query, k, document_ids, candidates, use_rerank,
                                                                use_mmr, "bm25" if strategy == "fts" else strategy)

    def _search(self, query, k, document_ids, candidates, use_rerank, use_mmr, strategy) -> list[Hit]:
        candidates = candidates or settings.retrieval_candidates
        depth = max(candidates, k)
        if strategy in ("hybrid", "bm25"):
            lex_ids, lex = self._bm25_ids(query, depth, document_ids)
        elif strategy == "fts":  # PostgreSQL's own ranking (ts_rank_cd), kept for the ablation
            lex_ids, lex = self._fts_ids(query, depth, document_ids)
        else:
            lex_ids, lex = [], {}
        den_ids, den = self._dense_ids(query, depth, document_ids) if strategy in ("hybrid", "dense") else ([], {})
        fused, ranks = _rrf([("bm25", lex_ids), ("dense", den_ids)], depth)
        cand_ids = [cid for cid, _ in sorted(fused.items(), key=lambda kv: (-kv[1], kv[0]))][:candidates]
        if not cand_ids:  # nothing matched: fall back to document order
            params: dict = {"k": k}
            extra, binds = self._where(document_ids, params)
            sql = text(f"""SELECT c.id FROM document_chunks c JOIN documents d ON d.id = c.document_id
                WHERE d.tenant_id = :t{extra} ORDER BY c.document_id, c.chunk_index, c.id LIMIT :k""").bindparams(*binds)
            cand_ids = [r[0] for r in self.db.execute(sql, params)]
        recs, vecs = self._records(cand_ids, with_vectors=use_mmr)
        hits = [Hit(chunk=recs[cid], score=float(fused.get(cid, 0.0)), dense=den.get(cid, 0.0), bm25=lex.get(cid, 0.0),
                    ranks=ranks.get(cid, {})) for cid in cand_ids if cid in recs]
        self._vec_cache = vecs
        return _finish(hits, query, k, use_rerank, use_mmr, self.mmr)

    def mmr(self, hits: list[Hit], k: int, lam: float = 0.75) -> list[Hit]:
        cache = getattr(self, "_vec_cache", {})
        missing = [h.chunk.id for h in hits if h.chunk.id not in cache]
        if missing:
            cache = {**cache, **self._records(missing, with_vectors=True)[1]}
        if any(h.chunk.id not in cache for h in hits):
            return hits[:k]
        return _mmr_select(hits, np.stack([cache[h.chunk.id] for h in hits]), k, lam)

    _mmr = mmr

    def chunks(self, ids) -> dict[int, ChunkRecord]:
        return self._records(ids)[0]

    def coverage_sample(self, document_ids: Optional[list[int]], k: int) -> list[Hit]:
        params: dict = {}
        extra, binds = self._where(document_ids, params)
        sql = text(f"""SELECT c.document_id, c.id FROM document_chunks c JOIN documents d ON d.id = c.document_id
            WHERE d.tenant_id = :t{extra} ORDER BY c.document_id, c.chunk_index, c.id""").bindparams(*binds)
        by_doc: dict[int, list[int]] = defaultdict(list)
        for did, cid in self.db.execute(sql, params):
            by_doc[did].append(cid)
        doc_ids = document_ids or list(by_doc)[:3]
        chosen = []
        for d in doc_ids:
            if by_doc.get(d):
                chosen += _even(by_doc[d], max(2, k // max(1, len(doc_ids))))
        recs = self.chunks(chosen)
        return [Hit(chunk=recs[c], score=0.7) for c in chosen if c in recs][: max(k, 4)]

    def document_vectors(self) -> dict[int, np.ndarray]:
        sql = text("""SELECT c.document_id, avg(c.embedding_vec)::text
            FROM document_chunks c JOIN documents d ON d.id = c.document_id
            WHERE d.tenant_id = :t AND c.embedding_model = :m AND c.embedding_vec IS NOT NULL
            GROUP BY c.document_id ORDER BY c.document_id""")
        out = {}
        for did, raw in self.db.execute(sql, {"t": self.tenant_id, "m": self.model_name}):
            v = _parse_pg_vec(raw)
            if v is not None:
                out[did] = v
        return out


# --------------------------------------------------------------------------------------------
# Index selection and cache
# --------------------------------------------------------------------------------------------

_cache: dict[int, tuple[tuple, WorkspaceIndex]] = {}
_pg_ready: dict[int, tuple[tuple, bool]] = {}
_cache_lock = threading.Lock()
_pg_columns: Optional[bool] = None


def _fingerprint(db: Session, tenant_id: int) -> tuple:
    row = (db.query(func.count(DocumentChunk.id), func.max(DocumentChunk.id))
           .join(Document, Document.id == DocumentChunk.document_id)
           .filter(Document.tenant_id == tenant_id).one())
    return (int(row[0] or 0), int(row[1] or 0), emb.active_model_name())


def _pg_has_columns(db: Session) -> bool:
    global _pg_columns
    if _pg_columns is None:
        _pg_columns = db.execute(text(
            "SELECT count(*) FROM information_schema.columns WHERE table_name = 'document_chunks' "
            "AND column_name IN ('embedding_vec', 'chunk_tsv')")).scalar() == 2
    return _pg_columns


_model_dims: dict[str, int] = {}


def _model_dim(model_name: str) -> Optional[int]:
    if model_name not in _model_dims:
        try:
            vecs, used = emb.embed(["dimension probe"], model_name)
            if used != model_name:
                return None
            _model_dims[model_name] = int(vecs.shape[1])
        except Exception:
            return None
    return _model_dims[model_name]


def _reembed(db: Session, tenant_id: int, model_name: str) -> int:
    """Embed chunks with no vector, a vector from another model, or a vector PostgreSQL could not store (wrong
    length or malformed). The JSON is rewritten; the trigger (migration 0007) fills `embedding_vec`."""
    ids = [r[0] for r in db.execute(text("""SELECT c.id FROM document_chunks c JOIN documents d ON d.id = c.document_id
        WHERE d.tenant_id = :t AND (c.embedding IS NULL OR c.embedding_vec IS NULL
                                    OR coalesce(c.embedding_model, :default) <> :m)
        ORDER BY c.id"""), {"t": tenant_id, "m": model_name, "default": settings.embedding_model})]
    if not ids:
        return 0
    stale = db.query(DocumentChunk).filter(DocumentChunk.id.in_(ids)).order_by(DocumentChunk.id).all()
    new, used = emb.embed([c.chunk_text or "" for c in stale], model_name)
    for chunk, v in zip(stale, new):
        chunk.embedding = json.dumps([round(float(x), 6) for x in v])
        chunk.embedding_model = used
    db.commit()
    logger.info("Re-embedded %d chunks with %s", len(stale), used)
    return len(stale)


def _pg_prepare(db: Session, tenant_id: int, model_name: str) -> bool:
    """Bring the tenant's vectors up to date; True when every chunk has a vector for the active model."""
    try:
        if _model_dim(model_name) != PG_DIM:  # vector(384): another model's vectors cannot be stored
            logger.info("PostgreSQL search needs %d-d vectors; %s gives %s: using the in-process index",
                        PG_DIM, model_name, _model_dim(model_name))
            return False
        db.execute(text("""UPDATE document_chunks c SET embedding_model = :m FROM documents d
            WHERE d.id = c.document_id AND d.tenant_id = :t AND c.embedding_model IS NULL AND c.embedding IS NOT NULL
              AND :m = :default"""), {"t": tenant_id, "m": model_name, "default": settings.embedding_model})
        # rows written before migration 0007 (or not visible to it under row-level security): fire the trigger
        db.execute(text("""UPDATE document_chunks c SET embedding = c.embedding FROM documents d
            WHERE d.id = c.document_id AND d.tenant_id = :t AND c.embedding IS NOT NULL AND c.embedding_vec IS NULL"""),
                   {"t": tenant_id})
        db.commit()
        _reembed(db, tenant_id, model_name)
        missing = db.execute(text("""SELECT count(*) FROM document_chunks c JOIN documents d ON d.id = c.document_id
            WHERE d.tenant_id = :t AND (c.embedding_vec IS NULL OR c.embedding_model <> :m)"""),
                             {"t": tenant_id, "m": model_name}).scalar()
        if missing:
            logger.info("PostgreSQL search not ready for tenant %s: %d chunks without a %d-d vector for %s; "
                        "using the in-process index", tenant_id, missing, PG_DIM, model_name)
        return not missing
    except Exception as e:  # never fail a search because the database path is unavailable
        db.rollback()
        logger.warning("PostgreSQL search unavailable (%s); using the in-process index", e)
        return False


def get_index(db: Session, tenant_id: int):
    """The tenant's search index: PostgreSQL when ready (see settings.retrieval_backend), else in process."""
    fp = _fingerprint(db, tenant_id)
    if settings.retrieval_backend != "memory" and db.get_bind().dialect.name == "postgresql" and _pg_has_columns(db):
        ready = _pg_ready.get(tenant_id)
        if not ready or ready[0] != fp:
            ok = _pg_prepare(db, tenant_id, fp[2])
            fp = _fingerprint(db, tenant_id)
            _pg_ready[tenant_id] = (fp, ok)
            ready = _pg_ready[tenant_id]
        if ready[1]:
            return PgIndex(db, tenant_id, fp[2], fp[0])
    return memory_index(db, tenant_id, fp)


def memory_index(db: Session, tenant_id: int, fp: Optional[tuple] = None) -> WorkspaceIndex:
    """The in-process index (cached per tenant), whatever the configured backend."""
    fp = fp or _fingerprint(db, tenant_id)
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
    _pg_ready.pop(tenant_id, None)


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
        dim = _model_dims.get(model_name)
        if v is None or not same_model or (dim is not None and v.shape[0] != dim):
            missing.append((len(vecs), chunk))
            vecs.append(None)
        else:
            vecs.append(v)

    if dims_seen := {v.shape[0] for v in vecs if v is not None}:
        if len(dims_seen) > 1:  # mixed lengths: keep the most common, re-embed the rest
            common = Counter(v.shape[0] for v in vecs if v is not None).most_common(1)[0][0]
            for pos, (v, (chunk, _)) in enumerate(zip(vecs, rows)):
                if v is not None and v.shape[0] != common:
                    missing.append((pos, chunk))
                    vecs[pos] = None
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
