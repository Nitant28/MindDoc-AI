"""Discovery ledger (R7): run the detectors on a case's transactions and keep their leads with dispositions.

* A run reads every analysed statement in the case, resolves parties first (so account holders and counterparties
  are canonical parties), runs the detectors with the stored parameters and records the run.
* Each lead has a stable key (detector + its transactions). Re-running updates the same row: an analyst's
  disposition (pursue / dismissed, with a reason) is kept. A lead that a later run no longer finds is kept and marked
  `still_detected = false`, never deleted.
* Payloads copy each transaction's date, amount, narration and page region, so a lead still shows its evidence after
  a statement is re-analysed.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.database.models import (BankAccount, CaseDocument, Claim, ClaimEvidence, Discovery, DiscoveryRun, Document,
                                  Party, PartyMention, PartyTag, Statement, StatementTxn)
from app.discovery import detectors
from app.discovery.detectors import CaseData, Txn

STATUSES = ("open", "confirmed", "dismissed")

_CHANNEL = [("CASH", re.compile(r"^\s*(by\s+)?cash|cash\s*(dep|deposit|wdl|withdrawal)|\batm\b|\bcsh\b", re.I)),
            ("UPI", re.compile(r"^\s*upi\b", re.I)), ("NEFT", re.compile(r"^\s*neft\b", re.I)),
            ("RTGS", re.compile(r"^\s*rtgs\b", re.I)), ("IMPS", re.compile(r"^\s*(imps|mmt)\b", re.I)),
            ("NACH", re.compile(r"^\s*(nach|ach|ecs)\b", re.I)), ("CHQ", re.compile(r"\b(chq|cheque|clg)\b", re.I))]


class DiscoveryError(ValueError):
    pass


def channel_of(narration: str) -> str:
    for name, pat in _CHANNEL:
        if pat.search(narration or ""):
            return name
    return "OTHER"


def case_data(db: Session, case_id: int) -> CaseData:
    from app.identity.service import canonical_map
    cmap = canonical_map(db, case_id)
    records = {p.id: p for p in db.query(Party).filter(Party.case_id == case_id)}
    names = {}
    for rid, cid in cmap.items():
        if cid in records:
            names[f"p:{cid}"] = records[cid].name

    def pkey(record_id: Optional[int]) -> Optional[str]:
        if record_id is None or record_id not in cmap:
            return None
        return f"p:{cmap[record_id]}"

    stmts = (db.query(Statement, Document).join(Document, Document.id == Statement.document_id)
             .join(CaseDocument, CaseDocument.document_id == Statement.document_id)
             .filter(CaseDocument.case_id == case_id).all())
    accounts = {s.bank_account_id for s, _ in stmts if s.bank_account_id}
    holders: dict[int, str] = {}
    for m in db.query(PartyMention).filter(PartyMention.source_type == "account_holder",
                                           PartyMention.source_id.in_(accounts or {-1})):
        if m.party_id in records and pkey(m.party_id):
            holders[m.source_id] = pkey(m.party_id)
    # counterparty of each row, from the current transfer claims (document + row → claim)
    by_row: dict[tuple, Claim] = {}
    current = {c.id: c for c in db.query(Claim).filter(Claim.case_id == case_id, Claim.superseded_at.is_(None))}
    for e in db.query(ClaimEvidence).filter(ClaimEvidence.claim_id.in_(list(current) or [-1])):
        if e.document_id is not None and e.seq is not None:
            by_row[(e.document_id, e.seq)] = current[e.claim_id]
    txns: list[Txn] = []
    for st, doc in stmts:
        acct = f"a:{st.bank_account_id}" if st.bank_account_id else f"d:{doc.id}"
        holder = holders.get(st.bank_account_id)
        for t in db.query(StatementTxn).filter(StatementTxn.statement_id == st.id).order_by(StatementTxn.seq):
            amount = t.debit_minor or t.credit_minor
            if not amount:
                continue
            claim = by_row.get((doc.id, t.seq))
            cp = pkey(claim.object_party_id) if claim else None
            txns.append(Txn(
                key=f"{(doc.content_hash or str(doc.id))[:16]}:{t.seq}", document_id=doc.id, account=acct,
                holder=holder, date=t.txn_date, amount_minor=abs(amount),
                direction="debit" if t.debit_minor else "credit", counterparty=cp,
                counterparty_name=names.get(cp) if cp else None, channel=channel_of(t.narration or ""),
                narration=t.narration or "", page=t.page, seq=t.seq,
                box=(t.box_x0, t.box_top, t.box_x1, t.box_bottom) if t.box_x0 is not None else None,
                claim_id=claim.id if claim else None, txn_id=t.id))
    related = {pkey(t.party_id) for t in db.query(PartyTag).filter(PartyTag.case_id == case_id,
                                                                   PartyTag.tag == "related")} - {None}
    group = set(holders.values())
    for acct_id in accounts:  # holders typed on the account but not yet a party record still name the account
        if acct_id not in holders:
            a = db.get(BankAccount, acct_id)
            if a is not None and a.holder_name:
                names.setdefault(f"a:{acct_id}", a.holder_name)
    return CaseData(txns=txns, names=names, related=related, group=group)


def _txn_view(t: Txn) -> dict:
    return {"key": t.key, "document_id": t.document_id, "page": t.page, "seq": t.seq,
            "box": list(t.box) if t.box else None, "date": t.date.isoformat(), "amount_minor": t.amount_minor,
            "direction": t.direction, "channel": t.channel, "counterparty": t.counterparty,
            "counterparty_name": t.counterparty_name, "narration": t.narration, "claim_id": t.claim_id}


def run(db: Session, tenant_id: int, case_id: int, user_id: Optional[int] = None,
        params: Optional[dict] = None) -> dict:
    from app.identity.service import run_resolution
    resolution = run_resolution(db, tenant_id, case_id, user_id)
    data = case_data(db, case_id)
    merged = {k: {**v, **((params or {}).get(k) or {})} for k, v in detectors.DEFAULTS.items()}
    now = datetime.utcnow()
    r = DiscoveryRun(tenant_id=tenant_id, case_id=case_id, started_at=now, params=json.dumps(merged),
                     versions=json.dumps({k: detectors.VERSION for k in detectors.DETECTORS}),
                     n_transactions=len(data.txns), run_by=user_id)
    db.add(r)
    db.flush()
    leads = detectors.run_all(data, merged)
    existing = {d.discovery_key: d for d in db.query(Discovery).filter(Discovery.case_id == case_id)}
    seen, new = set(), 0
    for lead in leads:
        payload = json.dumps({"transactions": [_txn_view(t) for t in lead.txns], "details": lead.details,
                              "rule_out": lead.rule_out}, ensure_ascii=False, default=str)
        d = existing.get(lead.key)
        if d is None:
            d = Discovery(tenant_id=tenant_id, case_id=case_id, discovery_key=lead.key, status="open",
                          first_seen_at=now)
            db.add(d)
            existing[lead.key] = d
            new += 1
        d.detector, d.detector_version, d.title, d.summary = lead.detector, detectors.VERSION, lead.title, lead.summary
        d.amount_minor, d.payload, d.last_seen_at, d.last_run_id, d.still_detected = \
            lead.amount_minor, payload, now, r.id, True
        seen.add(lead.key)
    for key, d in existing.items():
        if key not in seen:
            d.still_detected = False
    r.n_found, r.n_new, r.finished_at = len(leads), new, datetime.utcnow()
    db.flush()
    return {"run_id": r.id, "transactions": len(data.txns), "found": len(leads), "new": new,
            "no_longer_detected": sum(1 for k, d in existing.items() if k not in seen),
            "parties_resolved": resolution.get("records"), "version": detectors.VERSION}


def view(d: Discovery, full: bool = True) -> dict:
    out = {"id": d.id, "detector": d.detector, "detector_version": d.detector_version, "title": d.title,
           "summary": d.summary, "amount_minor": d.amount_minor, "status": d.status,
           "disposition_reason": d.disposition_reason, "disposed_by": d.disposed_by,
           "disposed_at": d.disposed_at.isoformat() if d.disposed_at else None,
           "first_seen_at": d.first_seen_at.isoformat(), "last_seen_at": d.last_seen_at.isoformat(),
           "still_detected": bool(d.still_detected)}
    payload = json.loads(d.payload)
    out["transactions"] = len(payload.get("transactions", []))
    if full:
        out.update(payload)
        out["description"] = detectors.DESCRIPTIONS.get(d.detector)
    return out


def list_view(db: Session, case_id: int, status: Optional[str] = None, detector: Optional[str] = None,
              include_gone: bool = False) -> dict:
    q = db.query(Discovery).filter(Discovery.case_id == case_id)
    if status:
        q = q.filter(Discovery.status == status)
    if detector:
        q = q.filter(Discovery.detector == detector)
    if not include_gone:
        q = q.filter(Discovery.still_detected.is_(True))
    rows = q.order_by(Discovery.amount_minor.desc(), Discovery.id).all()
    all_rows = db.query(Discovery).filter(Discovery.case_id == case_id).all()
    counts: dict = {"by_detector": {}, "by_status": {}}
    for d in all_rows:
        if d.still_detected:
            counts["by_detector"][d.detector] = counts["by_detector"].get(d.detector, 0) + 1
            counts["by_status"][d.status] = counts["by_status"].get(d.status, 0) + 1
    last = db.query(DiscoveryRun).filter(DiscoveryRun.case_id == case_id).order_by(DiscoveryRun.id.desc()).first()
    return {"discoveries": [view(d, full=False) for d in rows], "counts": counts,
            "no_longer_detected": sum(1 for d in all_rows if not d.still_detected),
            "last_run": None if last is None else {
                "id": last.id, "started_at": last.started_at.isoformat(), "transactions": last.n_transactions,
                "found": last.n_found, "new": last.n_new, "version": json.loads(last.versions)}}


def dispose(db: Session, case_id: int, discovery_id: int, status: str, reason: str, user_id: int) -> Discovery:
    if status not in STATUSES:
        raise DiscoveryError(f"status must be one of {', '.join(STATUSES)}")
    d = db.query(Discovery).filter(Discovery.case_id == case_id, Discovery.id == discovery_id).first()
    if d is None:
        raise DiscoveryError("discovery not found")
    if status != "open" and len((reason or "").strip()) < 3:
        raise DiscoveryError("give a reason for the disposition")
    d.status, d.disposition_reason = status, (reason or "").strip() or None
    d.disposed_by, d.disposed_at = (user_id, datetime.utcnow()) if status != "open" else (None, None)
    db.flush()
    return d


def set_tag(db: Session, tenant_id: int, case_id: int, party_id: int, tag: str, on: bool, reason: str,
            user_id: int) -> dict:
    from app.identity.service import canonical_map
    cmap = canonical_map(db, case_id)
    if party_id not in cmap:
        raise DiscoveryError("party not found in this case")
    members = [r for r, c in cmap.items() if c == cmap[party_id]]
    rows = db.query(PartyTag).filter(PartyTag.case_id == case_id, PartyTag.tag == tag,
                                     PartyTag.party_id.in_(members)).all()
    if on:
        if len((reason or "").strip()) < 3:
            raise DiscoveryError("give a reason")
        if not rows:
            db.add(PartyTag(tenant_id=tenant_id, case_id=case_id, party_id=party_id, tag=tag, reason=reason.strip(),
                            set_by=user_id, set_at=datetime.utcnow()))
    else:
        for r in rows:
            db.delete(r)
    db.flush()
    return {"party_id": cmap[party_id], "tag": tag, "on": on}


def tags_for(db: Session, case_id: int) -> dict[int, dict]:
    """Canonical party id → {tag: reason} for the parties page."""
    from app.identity.service import canonical_map
    cmap = canonical_map(db, case_id)
    out: dict[int, dict] = {}
    for t in db.query(PartyTag).filter(PartyTag.case_id == case_id):
        if t.party_id in cmap:
            out.setdefault(cmap[t.party_id], {})[t.tag] = t.reason
    return out
