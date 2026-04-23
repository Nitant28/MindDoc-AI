"""
semantic_search.py
AI-powered semantic document search using OpenAI embeddings.
"""

import openai
from typing import List, Dict

OPENAI_EMBEDDING_MODEL = "text-embedding-ada-002"

# Index documents (store embeddings in DB for production)
def embed_document(text: str) -> List[float]:
    response = openai.Embedding.create(
        model=OPENAI_EMBEDDING_MODEL,
        input=text
    )
    return response["data"][0]["embedding"]

# Semantic search (compare embeddings)
def semantic_search(query: str, documents: List[Dict[str, str]]) -> List[Dict[str, str]]:
    query_emb = embed_document(query)
    # For demo, use cosine similarity (production: use FAISS/DB)
    def cosine(a, b):
        import numpy as np
        a, b = np.array(a), np.array(b)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
    results = []
    for doc in documents:
        emb = embed_document(doc["text"])
        score = cosine(query_emb, emb)
        results.append({"doc": doc, "score": score})
    return sorted(results, key=lambda x: x["score"], reverse=True)

# Example usage:
# docs = [{"text": "Section 143(1) demand notice"}, {"text": "Penalty under 234A"}]
# print(semantic_search("penalty", docs))
