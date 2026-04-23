"""
embedding_generator.py
Generates embeddings for each row in tax_law_knowledge_base.csv using all-MiniLM-L6-v2.
Saves as embeddings.npy and metadata.json for vector DB ingestion.
"""

import csv
import numpy as np
from sentence_transformers import SentenceTransformer
import json

model = SentenceTransformer('all-MiniLM-L6-v2')

rows = []
with open('tax_law_knowledge_base.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        rows.append(row)

texts = [row['key_rule_summary'] for row in rows]
embeddings = model.encode(texts, show_progress_bar=True)
np.save('embeddings.npy', embeddings)

with open('metadata.json', 'w', encoding='utf-8') as f:
    json.dump(rows, f, ensure_ascii=False, indent=2)

print('Embeddings and metadata saved.')
