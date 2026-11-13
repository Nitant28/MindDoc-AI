"""Self-supervised retrieval evaluation (no labelled data needed).

For a random sample of chunks we synthesise a query the chunk should answer (LLM-written question,
or an inverse-cloze pseudo-query of its most informative terms), then measure whether each retrieval
strategy returns that chunk: hit-rate@5 and MRR, for hybrid vs dense-only vs BM25-only.
This makes retrieval quality a number you can track, not a vibe.
"""
from __future__ import annotations

import random
import time

from sqlalchemy.orm import Session

from app.ai import llm
from app.ml.insights import split_sentences
from app.ml.retrieval import BM25, get_index, memory_index, tokenize


def _pseudo_query(text: str, bm25: BM25, rng: random.Random) -> str:
    sents = [s for s in split_sentences(text) if len(s) > 60] or [text]
    toks = list(dict.fromkeys(tokenize(rng.choice(sents))))
    toks.sort(key=lambda t: -bm25.idf.get(t, 0))
    return " ".join(toks[:7])


def _llm_questions(texts: list[str]) -> list[str]:
    numbered = "\n\n".join(f"<p id={i}>{t[:700]}</p>" for i, t in enumerate(texts))
    data, _ = llm.generate_json(
        f"For each passage write ONE specific question a user might ask that this passage answers. Do not copy "
        f"long phrases verbatim.\nReturn JSON {{\"questions\": [str, ...]}} in passage order.\n\n{numbered}",
        max_tokens=1500)
    qs = data.get("questions", [])
    return [str(q) for q in qs] if len(qs) == len(texts) else []


def evaluate(db: Session, tenant_id: int, sample_size: int = 20, use_llm: bool = True, seed: int = 7) -> dict:
    t0 = time.perf_counter()
    index = get_index(db, tenant_id)          # searches run on the active backend
    corpus = memory_index(db, tenant_id)      # sampling and pseudo-query term weights
    pool = [r for r in corpus.records if len(r.text) > 200]
    if len(pool) < 3:
        return {"n": 0, "detail": "Need at least 3 substantial chunks - upload more documents."}
    rng = random.Random(seed)
    sample = rng.sample(pool, min(sample_size, len(pool)))
    queries, source = [], "pseudo-query (inverse cloze)"
    if use_llm and llm.has_llm():
        try:
            queries = _llm_questions([r.text for r in sample])
            source = "LLM-generated questions"
        except Exception:
            queries = []
    if not queries:
        queries = [_pseudo_query(r.text, corpus.bm25, rng) for r in sample]

    def run(strategy: str, rerank: bool) -> tuple[float, float]:
        hits5, rr = 0, 0.0
        for q, rec in zip(queries, sample):
            res = index.search(q, k=10, strategy=strategy, use_rerank=rerank, use_mmr=False)
            ids = [h.chunk.id for h in res]
            if rec.id in ids[:5]:
                hits5 += 1
            if rec.id in ids:
                rr += 1.0 / (ids.index(rec.id) + 1)
        return round(hits5 / len(sample), 3), round(rr / len(sample), 3)

    hybrid = run("hybrid", True)
    dense = run("dense", False)
    bm = run("bm25", False)
    return {"n": len(sample), "query_source": source,
            "hit_rate_at_5": hybrid[0], "mrr": hybrid[1],
            "dense_only_hit_rate": dense[0], "dense_only_mrr": dense[1],
            "bm25_only_hit_rate": bm[0], "bm25_only_mrr": bm[1],
            "embedding_model": index.model_name, "retrieval_backend": index.backend,
            "ms": int((time.perf_counter() - t0) * 1000)}
