"""Schema-driven structured extraction (document → JSON), grounded in retrieved passages."""
from __future__ import annotations

import json
import re

import numpy as np
from sqlalchemy.orm import Session

from app.ai import llm
from app.database.models import Document
from app.ml import embeddings as emb
from app.ml.insights import split_sentences
from app.ml.retrieval import get_index


def extract_fields(db: Session, doc: Document, fields: dict[str, str]) -> dict:
    fields = {re.sub(r"[^\w]", "_", k.strip())[:60]: str(v)[:300] for k, v in fields.items() if k.strip()}
    if not fields:
        return {"data": {}, "provider": None, "model": None}
    index = get_index(db, doc.tenant_id)
    passages: dict[int, str] = {}
    for name, desc in fields.items():
        for h in index.search(f"{name.replace('_', ' ')}: {desc}", k=3, document_ids=[doc.id], use_mmr=False):
            passages[h.chunk.id] = h.chunk.text
    context = "\n\n".join(list(passages.values())[:12]) or (doc.content or "")[:12000]

    if llm.has_llm():
        spec = "\n".join(f'- "{k}": {v}' for k, v in fields.items())
        prompt = (f"Extract these fields from the document excerpts.\nFields:\n{spec}\n\n"
                  f"Return a JSON object with exactly these keys. Use null when a value is not present. "
                  f"Use arrays for multiple values. Copy values exactly as written.\n\n<excerpts>\n{context}\n</excerpts>")
        data, res = llm.generate_json(prompt, system="You are a meticulous data-extraction engine.", fast=False)
        if isinstance(data, dict):
            return {"data": {k: data.get(k) for k in fields}, "provider": res.provider, "model": res.model}

    # Offline fallback: best-matching sentence per field (semantic search over the document).
    sents = [s for s in split_sentences(context) if 15 < len(s) < 400][:400]
    out = {}
    if sents:
        sv, model = emb.embed(sents)
        for name, desc in fields.items():
            qv, _ = emb.embed([f"{name.replace('_', ' ')} {desc}"], model)
            best = int(np.argmax(sv @ qv[0]))
            out[name] = sents[best]
    return {"data": out, "provider": "extractive", "model": emb.active_model_name()}


def as_json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)
