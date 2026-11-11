"""Identity service: party records from evidence, resolution runs, reversible merges, review decisions (ADR-0009).

Canonical parties are *derived*: at any system time T they are the connected components of merge events decided
by T and not reversed by an unmerge decided by T. Events are append-only, so the identity state of any past moment
can be replayed (design F §5). Human decisions always win over later automatic runs:
- a pair a reviewer kept separate is never auto-merged;
- a merge a person reversed is never re-created automatically.
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.database.models import (CaseDocument, Document, IdentityEvent, Party, PartyIdentifier, PartyMention,
                                  PartyReview, Statement, StatementTxn)
from app.identity.narration import extract_counterparty
from app.identity.normalize import name_kind, normalize_name
from app.identity.resolver import MODEL_VERSION, Record, resolve

SCHEME_FIELD = {"PAN": "pan", "GSTIN": "gstin", "UPI_VPA": "vpa", "ACCOUNT_IFSC": "account"}


class IdentityError(ValueError):
    pass


# ------------------------------------------------------------------------------------------- canonical replay

def canonical_map(db: Session, case_id: int, as_of: Optional[datetime] = None) -> dict[int, int]:
    """party_id -> canonical party_id (smallest id in its component) as of `as_of` (default: now)."""
    ids = [i for (i,) in db.query(Party.id).filter(Party.case_id == case_id).all()]
    q = db.query(IdentityEvent).filter(IdentityEvent.case_id == case_id)
    if as_of is not None:
        q = q.filter(IdentityEvent.decided_at <= as_of)
    events = q.order_by(IdentityEvent.decided_at, IdentityEvent.id).all()
    reversed_ids = {e.reverses_event_id for e in events if e.kind == "unmerge"}
    parent = {i: i for i in ids}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for e in events:
        if e.kind == "merge" and e.id not in reversed_ids and e.a_party_id in parent and e.b_party_id in parent:
            ra, rb = find(e.a_party_id), find(e.b_party_id)
            if ra != rb:
                parent[max(ra, rb)] = min(ra, rb)
    return {i: find(i) for i in ids}


def _cluster_pans(db: Session, cmap: dict[int, int]) -> dict[int, set]:
    pans: dict[int, set] = {}
    ids = list(cmap)
    if not ids:
        return pans
    for pid, scheme, value in db.query(PartyIdentifier.party_id, PartyIdentifier.scheme, PartyIdentifier.value) \
            .filter(PartyIdentifier.party_id.in_(ids), PartyIdentifier.scheme.in_(("PAN", "GSTIN")),
                    PartyIdentifier.valid_structure.is_(True)).all():
        pans.setdefault(cmap[pid], set()).add(value if scheme == "PAN" else value[2:12])
    return pans


# ------------------------------------------------------------------------------------------- candidates

def build_candidates(db: Session, tenant_id: int, case_id: int) -> dict:
    """Create party records and mentions from statement-transaction narrations in the case. Idempotent."""
    txns = (db.query(StatementTxn, Statement.document_id)
            .join(Statement, Statement.id == StatementTxn.statement_id)
            .join(CaseDocument, CaseDocument.document_id == Statement.document_id)
            .filter(CaseDocument.case_id == case_id).all())
    seen = {sid for (sid,) in db.query(PartyMention.source_id).join(Party, Party.id == PartyMention.party_id)
            .filter(Party.case_id == case_id, PartyMention.source_type == "statement_txn").all()}
    by_sig = {p.signature: p for p in db.query(Party).filter(Party.case_id == case_id).all()}
    created = mentions = 0
    for txn, document_id in txns:
        if txn.id in seen:
            continue
        cp = extract_counterparty(txn.narration or "")
        if cp is None or not (cp.name or cp.vpa):
            continue
        name = cp.name or cp.vpa
        norm = normalize_name(name)
        signature = f"{norm}|vpa:{cp.vpa or ''}"
        party = by_sig.get(signature)
        if party is None:
            party = Party(tenant_id=tenant_id, case_id=case_id, kind=name_kind(name), name=name[:255],
                          name_norm=norm, signature=signature)
            db.add(party)
            db.flush()
            by_sig[signature] = party
            created += 1
            if cp.vpa:
                db.add(PartyIdentifier(tenant_id=tenant_id, party_id=party.id, scheme="UPI_VPA", value=cp.vpa,
                                       valid_structure=True))
        db.add(PartyMention(tenant_id=tenant_id, party_id=party.id, source_type="statement_txn", source_id=txn.id,
                            document_id=document_id, text=(txn.narration or "")[:500], channel=cp.channel))
        mentions += 1
    db.flush()
    return {"parties_created": created, "mentions_added": mentions}


# ------------------------------------------------------------------------------------------- resolution run

def _blocked_pairs(db: Session, case_id: int) -> set:
    """Pairs a person kept separate or unmerged: automatic runs must not merge them again."""
    blocked = {tuple(sorted((r.a_party_id, r.b_party_id))) for r in
               db.query(PartyReview).filter(PartyReview.case_id == case_id, PartyReview.state == "kept_separate")}
    unmerged = {e.reverses_event_id for e in db.query(IdentityEvent).filter(
        IdentityEvent.case_id == case_id, IdentityEvent.kind == "unmerge", IdentityEvent.method == "human")}
    if unmerged:
        for e in db.query(IdentityEvent).filter(IdentityEvent.id.in_(unmerged)):
            blocked.add(tuple(sorted((e.a_party_id, e.b_party_id))))
    return blocked


def _records(db: Session, case_id: int) -> list[Record]:
    parties = db.query(Party).filter(Party.case_id == case_id).all()
    idents: dict[int, dict] = {}
    if parties:
        for pi in db.query(PartyIdentifier).filter(PartyIdentifier.party_id.in_([p.id for p in parties]),
                                                   PartyIdentifier.valid_structure.is_(True)):
            idents.setdefault(pi.party_id, {}).setdefault(SCHEME_FIELD.get(pi.scheme, ""), pi.value)
    return [Record(str(p.id), p.name, kind=p.kind if p.kind != "unknown" else "",
                   **{k: v for k, v in idents.get(p.id, {}).items() if k}) for p in parties]


def run_resolution(db: Session, tenant_id: int, case_id: int, user_id: Optional[int] = None) -> dict:
    """Build candidates, resolve, and record automatic merges and review items. Commits."""
    built = build_candidates(db, tenant_id, case_id)
    records = _records(db, case_id)
    decisions, _ = resolve(records)
    cmap = canonical_map(db, case_id)
    pans = _cluster_pans(db, cmap)
    blocked = _blocked_pairs(db, case_id)
    existing_reviews = {tuple(sorted((r.a_party_id, r.b_party_id))) for r in
                        db.query(PartyReview).filter(PartyReview.case_id == case_id)}
    merged = queued = skipped = 0
    now = datetime.utcnow()
    order = sorted(decisions, key=lambda d: (d.band != "auto", not d.method.startswith("rule"), -(d.probability or 1)))
    for d in order:
        a, b = sorted((int(d.a), int(d.b)))
        if (a, b) in blocked:
            skipped += 1
            continue
        method = d.method if d.method.startswith("rule") else MODEL_VERSION
        prob_bp = None if d.probability is None else int(round(d.probability * 10000))
        if d.band == "auto":
            ca, cb = cmap[a], cmap[b]
            if ca == cb:
                continue
            if len(pans.get(ca, set()) | pans.get(cb, set())) > 1:
                d.band, d.reason = "review", "would join parties with different PANs"
            else:
                db.add(IdentityEvent(tenant_id=tenant_id, case_id=case_id, kind="merge", a_party_id=a, b_party_id=b,
                                     method=method, probability_bp=prob_bp, reason=d.reason,
                                     features=json.dumps(d.features), decided_by=user_id, decided_at=now))
                keep, gone = min(ca, cb), max(ca, cb)
                for k, v in cmap.items():
                    if v == gone:
                        cmap[k] = keep
                pans[keep] = pans.get(keep, set()) | pans.pop(gone, set())
                merged += 1
                continue
        if d.band == "review" and (a, b) not in existing_reviews and cmap[a] != cmap[b]:
            db.add(PartyReview(tenant_id=tenant_id, case_id=case_id, a_party_id=a, b_party_id=b, method=method,
                               probability_bp=prob_bp, reason=d.reason, features=json.dumps(d.features),
                               state="open"))
            existing_reviews.add((a, b))
            queued += 1
    db.commit()
    return {**built, "records": len(records), "auto_merges": merged, "review_items": queued,
            "skipped_by_human_decision": skipped, "model": MODEL_VERSION}


# ------------------------------------------------------------------------------------------- human decisions

def merge(db: Session, tenant_id: int, case_id: int, a: int, b: int, reason: str, user_id: int,
          override_conflict: bool = False) -> IdentityEvent:
    if not (reason or "").strip():
        raise IdentityError("a reason is required")
    parties = {p.id: p for p in db.query(Party).filter(Party.case_id == case_id, Party.id.in_((a, b)))}
    if len(parties) != 2:
        raise IdentityError("both parties must exist in this case")
    cmap = canonical_map(db, case_id)
    if cmap[a] == cmap[b]:
        raise IdentityError("already the same party")
    pans = _cluster_pans(db, cmap)
    conflict = len(pans.get(cmap[a], set()) | pans.get(cmap[b], set())) > 1
    if conflict and not override_conflict:
        raise IdentityError("the two parties carry different PANs; confirm the override to merge anyway")
    a, b = sorted((a, b))
    ev = IdentityEvent(tenant_id=tenant_id, case_id=case_id, kind="merge", a_party_id=a, b_party_id=b,
                       method="human", reason=reason.strip()[:2000],
                       features=json.dumps({"override_pan_conflict": conflict}), decided_by=user_id,
                       decided_at=datetime.utcnow())
    db.add(ev)
    db.flush()
    return ev


def unmerge(db: Session, tenant_id: int, case_id: int, event_id: int, reason: str, user_id: int) -> dict:
    if not (reason or "").strip():
        raise IdentityError("a reason is required")
    ev = db.query(IdentityEvent).filter(IdentityEvent.id == event_id, IdentityEvent.case_id == case_id).first()
    if ev is None or ev.kind != "merge":
        raise IdentityError("merge event not found")
    if db.query(IdentityEvent).filter(IdentityEvent.reverses_event_id == ev.id).first():
        raise IdentityError("this merge was already reversed")
    un = IdentityEvent(tenant_id=tenant_id, case_id=case_id, kind="unmerge", a_party_id=ev.a_party_id,
                       b_party_id=ev.b_party_id, reverses_event_id=ev.id, method="human",
                       reason=reason.strip()[:2000], decided_by=user_id, decided_at=datetime.utcnow())
    db.add(un)
    db.flush()
    cmap = canonical_map(db, case_id)
    return {"event_id": un.id, "still_connected": cmap[ev.a_party_id] == cmap[ev.b_party_id]}


def decide_review(db: Session, tenant_id: int, case_id: int, review_id: int, decision: str, reason: str,
                  user_id: int, override_conflict: bool = False) -> PartyReview:
    r = db.query(PartyReview).filter(PartyReview.id == review_id, PartyReview.case_id == case_id).first()
    if r is None:
        raise IdentityError("review item not found")
    if r.state != "open":
        raise IdentityError(f"already decided ({r.state})")
    if decision not in ("merge", "keep_separate"):
        raise IdentityError("decision must be merge or keep_separate")
    if not (reason or "").strip():
        raise IdentityError("a reason is required")
    if decision == "merge":
        merge(db, tenant_id, case_id, r.a_party_id, r.b_party_id, reason, user_id, override_conflict)
        r.state = "merged"
    else:
        r.state = "kept_separate"
    r.decision_reason, r.decided_by, r.decided_at = reason.strip()[:2000], user_id, datetime.utcnow()
    db.flush()
    return r


# ------------------------------------------------------------------------------------------- read models

def parties_overview(db: Session, case_id: int, as_of: Optional[datetime] = None) -> list[dict]:
    cmap = canonical_map(db, case_id, as_of)
    parties = {p.id: p for p in db.query(Party).filter(Party.case_id == case_id)}
    if as_of is not None:
        parties = {i: p for i, p in parties.items() if p.created_at is None or p.created_at <= as_of}
    idents: dict[int, list] = {}
    mentions: dict[int, list] = {}
    if parties:
        for pi in db.query(PartyIdentifier).filter(PartyIdentifier.party_id.in_(list(parties))):
            idents.setdefault(pi.party_id, []).append({"scheme": pi.scheme, "value": pi.value})
        for m in db.query(PartyMention).filter(PartyMention.party_id.in_(list(parties))):
            mentions.setdefault(m.party_id, []).append(m)
    txn_ids = [m.source_id for ms in mentions.values() for m in ms if m.source_type == "statement_txn"]
    txns = {t.id: t for t in db.query(StatementTxn).filter(StatementTxn.id.in_(txn_ids))} if txn_ids else {}
    clusters: dict[int, list[int]] = {}
    for pid in parties:
        clusters.setdefault(cmap[pid], []).append(pid)
    out = []
    for canon, members in clusters.items():
        names = Counter()
        debit = credit = n_txn = 0
        docs = set()
        for pid in members:
            for m in mentions.get(pid, []):
                names[parties[pid].name] += 1
                t = txns.get(m.source_id)
                if t is not None:
                    debit += t.debit_minor
                    credit += t.credit_minor
                    n_txn += 1
                if m.document_id:
                    docs.add(m.document_id)
            if not mentions.get(pid):
                names[parties[pid].name] += 0
        kinds = Counter(parties[p].kind for p in members)
        ids = {(i["scheme"], i["value"]) for p in members for i in idents.get(p, [])}
        out.append({
            "party_id": canon, "name": (names.most_common(1)[0][0] if names else parties[canon].name),
            "kind": kinds.most_common(1)[0][0], "records": len(members), "member_ids": sorted(members),
            "names": [n for n, _ in names.most_common()], "identifiers": [{"scheme": s, "value": v} for s, v in sorted(ids)],
            "transactions": n_txn, "debit_minor": debit, "credit_minor": credit, "documents": sorted(docs)})
    return sorted(out, key=lambda x: (-(x["debit_minor"] + x["credit_minor"]), x["name"]))


def party_detail(db: Session, case_id: int, party_id: int) -> dict:
    cmap = canonical_map(db, case_id)
    if party_id not in cmap:
        raise IdentityError("party not found")
    canon = cmap[party_id]
    members = [p for p, c in cmap.items() if c == canon]
    overview = next(x for x in parties_overview(db, case_id) if x["party_id"] == canon)
    ms = db.query(PartyMention).filter(PartyMention.party_id.in_(members)).all()
    txns = {t.id: t for t in db.query(StatementTxn).filter(
        StatementTxn.id.in_([m.source_id for m in ms if m.source_type == "statement_txn"]))} if ms else {}
    events = db.query(IdentityEvent).filter(IdentityEvent.case_id == case_id,
                                            (IdentityEvent.a_party_id.in_(members)) |
                                            (IdentityEvent.b_party_id.in_(members))) \
        .order_by(IdentityEvent.decided_at, IdentityEvent.id).all()
    reversed_ids = {e.reverses_event_id for e in events if e.kind == "unmerge"}
    names = {p.id: p.name for p in db.query(Party).filter(Party.id.in_(
        {e.a_party_id for e in events} | {e.b_party_id for e in events} | set(members)))}
    return {**overview, "canonical_id": canon,
            "mentions": [{"party_record_id": m.party_id, "source_type": m.source_type, "source_id": m.source_id,
                          "document_id": m.document_id, "channel": m.channel, "text": m.text,
                          "date": txns[m.source_id].txn_date.isoformat() if m.source_id in txns else None,
                          "debit_minor": txns[m.source_id].debit_minor if m.source_id in txns else None,
                          "credit_minor": txns[m.source_id].credit_minor if m.source_id in txns else None,
                          "page": txns[m.source_id].page if m.source_id in txns else None,
                          "seq": txns[m.source_id].seq if m.source_id in txns else None}
                         for m in sorted(ms, key=lambda m: (m.document_id or 0, m.source_id))],
            "events": [{"id": e.id, "kind": e.kind, "a": {"id": e.a_party_id, "name": names.get(e.a_party_id)},
                        "b": {"id": e.b_party_id, "name": names.get(e.b_party_id)}, "method": e.method,
                        "probability": None if e.probability_bp is None else e.probability_bp / 10000,
                        "reason": e.reason, "features": json.loads(e.features) if e.features else {},
                        "decided_by": e.decided_by, "decided_at": e.decided_at,
                        "reverses_event_id": e.reverses_event_id, "reversed": e.id in reversed_ids}
                       for e in events]}


def review_queue(db: Session, case_id: int, state: str = "open") -> list[dict]:
    rows = db.query(PartyReview).filter(PartyReview.case_id == case_id, PartyReview.state == state) \
        .order_by(PartyReview.probability_bp.desc().nullslast(), PartyReview.id).all()
    if not rows:
        return []
    cmap = canonical_map(db, case_id)
    over = {o["party_id"]: o for o in parties_overview(db, case_id)}
    out = []
    for r in rows:
        if state == "open" and cmap.get(r.a_party_id) == cmap.get(r.b_party_id):
            continue  # already joined by another decision
        out.append({"id": r.id, "state": r.state, "reason": r.reason, "method": r.method,
                    "probability": None if r.probability_bp is None else r.probability_bp / 10000,
                    "features": json.loads(r.features) if r.features else {},
                    "a": over.get(cmap.get(r.a_party_id)), "b": over.get(cmap.get(r.b_party_id)),
                    "a_record_id": r.a_party_id, "b_record_id": r.b_party_id,
                    "decision_reason": r.decision_reason, "decided_at": r.decided_at})
    return out


def flow_graph(db: Session, case_id: int) -> dict:
    """Account (statement) nodes -> canonical party nodes, with money in/out and the transactions behind each edge."""
    cmap = canonical_map(db, case_id)
    over = {o["party_id"]: o for o in parties_overview(db, case_id)}
    ms = db.query(PartyMention).join(Party, Party.id == PartyMention.party_id) \
        .filter(Party.case_id == case_id, PartyMention.source_type == "statement_txn").all()
    txns = {t.id: t for t in db.query(StatementTxn).filter(StatementTxn.id.in_([m.source_id for m in ms]))} if ms else {}
    stmts = {s.document_id: s for s in db.query(Statement).filter(
        Statement.document_id.in_({m.document_id for m in ms if m.document_id}))} if ms else {}
    docs = {d.id: d.filename for d in db.query(Document.id, Document.filename).filter(Document.id.in_(list(stmts)))} \
        if stmts else {}
    edges: dict[tuple, dict] = {}
    for m in ms:
        t = txns.get(m.source_id)
        if t is None or not m.document_id:
            continue
        key = (m.document_id, cmap[m.party_id])
        e = edges.setdefault(key, {"source": f"acct:{m.document_id}", "target": f"party:{cmap[m.party_id]}",
                                   "out_minor": 0, "in_minor": 0, "transactions": []})
        e["out_minor"] += t.debit_minor
        e["in_minor"] += t.credit_minor
        e["transactions"].append(t.id)
    nodes = [{"id": f"acct:{d}", "type": "account", "label": (stmts[d].account_masked or docs.get(d) or f"Statement {d}"),
              "document_id": d} for d in stmts]
    used = {k[1] for k in edges}
    nodes += [{"id": f"party:{p}", "type": "party", "label": over[p]["name"], "kind": over[p]["kind"],
               "party_id": p} for p in used if p in over]
    return {"nodes": nodes, "edges": list(edges.values())}
