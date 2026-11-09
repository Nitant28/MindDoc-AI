#!/usr/bin/env python3
"""Start the MindDoc AI API (and the built frontend, if frontend/dist exists)."""
import os
import sys
from pathlib import Path

import uvicorn

sys.path.insert(0, str(Path(__file__).parent))
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")

if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    print(f"MindDoc AI -> http://{host}:{port}   API docs -> http://{host}:{port}/docs")
    uvicorn.run("app.main:app", host=host, port=port, log_level="info")
