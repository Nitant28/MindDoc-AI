import os
import sys
import json
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from app.database.models import DocumentChunk

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///app.db')
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

def is_valid_embedding(emb):
    try:
        arr = json.loads(emb)
        if isinstance(arr, list) and all(isinstance(x, (float, int)) for x in arr):
            return True
    except Exception:
        pass
    return False

def fix_embeddings():
    chunks = session.query(DocumentChunk).all()
    fixed = 0
    for chunk in chunks:
        if chunk.embedding and not is_valid_embedding(chunk.embedding):
            print(f"Fixing chunk id {chunk.id}: invalid embedding")
            chunk.embedding = None
            fixed += 1
    session.commit()
    print(f"Fixed {fixed} invalid embeddings.")

if __name__ == '__main__':
    fix_embeddings()