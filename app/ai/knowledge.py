"""Workspace ontology: entities, mentions and relations extracted from documents.

Hybrid extraction:
  * deterministic patterns for high-precision types (EMAIL, URL, MONEY, DATE, LAW)
  * heuristic NER for ORG / PERSON / LOCATION (suffixes, honorifics, gazetteers, repetition)
  * when an LLM is configured, GraphRAG-style JSON extraction of typed entities + relations

The graph powers the Knowledge Graph view and GraphRAG-lite retrieval (entity-linked chunk
expansion for questions that name an entity).
"""
from __future__ import annotations

import logging
import re
from collections import Counter, defaultdict
from itertools import combinations
from typing import Iterable, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.models import CoMention, DocumentChunk, Entity, EntityMention, Relation

logger = logging.getLogger(__name__)

ENTITY_TYPES = ["PERSON", "ORG", "LOCATION", "DATE", "MONEY", "EMAIL", "URL", "PRODUCT", "LAW", "CONCEPT", "OTHER"]

_PATTERNS = {
    "EMAIL": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "URL": re.compile(r"\bhttps?://[^\s)>\]]+", re.I),
    "MONEY": re.compile(r"(?:[$€£₹¥]\s?\d[\d,]*(?:\.\d+)?(?:\s?(?:million|billion|bn|m|k|crore|lakh))?)"
                        r"|\b(?:USD|EUR|GBP|INR|Rs\.?)\s?\d[\d,]*(?:\.\d+)?(?:\s?(?:million|billion|crore|lakh))?", re.I),
    "DATE": re.compile(r"\b(?:\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?,?\s+\d{4}"
                       r"|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}"
                       r"|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4})\b"),
    "LAW": re.compile(r"\b(?:Section|Article|Clause|Regulation|Act)\s+\d+[A-Za-z]?(?:\(\w+\))*"
                      r"|\b(?:GDPR|HIPAA|SOX|CCPA|PCI[- ]DSS|ISO\s?\d{4,5}|SOC\s?2)\b"),
}
_ORG_SUFFIX = (r"Inc|Inc\.|Corp|Corp\.|Corporation|Ltd|Ltd\.|LLC|LLP|GmbH|PLC|Pvt|Co\.|Company|Group|Bank|University|"
               r"Institute|Technologies|Technology|Systems|Labs|Foundation|Agency|Ministry|Department|Association|"
               r"Council|Hospital|Partners|Holdings|Solutions|Services|Capital|Industries|Limited|AG|SA|NV")
_ORG = re.compile(rf"\b((?:[A-Z][A-Za-z&\-]+\s){{0,4}}(?:{_ORG_SUFFIX}))(?=\W|$)")
_PERSON_TITLE = re.compile(r"\b(?:Mr|Mrs|Ms|Miss|Dr|Prof|Sir|Shri|Smt)\.?\s+((?:[A-Z][a-z]+\s?){1,3})")
_CAP_PHRASE = re.compile(r"(?<![.!?]\s)\b([A-Z][a-z]+(?:\s+(?:of\s+|de\s+|van\s+)?[A-Z][a-z]+){1,3})\b")
_LOC_WORDS = {w.strip() for w in """india, usa, united states, china, japan, germany, france, united kingdom,
england, london, paris, berlin, tokyo, new york, california, texas, new delhi, delhi, mumbai, bangalore, bengaluru,
hyderabad, chennai, pune, kolkata, singapore, dubai, canada, toronto, australia, sydney, europe, asia, africa,
brazil, mexico, spain, italy, russia, seattle, boston, san francisco, chicago, los angeles, ireland, dublin,
netherlands, amsterdam, switzerland, zurich, south korea, seoul""".replace("\n", " ").split(",") if w.strip()}
_LOC_SUFFIX = re.compile(r"\b(?:City|State|County|Province|Street|Road|Avenue|District|River|Island|Republic)\b")
_FIRST_NAMES = set("""james john robert michael william david richard joseph thomas charles mary patricia jennifer linda
elizabeth barbara susan jessica sarah karen nancy lisa emma olivia ava sophia mia amelia noah liam oliver elijah lucas
mason ethan aarav vivaan aditya arjun sai rohan rahul amit priya ananya diya isha neha pooja raj ravi sanjay sunil
vijay anil deepak kiran nitin nitant shubh shubham akash ankit arun ashok mohammed muhammad ahmed ali fatima omar wei
li zhang chen wang yuki hiroshi kenji anna maria elena carlos jose juan luis pablo sofia lucia peter paul mark alex
daniel matthew andrew steven kevin brian george edward helen grace julia laura rachel""".split())
_GENERIC = set("""the this that these those page section table figure chapter appendix agreement contract party
parties client customer company services terms conditions schedule exhibit date total amount invoice summary
introduction conclusion abstract results methods discussion references notes monday tuesday wednesday thursday
friday saturday sunday january february march april may june july august september october november december""".split())


def normalize(name: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s@.\-$€£₹/]", "", name.lower())).strip()


def _clean(name: str) -> str:
    return re.sub(r"\s+", " ", name).strip(" .,;:()[]\"'")


def extract_rule_based(text: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for etype, pat in _PATTERNS.items():
        found += [(_clean(m.group()), etype) for m in pat.finditer(text)]
    found += [(_clean(m.group(1)), "ORG") for m in _ORG.finditer(text)]
    found += [(_clean(m.group(1)), "PERSON") for m in _PERSON_TITLE.finditer(text)]
    lower = text.lower()
    for loc in _LOC_WORDS:
        m = re.search(rf"\b{re.escape(loc)}\b", lower)
        if m:
            found.append((loc.upper() if len(loc) <= 3 else loc.title(), "LOCATION"))
    known = {normalize(n) for n, _ in found}
    caps = Counter(_clean(m.group(1)) for m in _CAP_PHRASE.finditer(text))
    for phrase, cnt in caps.items():
        norm = normalize(phrase)
        toks = norm.split()
        if norm in known or cnt < 2 or any(t in _GENERIC for t in toks):
            continue
        if _LOC_SUFFIX.search(phrase):
            found.append((phrase, "LOCATION"))
        elif len(toks) in (2, 3) and toks[0] in _FIRST_NAMES:
            found.append((phrase, "PERSON"))
        elif cnt >= 3:
            found.append((phrase, "CONCEPT"))
    return [(n, t) for n, t in found if 2 < len(n) < 80]


def extract_llm(text: str) -> tuple[list[tuple[str, str]], list[tuple[str, str, str]]]:
    from app.ai import llm
    if not llm.has_llm():
        return [], []
    prompt = f"""Extract a knowledge graph from the document below.
Return JSON: {{"entities":[{{"name":str,"type":str}}],"relations":[{{"source":str,"target":str,"relation":str}}]}}
- type is one of {", ".join(ENTITY_TYPES)}
- at most 40 entities (the most important ones), at most 40 relations
- relation is a short snake_case verb phrase (e.g. "employs", "signed_with", "pays", "located_in", "regulated_by")
- use names exactly as written in the document; do not invent entities

<document>
{text[:9000]}
</document>"""
    try:
        data, _ = llm.generate_json(prompt, system="You are a precise information-extraction engine.", max_tokens=2000)
        ents = [(_clean(str(e.get("name", ""))), str(e.get("type", "OTHER")).upper())
                for e in data.get("entities", []) if e.get("name")]
        ents = [(n, t if t in ENTITY_TYPES else "OTHER") for n, t in ents if 1 < len(n) < 80]
        rels = [(_clean(str(r.get("source", ""))), _clean(str(r.get("target", ""))),
                 re.sub(r"[^a-z_]", "", str(r.get("relation", "related_to")).lower().replace(" ", "_"))[:40] or "related_to")
                for r in data.get("relations", []) if r.get("source") and r.get("target")]
        return ents, rels
    except Exception as e:
        logger.info("LLM graph extraction skipped: %s", e)
        return [], []


def build_graph_for_document(db: Session, tenant_id: int, document_id: int, chunks: list[DocumentChunk],
                             full_text: str, use_llm: bool = True) -> dict:
    """Extract entities/relations for one document and merge them into the workspace graph."""
    ents = extract_rule_based(full_text[:200_000])
    llm_rels: list[tuple[str, str, str]] = []
    if use_llm:
        le, llm_rels = extract_llm(full_text)
        ents += le

    # Resolve duplicates: same normalised name → one entity; prefer the most specific type.
    by_norm: dict[str, tuple[str, str]] = {}
    priority = {t: i for i, t in enumerate(["EMAIL", "URL", "MONEY", "DATE", "LAW", "PERSON", "ORG", "LOCATION",
                                            "PRODUCT", "CONCEPT", "OTHER"])}
    for name, etype in ents:
        norm = normalize(name)
        if not norm or norm in _GENERIC:
            continue
        cur = by_norm.get(norm)
        if cur is None or priority.get(etype, 99) < priority.get(cur[1], 99):
            by_norm[norm] = (name, etype)

    # Mentions per chunk (substring match on normalised text).
    chunk_norm = [(c.id, normalize(c.chunk_text or "")) for c in chunks]
    mentions: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for norm in by_norm:
        for cid, ctext in chunk_norm:
            cnt = ctext.count(norm)
            if cnt:
                mentions[norm].append((cid, cnt))
    keep = {n for n in by_norm if mentions.get(n)}

    entity_ids: dict[str, int] = {}
    for norm in keep:
        name, etype = by_norm[norm]
        ent = db.query(Entity).filter_by(tenant_id=tenant_id, norm_name=norm, type=etype).first()
        if not ent:
            ent = Entity(tenant_id=tenant_id, name=name, norm_name=norm, type=etype, mention_count=0)
            db.add(ent)
            db.flush()
        total = sum(c for _, c in mentions[norm])
        ent.mention_count = (ent.mention_count or 0) + total
        entity_ids[norm] = ent.id
        for cid, cnt in mentions[norm]:
            db.add(EntityMention(entity_id=ent.id, document_id=document_id, chunk_id=cid, count=cnt))

    # Relations are only what the LLM extracted as a typed relation. Being named in the same passage is a
    # co-mention: a weak signal kept separately and never shown as a relationship (ADR-0005 amendment).
    rel_weights: Counter = Counter()
    for s, t, r in llm_rels:
        a, b = entity_ids.get(normalize(s)), entity_ids.get(normalize(t))
        if a and b and a != b:
            rel_weights[(a, b, r)] += 1
    for (a, b, r), w in rel_weights.most_common(150):
        db.add(Relation(tenant_id=tenant_id, document_id=document_id, source_id=a, target_id=b, relation=r,
                        weight=float(w)))
    per_chunk: dict[int, set[int]] = defaultdict(set)
    for norm, ms in mentions.items():
        if norm in entity_ids and by_norm[norm][1] not in ("DATE", "URL"):
            for cid, _ in ms:
                per_chunk[cid].add(entity_ids[norm])
    co: Counter = Counter()
    for ids in per_chunk.values():
        for a, b in combinations(sorted(ids)[:25], 2):
            co[(a, b)] += 1
    for (a, b), n in co.most_common(300):
        db.add(CoMention(tenant_id=tenant_id, document_id=document_id, a_entity_id=a, b_entity_id=b, chunks=n))
    db.commit()
    return {"entities": len(entity_ids), "relations": min(150, len(rel_weights)), "co_mentions": min(300, len(co))}


def remove_document(db: Session, tenant_id: int, document_id: int):
    rows = (db.query(EntityMention.entity_id, func.sum(EntityMention.count))
            .filter(EntityMention.document_id == document_id).group_by(EntityMention.entity_id).all())
    for eid, total in rows:
        ent = db.get(Entity, eid)
        if ent:
            ent.mention_count = max(0, (ent.mention_count or 0) - int(total or 0))
    db.query(Relation).filter(Relation.document_id == document_id).delete(synchronize_session=False)
    db.query(CoMention).filter(CoMention.document_id == document_id).delete(synchronize_session=False)
    db.query(EntityMention).filter(EntityMention.document_id == document_id).delete(synchronize_session=False)
    db.flush()
    orphan_ids = [e.id for e in db.query(Entity).filter(Entity.tenant_id == tenant_id).all()
                  if not db.query(EntityMention.id).filter(EntityMention.entity_id == e.id).first()]
    if orphan_ids:
        db.query(Relation).filter((Relation.source_id.in_(orphan_ids)) | (Relation.target_id.in_(orphan_ids))) \
            .delete(synchronize_session=False)
        db.query(Entity).filter(Entity.id.in_(orphan_ids)).delete(synchronize_session=False)


def document_entities(db: Session, document_id: int, limit: int = 40) -> list[dict]:
    rows = (db.query(Entity.name, Entity.type, func.sum(EntityMention.count).label("c"))
            .join(EntityMention, EntityMention.entity_id == Entity.id)
            .filter(EntityMention.document_id == document_id)
            .group_by(Entity.id).order_by(func.sum(EntityMention.count).desc()).limit(limit).all())
    return [{"name": n, "type": t, "count": int(c)} for n, t, c in rows]


def graph(db: Session, tenant_id: int, document_id: Optional[int] = None, limit: int = 150,
          allowed: Optional[list[int]] = None) -> dict:
    """Entities and relations; `allowed` (a document allow-list from case access) limits everything shown to what
    those documents say."""
    q = db.query(Entity.id, Entity.name, Entity.type, func.sum(EntityMention.count).label("w")) \
        .join(EntityMention, EntityMention.entity_id == Entity.id).filter(Entity.tenant_id == tenant_id)
    if document_id:
        q = q.filter(EntityMention.document_id == document_id)
    if allowed is not None:
        q = q.filter(EntityMention.document_id.in_(allowed or [-1]))
    rows = q.group_by(Entity.id).order_by(func.sum(EntityMention.count).desc()).limit(limit).all()
    ids = [r[0] for r in rows]
    docs_by_ent: dict[int, set] = defaultdict(set)
    if ids:
        for eid, did in db.query(EntityMention.entity_id, EntityMention.document_id) \
                .filter(EntityMention.entity_id.in_(ids)).distinct():
            if allowed is None or did in allowed:
                docs_by_ent[eid].add(did)
    nodes = [{"id": f"e:{eid}", "label": name, "type": etype, "weight": int(w),
              "documents": sorted(docs_by_ent[eid])} for eid, name, etype, w in rows]
    edges = []
    if ids:
        rq = db.query(Relation.source_id, Relation.target_id, Relation.relation, func.sum(Relation.weight)) \
            .filter(Relation.tenant_id == tenant_id, Relation.source_id.in_(ids), Relation.target_id.in_(ids))
        if document_id:
            rq = rq.filter(Relation.document_id == document_id)
        if allowed is not None:
            rq = rq.filter(Relation.document_id.in_(allowed or [-1]))
        weak: Counter = Counter()
        for s, t, r, w in rq.group_by(Relation.source_id, Relation.target_id, Relation.relation) \
                .order_by(func.sum(Relation.weight).desc()).limit(limit * 4):
            if r == "co_occurs":  # written before migration 0008 moved co-occurrence out of relations
                weak[(s, t)] += int(w)
            else:
                edges.append({"source": f"e:{s}", "target": f"e:{t}", "relation": r, "weight": float(w),
                              "weak": False})
        cq = db.query(CoMention.a_entity_id, CoMention.b_entity_id, func.sum(CoMention.chunks)) \
            .filter(CoMention.tenant_id == tenant_id, CoMention.a_entity_id.in_(ids), CoMention.b_entity_id.in_(ids))
        if document_id:
            cq = cq.filter(CoMention.document_id == document_id)
        if allowed is not None:
            cq = cq.filter(CoMention.document_id.in_(allowed or [-1]))
        for a, b, n in cq.group_by(CoMention.a_entity_id, CoMention.b_entity_id) \
                .order_by(func.sum(CoMention.chunks).desc()).limit(limit * 4):
            weak[(a, b)] += int(n)
        for (a, b), n in weak.most_common(limit * 4):
            edges.append({"source": f"e:{a}", "target": f"e:{b}", "relation": "mentioned_together",
                          "weight": float(n), "weak": True})
    return {"nodes": nodes, "edges": edges}


_MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov",
                                        "dec"], start=1)}


def parse_date(text: str):
    """Parse the DATE formats produced by the extractor into a datetime.date (or None)."""
    from datetime import date
    t = text.strip().lower().replace(",", " ")
    try:
        m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", t)
        if m:
            return date(int(m[1]), int(m[2]), int(m[3]))
        m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{2,4})$", t)
        if m:
            a, b, y = int(m[1]), int(m[2]), int(m[3])
            y += 2000 if y < 100 else 0
            d, mo = (a, b) if a > 12 or b <= 12 else (b, a)  # day-first unless impossible
            return date(y, mo, d)
        m = re.match(r"^(\d{1,2})(?:st|nd|rd|th)?\s+([a-z]{3})[a-z]*\.?\s+(\d{4})$", t)
        if m:
            return date(int(m[3]), _MONTHS[m[2][:3]], int(m[1]))
        m = re.match(r"^([a-z]{3})[a-z]*\.?\s+(\d{1,2})(?:st|nd|rd|th)?\s+(\d{4})$", t)
        if m:
            return date(int(m[3]), _MONTHS[m[1][:3]], int(m[2]))
    except (ValueError, KeyError):
        return None
    return None


def timeline(db: Session, tenant_id: int, document_id: Optional[int] = None,
             upcoming_days: Optional[int] = None, limit: int = 300, allowed: Optional[list[int]] = None) -> list[dict]:
    """Every dated fact in the workspace (deadlines, renewals, effective dates) with its context."""
    from datetime import date
    from app.database.models import Document
    q = (db.query(Entity.name, EntityMention.document_id, DocumentChunk.chunk_text, DocumentChunk.page, Document.filename)
         .join(EntityMention, EntityMention.entity_id == Entity.id)
         .join(DocumentChunk, DocumentChunk.id == EntityMention.chunk_id)
         .join(Document, Document.id == EntityMention.document_id)
         .filter(Entity.tenant_id == tenant_id, Entity.type == "DATE"))
    if document_id:
        q = q.filter(EntityMention.document_id == document_id)
    if allowed is not None:
        q = q.filter(EntityMention.document_id.in_(allowed or [-1]))
    today = date.today()
    seen, items = set(), []
    for name, doc_id, text, page, filename in q.limit(2000):
        d = parse_date(name)
        if not d or (doc_id, d) in seen:
            continue
        seen.add((doc_id, d))
        idx = (text or "").lower().find(name.lower())
        body = text or ""
        s = max(0, idx - 120) if idx >= 0 else 0
        if s > 0:  # start at a word boundary, not mid-word
            sp = body.find(" ", s)
            s = sp + 1 if 0 <= sp < idx else s
        e = min(len(body), s + 260)
        if e < len(body):
            sp = body.rfind(" ", s, e)
            e = sp if sp > idx + len(name) else e
        snippet = ("… " if s > 0 else "") + re.sub(r"\s+", " ", body[s:e]).strip() + (" …" if e < len(body) else "")
        delta = (d - today).days
        items.append({"date": d.isoformat(), "text": name, "document_id": doc_id, "filename": filename, "page": page,
                      "snippet": snippet, "upcoming": delta >= 0, "days_from_now": delta})
    if upcoming_days is not None:
        items = [i for i in items if 0 <= i["days_from_now"] <= upcoming_days]
    return sorted(items, key=lambda i: i["date"])[:limit]


def entity_linked_chunks(db: Session, tenant_id: int, query: str, document_ids: Optional[Iterable[int]] = None,
                         limit: int = 4) -> tuple[list[int], list[str]]:
    """GraphRAG-lite: chunks that mention entities named in the query (and 1-hop neighbours)."""
    qn = f" {normalize(query)} "
    cands = db.query(Entity).filter(Entity.tenant_id == tenant_id, func.length(Entity.norm_name) >= 4) \
        .order_by(Entity.mention_count.desc()).limit(3000).all()
    matched = [e for e in cands if f" {e.norm_name} " in qn]
    if not matched:
        return [], []
    ids = [e.id for e in matched[:5]]
    # 1-hop neighbours for retrieval: typed relations first, then co-mentions (a weak signal is fine for finding
    # passages; it is never presented as a relationship)
    neighbours = [r.target_id for r in db.query(Relation).filter(Relation.source_id.in_(ids))
                  .order_by(Relation.weight.desc()).limit(5)]
    if len(neighbours) < 5:
        neighbours += [c.b_entity_id for c in db.query(CoMention).filter(CoMention.a_entity_id.in_(ids))
                       .order_by(CoMention.chunks.desc()).limit(5 - len(neighbours))]
    q = db.query(EntityMention.chunk_id).filter(EntityMention.entity_id.in_(ids + neighbours),
                                                 EntityMention.chunk_id.isnot(None))
    if document_ids:
        q = q.filter(EntityMention.document_id.in_(list(document_ids)))
    chunk_ids = [c for (c,) in q.order_by(EntityMention.count.desc()).limit(limit * 3)]
    return list(dict.fromkeys(chunk_ids))[:limit], [e.name for e in matched[:5]]
