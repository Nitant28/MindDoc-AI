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

from app.database.models import (BankAccount, CaseDocument, Document, IdentityEvent, Party, PartyIdentifier,
                                  PartyMention, PartyReview, Statement, StatementTxn)
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


def build_doc_candidates(db: Session, tenant_id: int, case_id: int) -> dict:
    """Party records from names printed next to a valid PAN/GSTIN in the case's documents. Idempotent."""
    from app.identity.doc_parties import find_doc_parties
    docs = (db.query(Document).join(CaseDocument, CaseDocument.document_id == Document.id)
            .filter(CaseDocument.case_id == case_id).all())
    by_sig = {p.signature: p for p in db.query(Party).filter(Party.case_id == case_id).all()}
    seen = {(m.party_id, m.source_id) for m in db.query(PartyMention).join(Party, Party.id == PartyMention.party_id)
            .filter(Party.case_id == case_id, PartyMention.source_type == "document")}
    created = mentions = 0
    for doc in docs:
        for dp in find_doc_parties(doc.content or ""):
            norm = normalize_name(dp.name)
            signature = f"{norm}|pan:{dp.pan}"
            party = by_sig.get(signature)
            if party is None:
                party = Party(tenant_id=tenant_id, case_id=case_id, kind=dp.kind, name=dp.name[:255],
                              name_norm=norm, signature=signature)
                db.add(party)
                db.flush()
                by_sig[signature] = party
                created += 1
            have = {(i.scheme, i.value) for i in db.query(PartyIdentifier).filter(PartyIdentifier.party_id == party.id)}
            for ident in dp.identifiers:
                if (ident["scheme"], ident["value"]) not in have:
                    db.add(PartyIdentifier(tenant_id=tenant_id, party_id=party.id, scheme=ident["scheme"],
                                           value=ident["value"], valid_structure=True))
                    have.add((ident["scheme"], ident["value"]))
            if (party.id, doc.id) not in seen:
                db.add(PartyMention(tenant_id=tenant_id, party_id=party.id, source_type="document",
                                    source_id=doc.id, document_id=doc.id, text=dp.line, channel="DOC"))
                seen.add((party.id, doc.id))
                mentions += 1
    db.flush()
    return {"document_parties_created": created, "document_mentions_added": mentions}


def build_holder_candidates(db: Session, tenant_id: int, case_id: int) -> dict:
    """The holder of each statement's bank account becomes a party record with the account as its identifier, so
    resolution can join "the account holder" with the same name or PAN seen elsewhere (as a counterparty in another
    statement, or in a document). Idempotent; a changed holder name moves the mention to the new record."""
    rows = (db.query(Statement, BankAccount)
            .join(BankAccount, BankAccount.id == Statement.bank_account_id)
            .join(CaseDocument, CaseDocument.document_id == Statement.document_id)
            .filter(CaseDocument.case_id == case_id, BankAccount.holder_name.isnot(None)).all())
    by_sig = {p.signature: p for p in db.query(Party).filter(Party.case_id == case_id).all()}
    existing = {(m.source_id, m.document_id): m for m in db.query(PartyMention).join(Party, Party.id == PartyMention.party_id)
                .filter(Party.case_id == case_id, PartyMention.source_type == "account_holder")}
    created = mentions = moved = 0
    for st, acct in rows:
        norm = normalize_name(acct.holder_name)
        signature = f"{norm}|acct:{acct.account_key}"
        party = by_sig.get(signature)
        if party is None:
            party = Party(tenant_id=tenant_id, case_id=case_id, kind=name_kind(acct.holder_name),
                          name=acct.holder_name[:255], name_norm=norm, signature=signature)
            db.add(party)
            db.flush()
            by_sig[signature] = party
            db.add(PartyIdentifier(tenant_id=tenant_id, party_id=party.id, scheme="ACCOUNT_IFSC",
                                   value=f"{acct.account_hash}|{acct.ifsc or ''}", valid_structure=True))
            created += 1
        m = existing.get((acct.id, st.document_id))
        if m is not None and m.party_id != party.id:
            db.delete(m)  # the holder changed (e.g. set by an analyst): the old record keeps no mention
            moved += 1
            m = None
        if m is None:
            m = PartyMention(tenant_id=tenant_id, party_id=party.id, source_type="account_holder", source_id=acct.id,
                             document_id=st.document_id, channel="HOLDER",
                             text=f"Holder of account {acct.account_masked}"
                                  + (f" (IFSC {acct.ifsc})" if acct.ifsc else "")
                                  + (" · set by an analyst" if acct.holder_source == "analyst" else " · statement header"))
            db.add(m)
            existing[(acct.id, st.document_id)] = m
            mentions += 1
    db.flush()
    return {"holder_parties_created": created, "holder_mentions_added": mentions, "holder_mentions_moved": moved}


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
    """Records that still have evidence. One whose last mention was withdrawn (e.g. a holder an analyst replaced)
    keeps its history but no longer takes part in resolution, so it cannot pull its identifiers into new merges."""
    live = {pid for (pid,) in db.query(PartyMention.party_id).join(Party, Party.id == PartyMention.party_id)
            .filter(Party.case_id == case_id).distinct()}
    parties = [p for p in db.query(Party).filter(Party.case_id == case_id).all() if p.id in live]
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
    built.update(build_doc_candidates(db, tenant_id, case_id))
    built.update(build_holder_candidates(db, tenant_id, case_id))
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
    from app.identity.claims import build_claims
    claims = build_claims(db, tenant_id, case_id, now)
    db.commit()
    return {**built, **claims, "records": len(records), "auto_merges": merged, "review_items": queued,
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
    accounts = {a.id: a for a in db.query(BankAccount).filter(BankAccount.id.in_(
        [m.source_id for ms in mentions.values() for m in ms if m.source_type == "account_holder"]))} \
        if mentions else {}
    from app.database.models import Claim
    claimed = {pid for (pid,) in db.query(Claim.object_party_id).filter(
        Claim.case_id == case_id, Claim.superseded_at.is_(None), Claim.object_party_id.isnot(None)).distinct()}
    for canon, members in clusters.items():
        # a record with no evidence left (e.g. a holder an analyst replaced) is history, not a party to show; one
        # still cited by a current claim stays visible until resolution re-attaches its mentions
        if not any(mentions.get(pid) for pid in members) and not claimed & set(members):
            continue
        names = Counter()
        debit = credit = n_txn = 0
        docs = set()
        for pid in members:
            for m in mentions.get(pid, []):
                names[parties[pid].name] += 1
                t = txns.get(m.source_id) if m.source_type == "statement_txn" else None
                if t is not None:
                    debit += t.debit_minor
                    credit += t.credit_minor
                    n_txn += 1
                if m.document_id:
                    docs.add(m.document_id)
            if not mentions.get(pid):
                names[parties[pid].name] += 0
        kinds = Counter(parties[p].kind for p in members)
        held = sorted({m.source_id for pid in members for m in mentions.get(pid, []) if m.source_type == "account_holder"})
        ids = {(i["scheme"], i["value"]) for p in members for i in idents.get(p, [])}
        out.append({
            "party_id": canon, "name": (names.most_common(1)[0][0] if names else parties[canon].name),
            "kind": kinds.most_common(1)[0][0], "records": len(members), "member_ids": sorted(members),
            "names": [n for n, _ in names.most_common()], "identifiers": [{"scheme": s, "value": v} for s, v in sorted(ids)],
            "transactions": n_txn, "debit_minor": debit, "credit_minor": credit, "documents": sorted(docs),
            "accounts": [{"id": a, "masked": accounts[a].account_masked, "ifsc": accounts[a].ifsc}
                         for a in held if a in accounts]})
    return sorted(out, key=lambda x: (-(x["debit_minor"] + x["credit_minor"]), x["name"]))


def party_detail(db: Session, case_id: int, party_id: int) -> dict:
    cmap = canonical_map(db, case_id)
    if party_id not in cmap:
        raise IdentityError("party not found")
    canon = cmap[party_id]
    members = [p for p, c in cmap.items() if c == canon]
    overview = next((x for x in parties_overview(db, case_id) if x["party_id"] == canon), None)
    if overview is None:
        raise IdentityError("party not found")
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
    from app.identity.claims import claims_view
    def txn(m):
        return txns.get(m.source_id) if m.source_type == "statement_txn" else None

    return {**overview, "canonical_id": canon, "claims": claims_view(db, case_id, party_id=canon, cmap=cmap),
            "mentions": [{"party_record_id": m.party_id, "source_type": m.source_type, "source_id": m.source_id,
                          "document_id": m.document_id, "channel": m.channel, "text": m.text,
                          "date": txn(m).txn_date.isoformat() if txn(m) else None,
                          "debit_minor": txn(m).debit_minor if txn(m) else None,
                          "credit_minor": txn(m).credit_minor if txn(m) else None,
                          "page": txn(m).page if txn(m) else None,
                          "seq": txn(m).seq if txn(m) else None}
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


def flow_graph(db: Session, case_id: int, as_of: Optional[datetime] = None) -> dict:
    """Bank accounts -> canonical parties, built from transfer claims (current, or as known at `as_of`). Every money
    edge carries its claims and each claim its evidence rows (document, page, row, region). Statements of the same
    account share one account node, and an account's holder (a party) is joined to it by a "holds" edge, so money
    paid to a party that holds another statement's account can be followed into that account."""
    from app.identity.claims import claims_view
    cmap = canonical_map(db, case_id, as_of)
    over = {o["party_id"]: o for o in parties_overview(db, case_id, as_of)}
    claims = claims_view(db, case_id, as_of=as_of, cmap=cmap)
    doc_account = {d: a for d, a in db.query(Statement.document_id, Statement.bank_account_id)
                   .join(CaseDocument, CaseDocument.document_id == Statement.document_id)
                   .filter(CaseDocument.case_id == case_id)}
    accts = {a.id: a for a in db.query(BankAccount).filter(BankAccount.id.in_([a for a in doc_account.values() if a]))} \
        if any(doc_account.values()) else {}

    def node_id(doc_id: int) -> str:
        a = doc_account.get(doc_id)
        return f"acct:{a}" if a else f"acct:d{doc_id}"

    edges: dict[tuple, dict] = {}
    accounts: dict[str, dict] = {}
    for c in claims:
        if c["party_id"] is None or c["subject_document_id"] is None:
            continue
        nid = node_id(c["subject_document_id"])
        a = accts.get(doc_account.get(c["subject_document_id"]))
        node = accounts.setdefault(nid, {
            "id": nid, "type": "account", "document_id": c["subject_document_id"], "document_ids": [],
            "bank_account_id": a.id if a else None, "holder": a.holder_name if a else None,
            "label": (f"{a.account_masked}" + (f" · {a.ifsc}" if a.ifsc else "")) if a else
                     (c["subject_label"] or f"Statement {c['subject_document_id']}")})
        if c["subject_document_id"] not in node["document_ids"]:
            node["document_ids"].append(c["subject_document_id"])
        key = (nid, c["party_id"])
        e = edges.setdefault(key, {"source": nid, "target": f"party:{key[1]}", "kind": "flow", "out_minor": 0,
                                   "in_minor": 0, "claims": []})
        if c["kind"] == "TRANSFERRED_TO":
            e["out_minor"] += c["amount_minor"]
        else:
            e["in_minor"] += c["amount_minor"]
        ev = c["evidence"][0] if c["evidence"] else {}
        e["claims"].append({"id": c["id"], "kind": c["kind"], "date": c["date"], "amount_minor": c["amount_minor"],
                            "status": c["status"], "document_id": ev.get("document_id"), "page": ev.get("page"),
                            "seq": ev.get("seq"), "quote": ev.get("quote")})
    # holders: the canonical party behind each account node
    holder_of: dict[str, int] = {}
    if accts:
        for m in db.query(PartyMention).join(Party, Party.id == PartyMention.party_id).filter(
                Party.case_id == case_id, PartyMention.source_type == "account_holder",
                PartyMention.source_id.in_(list(accts))):
            if m.party_id in cmap:
                holder_of[f"acct:{m.source_id}"] = cmap[m.party_id]
    for nid, pid in holder_of.items():
        if nid in accounts and pid in over:
            a = accts[accounts[nid]["bank_account_id"]]
            if a.holder_source == "analyst":
                evidence = [{"source": "analyst", "set_by": a.holder_set_by, "set_at": a.holder_set_at}]
            else:  # the labelled holder field on the statement's first page
                evidence = [{"source": "statement_header", "document_id": d, "page": 1}
                            for d in accounts[nid]["document_ids"]]
            edges[(nid, pid, "holds")] = {"source": f"party:{pid}", "target": nid, "kind": "holds", "out_minor": 0,
                                          "in_minor": 0, "claims": [], "evidence": evidence}
    edges = {k: e for k, e in edges.items() if k[1] in over}  # never an edge to a party that is not listed
    nodes = list(accounts.values())
    used = {k[1] for k in edges}
    nodes += [{"id": f"party:{p}", "type": "party", "label": over[p]["name"], "kind": over[p]["kind"],
               "party_id": p, "holds": [n for n, h in holder_of.items() if h == p and n in accounts]}
              for p in used if p in over]
    for e in edges.values():
        e["transactions"] = [c["id"] for c in e["claims"]]
    return {"nodes": nodes, "edges": list(edges.values()), "as_of": as_of}
