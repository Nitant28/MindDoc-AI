# RetrievalBench-Synth v0: in-process vs PostgreSQL retrieval (R6 part 2, 2026-11-13)

**Question:** when hybrid search moves into PostgreSQL (pgvector exact scan + full-text search, migration 0007), does
it rank as well as the in-process index it replaces, and is PostgreSQL's own full-text ranking good enough as the
lexical half (ADR-0002 ablation R1)?

**Data:** the 160 unique passages of HB-Synth v1 (dev and test) and v2, one chunk each, with many near-duplicates
(same templates, different names and figures). The queries are the 728 supported claims; the gold passage is each
claim's source. Candidate retrieval only: no reranker, no MMR. Nothing is tuned, so there is no split. Run:
`python -m benchmarks.retrieval.run [--hashing] --report`, commit `7859457`, local PostgreSQL 16 + pgvector 0.6.2.

## Results (Hit@k with Wilson 95% intervals)

| Backend / ranking | Hit@1 | Hit@5 | MRR@10 | Median latency |
|---|---|---|---|---|
| **MiniLM embeddings** | | | | |
| in-process hybrid (BM25 + dense) | 0.442 (0.41–0.48) | 0.775 (0.74–0.80) | 0.578 | 22 ms |
| **PostgreSQL hybrid (BM25 on lexemes + pgvector)** | **0.445 (0.41–0.48)** | **0.782 (0.75–0.81)** | **0.579** | 49 ms |
| in-process BM25 | 0.541 | 0.821 | 0.656 | 1 ms |
| PostgreSQL BM25 on lexemes | 0.552 | 0.841 | 0.662 | 24 ms |
| PostgreSQL `ts_rank_cd` only | 0.376 | 0.690 | 0.505 | 9 ms |
| dense only (identical on both) | 0.302 | 0.596 | 0.428 | 21 / 31 ms |
| **Hashing embedder (slim image)** | | | | |
| in-process hybrid | 0.445 | 0.721 (0.69–0.75) | 0.556 | 2 ms |
| PostgreSQL hybrid | 0.433 | 0.724 (0.69–0.76) | 0.551 | 29 ms |

**Dense parity:** the top-10 lists are identical on both backends for all 728 queries, with both embedders. Exact
cosine in SQL equals the NumPy scan.

## What it shows

1. **Parity.** PostgreSQL hybrid search ranks as well as the in-process index; the differences are inside the
   intervals. On PostgreSQL deployments it is now the default (`RETRIEVAL_BACKEND=auto`).
2. **`ts_rank_cd` is not a substitute for BM25.** It has no rarity weighting, so names and figures count for little:
   Hit@5 0.690 vs 0.821. The PostgreSQL backend therefore ranks the lexical side with BM25 computed on PostgreSQL's
   lexemes (full-text search for candidates; term and document frequencies from `chunk_tsv`). That is the ADR-0002
   amendment's design, and it needs no AGPL BM25 extension.
3. **Hybrid is below BM25 alone on this set** (0.78 vs 0.82–0.84). The passages differ mainly in names and figures,
   which embeddings blur. This is a property of a template-generated corpus; it says nothing yet about real
   questions. Fusion weights are unchanged until a human-written set (RB) exists.
4. **Latency** is higher in PostgreSQL (tens of milliseconds) at this tiny size. The in-process figures exclude the
   index build that every process repeats when chunks change. Neither number says anything about scale.

## Limits

- Synthetic: generated claims as queries over generated passages, one chunk per document, 160 chunks.
- No HNSW index was built or measured; exact scans are the design at case size (ADR-0002).
- Local PostgreSQL 16 + pgvector 0.6.2; CI runs the tests on PostgreSQL 18 + pgvector 0.8.7. Benchmark latency was
  not measured there.
