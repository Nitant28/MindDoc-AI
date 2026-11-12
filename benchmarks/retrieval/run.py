"""RetrievalBench-Synth v0: in-process index vs PostgreSQL (pgvector + full-text search), R6 part 2.

    python -m benchmarks.retrieval.run                # MiniLM if installed, else hashing
    python -m benchmarks.retrieval.run --hashing      # the slim image's embedder

Corpus: the 160 unique passages of HB-Synth v1 (dev + test) and v2, one chunk each, many of them near-duplicates
(same templates, different names and figures), so retrieval must use names and numbers, not just topic words.
Queries: the 728 supported claims; the gold passage is the claim's source. Nothing here is tuned, so there is no
dev/test split: it measures (1) whether the PostgreSQL backend ranks like the in-process one (dense: exact cosine in
both, so rankings should agree) and (2) how PostgreSQL full-text search compares with in-process BM25 as the lexical
half of hybrid search (ADR-0002 ablation R1). No reranker, no MMR: candidate retrieval only.

Needs a local PostgreSQL with pgvector (pgserver, dev requirement). Metrics: Hit@1, Hit@5 (Wilson 95% intervals),
MRR@10, and per-query latency (median, p95). Limits: synthetic claims as queries (not human questions), one chunk
per document, 160 chunks (latency at this size says little about scale).
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import tempfile
import time
import uuid
from datetime import date
from pathlib import Path

if "--hashing" in sys.argv:
    os.environ["EMBEDDING_MODEL"] = "none/hashing-only"
    os.environ["HF_HUB_OFFLINE"] = "1"

from benchmarks.hallucination import synth, synth2  # noqa: E402
from benchmarks.hallucination.run import git_state, wilson  # noqa: E402

REPORTS = Path(__file__).resolve().parents[1] / "reports"


def corpus() -> tuple[list[dict], list[dict]]:
    passages, queries, seen = [], [], {}
    for c in synth.cases() + synth2.cases():
        if c["passage"] not in seen:
            seen[c["passage"]] = len(passages)
            passages.append({"source_id": c["source_id"], "text": c["passage"]})
        if c["label"] == "supported":
            queries.append({"id": c["id"], "query": c["claim"], "gold": seen[c["passage"]]})
    return passages, queries


def pg_url() -> str:
    import pgserver
    srv = pgserver.get_server(Path(tempfile.gettempdir()) / "minddoc-pg-bench", cleanup_mode="stop")
    name = f"rb_{uuid.uuid4().hex[:8]}"
    srv.psql(f"CREATE DATABASE {name};")
    from urllib.parse import urlparse
    u = urlparse(srv.get_uri())
    return f"postgresql+pg8000://{u.username or 'postgres'}@{u.hostname}:{u.port}/{name}"


def score(ranked: list[list[int]], gold: list[int], times: list[float]) -> dict:
    n = len(gold)
    h1 = sum(r[:1] == [g] for r, g in zip(ranked, gold))
    h5 = sum(g in r[:5] for r, g in zip(ranked, gold))
    mrr = sum(1 / (r.index(g) + 1) for r, g in zip(ranked, gold) if g in r[:10]) / n
    t = sorted(times)
    return {"n": n, "hit1": h1 / n, "hit1_ci": wilson(h1, n), "hit5": h5 / n, "hit5_ci": wilson(h5, n),
            "mrr10": mrr, "latency_ms_median": round(statistics.median(t) * 1000, 2),
            "latency_ms_p95": round(t[int(0.95 * (len(t) - 1))] * 1000, 2)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hashing", action="store_true")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    url = pg_url()
    os.environ["DATABASE_URL"] = url

    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    from app.database.migrate import upgrade_head
    from app.ml import embeddings as emb
    from app.ml.retrieval import ChunkRecord, PgIndex, WorkspaceIndex

    passages, queries = corpus()
    model = emb.active_model_name()
    vecs, model = emb.embed([p["text"] for p in passages])
    upgrade_head(url)
    owner = create_engine(url)  # superuser: row-level security does not apply; tenant filter is explicit anyway
    with owner.begin() as c:
        tid = c.execute(text("INSERT INTO tenants (name) VALUES ('bench') RETURNING id")).scalar()
        chunk_ids = []
        for p, v in zip(passages, vecs):
            did = c.execute(text("INSERT INTO documents (tenant_id, filename) VALUES (:t, :f) RETURNING id"),
                            {"t": tid, "f": p["source_id"]}).scalar()
            chunk_ids.append(c.execute(text(
                "INSERT INTO document_chunks (tenant_id, document_id, chunk_text, embedding, embedding_model, page, "
                "chunk_index) VALUES (:t, :d, :x, :e, :m, 1, 0) RETURNING id"),
                {"t": tid, "d": did, "x": p["text"], "e": json.dumps([round(float(x), 6) for x in v]), "m": model}
            ).scalar())
        assert c.execute(text("SELECT count(*) FROM document_chunks WHERE embedding_vec IS NULL")).scalar() == 0
    db = sessionmaker(bind=owner)()
    pg = PgIndex(db, tid, model, len(passages))
    stored = [json.loads(json.dumps([round(float(x), 6) for x in v])) for v in vecs]  # what both backends read
    import numpy as np
    matrix = np.asarray(stored, dtype=np.float32)
    matrix /= np.linalg.norm(matrix, axis=1, keepdims=True)
    mem = WorkspaceIndex([ChunkRecord(cid, cid, p["source_id"], 1, p["text"]) for cid, p in zip(chunk_ids, passages)],
                         matrix, model)

    gold = [chunk_ids[q["gold"]] for q in queries]
    configs = [("memory", "hybrid", mem, "hybrid"), ("memory", "bm25", mem, "bm25"), ("memory", "dense", mem, "dense"),
               ("postgres", "bm25", pg, "bm25"),
               ("postgres", "hybrid", pg, "hybrid"), ("postgres", "fts", pg, "fts"), ("postgres", "dense", pg, "dense")]
    results, rankings = {}, {}
    for backend, name, index, strategy in configs:
        ranked, times = [], []
        for q in queries:
            t0 = time.perf_counter()
            hits = index.search(q["query"], k=10, strategy=strategy, use_rerank=False, use_mmr=False)
            times.append(time.perf_counter() - t0)
            ranked.append([h.chunk.id for h in hits])
        key = f"{backend}-{name}"
        rankings[key] = ranked
        results[key] = score(ranked, gold, times)
        s = results[key]
        print(f"{key:<17} Hit@1 {s['hit1']:.3f} ({s['hit1_ci'][0]:.2f}–{s['hit1_ci'][1]:.2f})  Hit@5 {s['hit5']:.3f} "
              f"({s['hit5_ci'][0]:.2f}–{s['hit5_ci'][1]:.2f})  MRR@10 {s['mrr10']:.3f}  "
              f"latency median {s['latency_ms_median']} ms, p95 {s['latency_ms_p95']} ms")
    same10 = sum(a == b for a, b in zip(rankings["memory-dense"], rankings["postgres-dense"]))
    same1 = sum(a[:1] == b[:1] for a, b in zip(rankings["memory-dense"], rankings["postgres-dense"]))
    parity = {"dense_top10_identical": same10, "dense_top1_identical": same1, "n": len(queries)}
    print(f"dense parity: identical top-10 lists {same10}/{len(queries)}, identical top-1 {same1}/{len(queries)}")
    commit, dirty = git_state()
    if args.report:
        REPORTS.mkdir(exist_ok=True)
        out = REPORTS / f"retrievalbench-{'hashing' if args.hashing else 'minilm'}-{date.today()}.json"
        out.write_text(json.dumps({"meta": {"embeddings": model, "passages": len(passages), "queries": len(queries),
                                            "commit": commit, "dirty": dirty, "date": str(date.today())},
                                   "results": results, "dense_parity": parity}, indent=1), encoding="utf-8")
        print(f"wrote {out}")
    db.close()


if __name__ == "__main__":
    main()
