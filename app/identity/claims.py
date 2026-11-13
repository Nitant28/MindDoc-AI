"""Transfer claims from statement observations (ADR-0004, design F §2.3/§3).

A debit row with a resolved counterparty becomes `TRANSFERRED_TO(statement account -> party record, amount, date)`;
a credit row becomes `RECEIVED_FROM`. Claims are *versioned*:
- the logical key is deterministic (document content hash + row number + kind), so re-processing the same source
  with the same engine yields the same keys and, when nothing changed, no new versions;
- a changed observation closes the current version (`superseded_at`) and inserts a successor (`supersedes_id`);
- an observation that disappeared closes its claim with a reason, and nothing is deleted.
The object is a party *record*; which canonical party it belongs to is resolved at read time from identity events,
so merges and unmerges never rewrite claims.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.database.models import (Claim, ClaimEvidence, Document, Party, PartyMention, ReconciliationCheck, Statement,
                                  StatementTxn)

_CONTENT = ("kind", "subject_document_id", "subject_label", "object_party_id", "amount_minor", "currency",
            "valid_date", "status", "method")
_REGION = ("document_id", "page", "seq", "box_x0", "box_top", "box_x1", "box_bottom", "quote", "external_id")


def _status(statement: Statement, txn: StatementTxn, failing: set) -> str:
    if (statement.id, txn.seq) in failing:
        return "needs_review"
    if statement.status in ("reconciled", "reconciled_with_flags") and txn.direction_source in ("column", "suffix"):
        return "reconciled"
    return "extracted"


def build_claims(db: Session, tenant_id: int, case_id: int, now: Optional[datetime] = None) -> dict:
    now = now or datetime.utcnow()
    rows = (db.query(PartyMention, StatementTxn, Statement, Document)
            .join(Party, Party.id == PartyMention.party_id)
            .join(StatementTxn, StatementTxn.id == PartyMention.source_id)
            .join(Statement, Statement.id == StatementTxn.statement_id)
            .join(Document, Document.id == Statement.document_id)
            .filter(Party.case_id == case_id, PartyMention.source_type == "statement_txn").all())
    stmt_ids = {st.id for _, _, st, _ in rows}
    failing = {(c.statement_id, c.seq) for c in db.query(ReconciliationCheck).filter(
        ReconciliationCheck.statement_id.in_(stmt_ids), ReconciliationCheck.status == "fail",
        ReconciliationCheck.scope == "row")} if stmt_ids else set()

    desired: dict[str, tuple[dict, dict]] = {}
    for m, t, st, doc in rows:
        if not (t.debit_minor or t.credit_minor):
            continue
        kind = "TRANSFERRED_TO" if t.debit_minor else "RECEIVED_FROM"
        key = f"{kind}:{doc.content_hash or f'doc{doc.id}'}:{t.seq}"
        content = {"kind": kind, "subject_document_id": doc.id,
                   "subject_label": st.account_masked or doc.filename, "object_party_id": m.party_id,
                   "amount_minor": t.debit_minor or t.credit_minor, "currency": st.currency or "INR",
                   "valid_date": t.txn_date, "status": _status(st, t, failing),
                   "method": f"statement-engine {st.engine_version}"}
        region = {"document_id": doc.id, "page": t.page or None, "seq": t.seq, "box_x0": t.box_x0,
                  "box_top": t.box_top, "box_x1": t.box_x1, "box_bottom": t.box_bottom,
                  "quote": (t.narration or "")[:1000], "external_id": t.external_id}
        desired[key] = (content, {**region, "statement_txn_id": t.id})

    current = {c.claim_key: c for c in db.query(Claim).filter(Claim.case_id == case_id,
                                                               Claim.superseded_at.is_(None))}
    ev_by_claim = {}
    if current:
        for e in db.query(ClaimEvidence).filter(ClaimEvidence.claim_id.in_([c.id for c in current.values()])):
            ev_by_claim.setdefault(e.claim_id, e)
    created = superseded = unchanged = retracted = 0
    for key, (content, ev) in desired.items():
        cur = current.get(key)
        if cur is not None:
            old_ev = ev_by_claim.get(cur.id)
            same = all(getattr(cur, f) == content[f] for f in _CONTENT) and old_ev is not None and \
                all(getattr(old_ev, f) == ev[f] for f in _REGION)
            if same:
                unchanged += 1
                continue
            changed = [f for f in _CONTENT if getattr(cur, f) != content[f]] + \
                      [f for f in _REGION if old_ev is None or getattr(old_ev, f) != ev[f]]
            cur.superseded_at, cur.supersede_reason = now, ("changed: " + ", ".join(changed))[:255]
            db.flush()  # close before inserting the successor (one current version per key)
            superseded += 1
        claim = Claim(tenant_id=tenant_id, case_id=case_id, claim_key=key, supersedes_id=cur.id if cur else None,
                      recorded_at=now, **content)
        db.add(claim)
        db.flush()
        db.add(ClaimEvidence(tenant_id=tenant_id, claim_id=claim.id, role="supports", source_type="statement_txn",
                             **ev))
        created += 1
    for key, cur in current.items():
        if key not in desired:
            cur.superseded_at, cur.supersede_reason = now, "observation no longer present"
            retracted += 1
    db.flush()
    return {"claims_created": created, "claims_superseded": superseded, "claims_unchanged": unchanged,
            "claims_retracted": retracted}


def claims_view(db: Session, case_id: int, as_of: Optional[datetime] = None,
                party_id: Optional[int] = None, cmap: Optional[dict] = None) -> list[dict]:
    """Claims as known at system time `as_of` (default: current), with canonical party and evidence."""
    from app.identity.service import canonical_map
    cmap = cmap if cmap is not None else canonical_map(db, case_id, as_of)
    q = db.query(Claim).filter(Claim.case_id == case_id)
    if as_of is None:
        q = q.filter(Claim.superseded_at.is_(None))
    else:
        q = q.filter(Claim.recorded_at <= as_of, (Claim.superseded_at.is_(None)) | (Claim.superseded_at > as_of))
    claims = q.order_by(Claim.valid_date, Claim.id).all()
    if party_id is not None:
        target = cmap.get(party_id)
        claims = [c for c in claims if c.object_party_id is not None and cmap.get(c.object_party_id) == target]
    if not claims:
        return []
    evidence: dict[int, list] = {}
    for e in db.query(ClaimEvidence).filter(ClaimEvidence.claim_id.in_([c.id for c in claims])):
        evidence.setdefault(e.claim_id, []).append(e)
    names = {p.id: p.name for p in db.query(Party.id, Party.name).filter(Party.case_id == case_id)}
    return [{"id": c.id, "claim_key": c.claim_key, "kind": c.kind, "subject_document_id": c.subject_document_id,
             "subject_label": c.subject_label, "party_record_id": c.object_party_id,
             "party_id": cmap.get(c.object_party_id), "party_name": names.get(cmap.get(c.object_party_id)),
             "amount_minor": c.amount_minor, "currency": c.currency,
             "date": c.valid_date.isoformat() if c.valid_date else None, "status": c.status, "method": c.method,
             "version": {"recorded_at": c.recorded_at, "superseded_at": c.superseded_at,
                         "supersedes_id": c.supersedes_id},
             "evidence": [{"document_id": e.document_id, "page": e.page, "seq": e.seq, "quote": e.quote,
                           "box": [e.box_x0, e.box_top, e.box_x1, e.box_bottom] if e.box_x0 is not None else None,
                           "external_id": e.external_id} for e in evidence.get(c.id, [])]}
            for c in claims]


def claim_history(db: Session, case_id: int, claim_key: str) -> list[dict]:
    versions = db.query(Claim).filter(Claim.case_id == case_id, Claim.claim_key == claim_key) \
        .order_by(Claim.recorded_at, Claim.id).all()
    return [{"id": v.id, "amount_minor": v.amount_minor, "status": v.status, "party_record_id": v.object_party_id,
             "recorded_at": v.recorded_at, "superseded_at": v.superseded_at, "supersede_reason": v.supersede_reason,
             "supersedes_id": v.supersedes_id} for v in versions]
