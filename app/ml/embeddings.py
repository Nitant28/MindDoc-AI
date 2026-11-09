"""Embedding + reranking models (loaded once, shared process-wide).

Primary: sentence-transformers (MiniLM, 384-d). Offline fallback: a deterministic feature-hashing
embedder over word uni/bi-grams + char tri-grams, so semantic search keeps working with zero
downloads. Each stored vector records which model produced it, so mixed indexes never compare
incompatible vectors.
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
import threading
from typing import Optional

import numpy as np

from app.core.config import settings

os.environ.setdefault("TRANSFORMERS_NO_TF", "1")  # avoid importing TensorFlow (slow, unused)
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

logger = logging.getLogger(__name__)

HASHING_MODEL_NAME = "hashing-384"
_DIM = 384
_st_lock = threading.Lock()
_rr_lock = threading.Lock()
_st_model = None
_st_state = "idle"  # idle | ready | downloading | failed
_reranker = None
_rr_state = "idle"  # idle | loading | ready | failed


def _construct(cls_name: str, name: str, allow_download: bool):
    """Instantiate a sentence-transformers model, from the local cache only unless allow_download."""
    import sentence_transformers as st
    cls = getattr(st, cls_name)
    try:
        return cls(name, device="cpu", local_files_only=True)
    except TypeError:  # very old sentence-transformers without local_files_only
        if not allow_download:
            raise
    except Exception:
        if not allow_download:
            raise
    return cls(name, device="cpu")


def _download_st_in_background():
    def run():
        global _st_model, _st_state
        try:
            _st_model = _construct("SentenceTransformer", settings.embedding_model, allow_download=True)
            _st_state = "ready"
            logger.info("Downloaded embedding model %s; index will re-embed automatically", settings.embedding_model)
        except Exception as e:
            _st_state = "failed"
            logger.warning("Embedding model download failed (%s); staying on hashing embeddings", e)
    threading.Thread(target=run, daemon=True).start()


def _load_st():
    """Never blocks on the network: local cache or hashing fallback (download continues in background)."""
    global _st_model, _st_state
    if _st_state != "idle":
        return _st_model
    with _st_lock:
        if _st_state == "idle":
            try:
                _st_model = _construct("SentenceTransformer", settings.embedding_model, allow_download=False)
                _st_state = "ready"
                logger.info("Loaded embedding model %s", settings.embedding_model)
            except ImportError as e:
                _st_state = "failed"
                logger.warning("sentence-transformers not installed (%s); using hashing embeddings", e)
            except Exception as e:
                _st_state = "downloading"
                logger.warning("Embedding model not cached (%s); hashing embeddings until download completes", e)
                _download_st_in_background()
    return _st_model


def active_model_name() -> str:
    return settings.embedding_model if _load_st() is not None else HASHING_MODEL_NAME


_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _hash_embed_one(text: str) -> np.ndarray:
    vec = np.zeros(_DIM, dtype=np.float32)
    t = text.lower()
    words = _TOKEN_RE.findall(t)
    feats = words + [f"{a}_{b}" for a, b in zip(words, words[1:])]
    compact = " ".join(words)
    feats += [compact[i:i + 3] for i in range(0, max(0, len(compact) - 2))]
    for f in feats:
        h = int.from_bytes(hashlib.blake2b(f.encode(), digest_size=8).digest(), "little")
        vec[h % _DIM] += 1.0 if (h >> 63) & 1 else -1.0
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec


def embed(texts: list[str], model_name: Optional[str] = None) -> tuple[np.ndarray, str]:
    """Return (L2-normalised float32 matrix, model_name)."""
    if not texts:
        return np.zeros((0, _DIM), dtype=np.float32), model_name or active_model_name()
    want = model_name or active_model_name()
    if want != HASHING_MODEL_NAME:
        model = _load_st()
        if model is not None and want == settings.embedding_model:
            vecs = model.encode(texts, batch_size=32, show_progress_bar=False, normalize_embeddings=True,
                                convert_to_numpy=True)
            return np.asarray(vecs, dtype=np.float32), want
        if model_name:  # caller needs this specific model and we can't provide it
            raise RuntimeError(f"embedding model {model_name} unavailable")
    return np.vstack([_hash_embed_one(t) for t in texts]).astype(np.float32), HASHING_MODEL_NAME


def embed_query(text: str, model_name: Optional[str] = None) -> Optional[np.ndarray]:
    try:
        vecs, _ = embed([text], model_name)
        return vecs[0]
    except Exception:
        return None


# --------------------------------------------------------------------------------------------
# Cross-encoder reranker (optional, big quality win for precision@k)
# --------------------------------------------------------------------------------------------

def load_reranker_blocking():
    """Load the cross-encoder (local cache first, then download). Call from background threads only."""
    global _reranker, _rr_state
    if not settings.enable_reranker:
        return None
    with _rr_lock:
        if _rr_state in ("ready", "failed"):
            return _reranker
        _rr_state = "loading"
        try:
            _reranker = _construct("CrossEncoder", settings.reranker_model, allow_download=True)
            _rr_state = "ready"
            logger.info("Loaded reranker %s", settings.reranker_model)
        except Exception as e:
            _rr_state = "failed"
            logger.warning("Reranker unavailable (%s); continuing without reranking", e)
    return _reranker


def _ensure_reranker_loading():
    if settings.enable_reranker and _rr_state == "idle":
        threading.Thread(target=load_reranker_blocking, daemon=True).start()


def reranker_available() -> bool:
    _ensure_reranker_loading()
    return _rr_state == "ready"


def rerank_scores(query: str, passages: list[str]) -> Optional[np.ndarray]:
    """Rerank if the cross-encoder is ready; never waits for it to load (request path stays fast)."""
    _ensure_reranker_loading()
    model = _reranker if _rr_state == "ready" else None
    if model is None or not passages:
        return None
    try:
        scores = model.predict([(query, p[:2000]) for p in passages], show_progress_bar=False)
        return 1.0 / (1.0 + np.exp(-np.asarray(scores, dtype=np.float32)))  # logits -> [0,1]
    except Exception as e:
        logger.warning("Rerank failed: %s", e)
        return None
