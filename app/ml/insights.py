"""Classical ML + embedding analytics for documents.

- Structure-aware chunking that keeps page numbers (for citations)
- Keyphrase extraction: TF-IDF candidates re-ranked KeyBERT-style by embedding similarity + MMR
- Zero-shot document classification via label-prototype embeddings (no training data needed)
- Extractive summarisation (centroid / TextRank-style) as an offline fallback to the LLM summary
- Readability (Flesch reading ease) and reading-time stats
- Workspace topic discovery: K-Means over document embeddings, clusters labelled by c-TF-IDF terms
"""
from __future__ import annotations

import logging
import math
import re
from collections import Counter
from typing import Optional

import numpy as np

from app.core.config import settings
from app.ml import embeddings as emb
from app.ml.retrieval import STOPWORDS

logger = logging.getLogger(__name__)

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(\[])|\n{2,}")


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT_SPLIT.split(text) if len(s.strip()) > 2]


# ----------------------------------------------------------------------------- chunking

def chunk_pages(pages: list[tuple[int, str]], size: Optional[int] = None, overlap: Optional[int] = None):
    """Split page texts into ~size-char chunks on paragraph/sentence boundaries, with overlap.

    Returns list of (page_number, chunk_text). Chunks never span pages, so citations are exact.
    """
    size = size or settings.chunk_size
    overlap = overlap or settings.chunk_overlap
    out: list[tuple[int, str]] = []
    for page_no, text in pages:
        text = re.sub(r"[ \t]+", " ", text or "").strip()
        if not text:
            continue
        units: list[str] = []
        for para in re.split(r"\n\s*\n", text):
            para = para.strip()
            if not para:
                continue
            if len(para) <= size:
                units.append(para)
            else:
                for s in split_sentences(para) or [para]:
                    while len(s) > size:  # pathological long "sentence" (tables, OCR soup)
                        units.append(s[:size])
                        s = s[size - overlap:]
                    units.append(s)
        buf = ""
        for u in units:
            if buf and len(buf) + len(u) + 2 > size:
                out.append((page_no, buf.strip()))
                tail = buf[-overlap:]
                cut = tail.find(" ")
                buf = (tail[cut + 1:] if cut >= 0 else tail) + "\n" + u
            else:
                buf = f"{buf}\n\n{u}" if buf else u
        if buf.strip():
            out.append((page_no, buf.strip()))
    return out


# ----------------------------------------------------------------------------- stats

def _syllables(word: str) -> int:
    w = word.lower()
    groups = re.findall(r"[aeiouy]+", w)
    n = len(groups) - (1 if w.endswith("e") and len(groups) > 1 else 0)
    return max(1, n)


def text_stats(text: str, pages: int, chunks: int) -> dict:
    words = re.findall(r"[A-Za-z]+", text)
    sentences = max(1, len(split_sentences(text)))
    nw = max(1, len(words))
    sample = words[:5000]
    syl = sum(_syllables(w) for w in sample) / max(1, len(sample))
    flesch = 206.835 - 1.015 * (nw / sentences) - 84.6 * syl
    return {"characters": len(text), "words": len(words), "chunks": chunks, "pages": pages,
            "reading_time_min": max(1, round(len(words) / 230)), "readability": round(max(0.0, min(100.0, flesch)), 1)}


# ----------------------------------------------------------------------------- keywords

def extract_keywords(chunks: list[str], top_n: int = 12) -> list[dict]:
    if not chunks:
        return []
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        vec = TfidfVectorizer(ngram_range=(1, 3), stop_words=list(STOPWORDS | {"page"}), max_features=4000,
                              token_pattern=r"(?u)\b[A-Za-z][A-Za-z\-]{2,}\b", sublinear_tf=True)
        m = vec.fit_transform(chunks)
        scores = np.asarray(m.sum(axis=0)).ravel()
        terms = vec.get_feature_names_out()
    except Exception:
        counts = Counter(w for c in chunks for w in re.findall(r"[a-z]{4,}", c.lower()) if w not in STOPWORDS)
        return [{"term": t, "score": round(c / max(counts.values()), 3)} for t, c in counts.most_common(top_n)]

    order = np.argsort(-scores)[:60]
    cands = [terms[i] for i in order]
    base = scores[order] / (scores[order].max() or 1)
    # KeyBERT-style: prefer phrases semantically central to the document, then diversify (MMR).
    try:
        cvecs, model = emb.embed(cands)
        doc_vec, _ = emb.embed([" ".join(chunks)[:6000]], model)
        rel = 0.5 * base + 0.5 * (cvecs @ doc_vec[0])
        selected: list[int] = []
        rest = list(range(len(cands)))
        while rest and len(selected) < top_n:
            if not selected:
                best = max(rest, key=lambda j: rel[j])
            else:
                sim = cvecs[rest] @ cvecs[selected].T
                best = rest[int(np.argmax([0.7 * rel[j] - 0.3 * sim[i].max() for i, j in enumerate(rest)]))]
            selected.append(best)
            rest.remove(best)
        return [{"term": cands[j], "score": round(float(rel[j]), 3)} for j in selected]
    except Exception:
        return [{"term": t, "score": round(float(s), 3)} for t, s in zip(cands[:top_n], base[:top_n])]


# ----------------------------------------------------------------------------- classification

DOC_TYPES = {
    "legal_contract": "legal agreement contract between parties with clauses, terms, obligations, termination, liability, governing law",
    "invoice_financial": "invoice, receipt, bill, purchase order, payment, amount due, tax, bank statement, financial statement",
    "research_paper": "scientific research paper with abstract, methodology, experiments, results, references, citations",
    "resume_cv": "resume or curriculum vitae with work experience, education, skills, projects, contact details",
    "medical_record": "medical or clinical record, patient, diagnosis, prescription, lab results, treatment, symptoms",
    "technical_manual": "technical documentation, user manual, installation guide, API reference, configuration steps",
    "policy_compliance": "policy, regulation, compliance, standard operating procedure, governance, security policy, GDPR",
    "business_report": "business report, market analysis, quarterly results, strategy, KPIs, revenue, presentation",
    "identity_document": "identity document, passport, driver licence, ID card, date of birth, nationality",
    "correspondence": "letter or email correspondence, dear, regards, sincerely, meeting, request, reply",
    "academic_notes": "lecture notes, textbook chapter, study material, exam questions, definitions, examples",
}
_label_cache: dict[str, np.ndarray] = {}


def classify_document(text: str) -> tuple[str, float]:
    """Zero-shot classification: cosine similarity to label prototypes, softmax-calibrated."""
    sample = text[:4000]
    if len(sample.strip()) < 30:
        return "other", 0.0
    try:
        model = emb.active_model_name()
        if model not in _label_cache:
            _label_cache[model], _ = emb.embed(list(DOC_TYPES.values()), model)
        labels = _label_cache[model]
        dvec, _ = emb.embed([sample], model)
        sims = labels @ dvec[0]
        probs = np.exp((sims - sims.max()) * 20)
        probs /= probs.sum()
        i = int(np.argmax(probs))
        if sims[i] < 0.12:
            return "other", round(float(probs[i]), 3)
        return list(DOC_TYPES)[i], round(float(probs[i]), 3)
    except Exception as e:
        logger.warning("classification failed: %s", e)
        return "other", 0.0


# ----------------------------------------------------------------------------- summarisation

def extractive_summary(text: str, n: int = 4) -> str:
    text = re.sub(r"-{3}\s*Page \d+(?: \(OCR\))?\s*-{3}", " ", text)
    sents = [s for s in split_sentences(text[:30000]) if 40 <= len(s) <= 400]
    if len(sents) <= n:
        return " ".join(sents) or text[:500]
    try:
        vecs, _ = emb.embed(sents[:300])
        centroid = vecs.mean(axis=0)
        centroid /= np.linalg.norm(centroid) or 1
        scores = vecs @ centroid
        # light position prior: openings of documents tend to be informative
        scores += 0.05 * np.exp(-np.arange(len(scores)) / 20)
        top = sorted(np.argsort(-scores)[:n])
        return " ".join(sents[i] for i in top)
    except Exception:
        return " ".join(sents[:n])


def llm_summary(text: str) -> Optional[str]:
    from app.ai import llm
    if not llm.has_llm():
        return None
    excerpt = text[:12000]
    try:
        res = llm.generate(
            f"Summarise this document in 3-5 sentences for a busy analyst. State what it is, who/what it "
            f"concerns, the key facts/figures, and any obligations, risks or deadlines. No preamble.\n\n"
            f"<document>\n{excerpt}\n</document>",
            system="You write precise, factual executive summaries. Never invent facts.",
            max_tokens=350, fast=True)
        return res.text.strip()
    except Exception as e:
        logger.info("LLM summary unavailable: %s", e)
        return None


# ----------------------------------------------------------------------------- topics

def discover_topics(doc_ids: list[int], doc_vectors: np.ndarray, doc_texts: list[str]) -> list[dict]:
    n = len(doc_ids)
    if n < 3:
        return []
    k = int(min(8, max(2, round(math.sqrt(n / 1.5)))))
    try:
        from sklearn.cluster import KMeans
        from sklearn.feature_extraction.text import TfidfVectorizer
        labels = KMeans(n_clusters=k, n_init=10, random_state=42).fit_predict(doc_vectors)
        # c-TF-IDF: treat each cluster as one big document to find its distinctive terms
        cluster_docs = [" ".join(doc_texts[i][:20000] for i in range(n) if labels[i] == c) for c in range(k)]
        vec = TfidfVectorizer(stop_words=list(STOPWORDS), max_features=3000,
                              token_pattern=r"(?u)\b[A-Za-z][A-Za-z\-]{3,}\b")
        m = vec.fit_transform(cluster_docs).toarray()
        terms = vec.get_feature_names_out()
        topics = []
        for c in range(k):
            members = [doc_ids[i] for i in range(n) if labels[i] == c]
            if not members:
                continue
            kw = [terms[j] for j in np.argsort(-m[c])[:5]]
            topics.append({"id": c, "label": " · ".join(kw[:3]), "keywords": kw, "document_ids": members})
        return sorted(topics, key=lambda t: -len(t["document_ids"]))
    except Exception as e:
        logger.warning("topic discovery failed: %s", e)
        return []
