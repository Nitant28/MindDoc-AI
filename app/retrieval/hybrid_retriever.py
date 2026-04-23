
# Hybrid Retriever: BM25 + Embedding + extensible for more
from sentence_transformers import SentenceTransformer
import numpy as np

def hybrid_retrieve(query, bm25_index, embedding_index, model: SentenceTransformer, alpha=0.5, top_k=5):
    """
    Retrieve top documents using hybrid BM25 (keyword) + embedding (vector) search.
    final_score = alpha * bm25_score + (1 - alpha) * embedding_score
    Results are merged, deduplicated, and reranked by final_score.
    """
    # 1. BM25 search (assume bm25_index is a Whoosh/RankBM25 index)
    bm25_scores = []
    bm25_texts = []
    if bm25_index is not None:
        # Example: bm25_index.search(query, top_k) returns list of (text, score)
        bm25_results = bm25_index.search(query, top_k)
        bm25_texts = [r[0] for r in bm25_results]
        bm25_scores = [r[1] for r in bm25_results]
    # 2. Embedding search
    query_emb = model.encode([query])[0]
    doc_embs = embedding_index['embeddings']
    doc_texts = embedding_index['texts']
    sims = np.dot(doc_embs, query_emb) / (np.linalg.norm(doc_embs, axis=1) * np.linalg.norm(query_emb) + 1e-8)
    emb_results = list(zip(doc_texts, sims))
    # 3. Merge results
    merged = {}
    for i, text in enumerate(bm25_texts):
        merged[text] = {'bm25': bm25_scores[i], 'emb': 0.0}
    for i, (text, emb_score) in enumerate(emb_results):
        if text in merged:
            merged[text]['emb'] = emb_score
        else:
            merged[text] = {'bm25': 0.0, 'emb': emb_score}
    # 4. Compute final score
    results = []
    for text, scores in merged.items():
        final_score = alpha * scores['bm25'] + (1 - alpha) * scores['emb']
        results.append({'text': text, 'score': final_score, 'bm25': scores['bm25'], 'emb': scores['emb']})
    # 5. Sort and return top_k
    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:top_k]
