import os
import sys
# Ensure project root is on sys.path so `app` package imports work when running scripts
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.services.rag_service import query_rag, load_vector_store
from app.database import models
import sqlite3

def main():
    # Simple smoke test: no DB vector store (None) — should call Ollama HTTP
    q = 'Who is the president of France?'
    print('Query:', q)
    try:
        out = query_rag(None, q)
        print('Response:\n', out)
    except Exception as e:
        import traceback
        print('Exception during RAG test:')
        traceback.print_exc()

if __name__ == '__main__':
    main()
