
"""
hybrid_retrieval.py
Implements vector-based retrieval: semantic search only for legal document search.
Uses FAISS for vector DB (local, open-source, fast for prototyping).
"""

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import os
import json

# Config
VECTOR_DIM = 384  # for MiniLM or similar
EMBED_MODEL = 'all-MiniLM-L6-v2'

# Load legal data
with open('laws_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    docs = []
    for law in data.get('laws', []):
        for section in law.get('sections', []):
            docs.append({
                'text': section.get('section_content', ''),
                'meta': {
                    'law': law.get('act_title', ''),
                    'section': section.get('section_title', '')
                }
            })
    for faq in data.get('faqs', []):
        docs.append({'text': faq.get('answer', ''), 'meta': {'faq': faq.get('question', '')}})

# 1. Vector DB (FAISS)
model = SentenceTransformer(EMBED_MODEL)
corpus = [d['text'] for d in docs]
embeddings = model.encode(corpus, show_progress_bar=True)
index = faiss.IndexFlatL2(VECTOR_DIM)
index.add(np.array(embeddings, dtype='float32'))


# Vector search function
def vector_search(query, top_k=5):
    q_emb = model.encode([query])
    D, I = index.search(np.array(q_emb, dtype='float32'), top_k)
    vector_results = [docs[i] for i in I[0]]
    return vector_results

# Example usage
def main():
    q = input('Enter your legal query: ')
    results = vector_search(q)
    for i, r in enumerate(results):
        print(f'--- Result {i+1} ---')
        print('Meta:', r['meta'])
        print('Text:', r['text'][:500], '\n')

if __name__ == '__main__':
    main()
