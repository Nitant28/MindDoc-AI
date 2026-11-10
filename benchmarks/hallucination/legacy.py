"""Frozen copy of the v1 claim check (app/ai/rag.py `_verify` before verifier v2), for the baseline column.

Logic is unchanged: a sentence counts as supported if its embedding similarity to the cited source is >= 0.5
(0.35 with hashing embeddings) or >= 60% of its tokens appear in the source.
"""
import re

from app.ml import embeddings as emb
from app.ml.retrieval import tokenize

_CITE = re.compile(r"\[(\d{1,2})\]")


def legacy_supported(claim: str, passage: str) -> bool:
    src_vecs, model = emb.embed([passage])
    text = _CITE.sub("", re.sub(r"[*_`#>|]", " ", claim)).strip()
    if len(text) <= 25:  # v1 skipped short sentences entirely (counted as nothing to check)
        return True
    cv, _ = emb.embed([text], model)
    sim = float(src_vecs[0] @ cv[0])
    toks = set(tokenize(text))
    lex = len(toks & set(tokenize(passage))) / max(1, len(toks))
    threshold = 0.5 if model != emb.HASHING_MODEL_NAME else 0.35
    return sim >= threshold or lex >= 0.6
