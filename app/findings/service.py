"""Findings and frozen reports (design F §4): explainable over time.

A finding is an analyst's statement about the case, supported by specific *claim versions*. It is versioned the same
way as claims: any change (wording, status, supporting evidence) closes the current version and inserts a successor,
so every version still resolves to exactly the claims, page regions and source files it relied on.
- `refresh` re-points a finding at the current versions of its claims after the evidence changed (a corrected row,
  a re-analysed statement, a deleted source). The new version returns to draft: it needs approval again.
- MindDoc never writes or approves findings itself, and never labels anything as fraud.

A report freezes approved finding versions: a canonical-JSON snapshot of everything they relied on (claim values,
evidence regions, source SHA-256) and its SHA-256. The application cannot change or delete it; reading it re-checks
the hash and lists findings whose evidence changed since the report was frozen ("new evidence since report").
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.database.models import (Case, Claim, ClaimEvidence, Document, Finding, FindingSupport, Party, Report,
                                  ReportFinding, User)
from app.findings import fragility

STATUSES = ("draft", "proposed", "approved", "rejected")
TRANSITIONS = {"draft": {"proposed"}, "proposed": {"approved", "rejected", "draft"}, "approved": {"draft"},
               "rejected": {"draft"}}
ROLES = ("supports", "contradicts", "context")


class FindingError(ValueError):
    pass


# ------------------------------------------------------------------------------------------------- findings

def _support_claims(db: Session, case_id: int, support: list[dict]) -> list[tuple[Claim, str]]:
    if not support:
        raise FindingError("a finding needs at least one supporting claim")
    ids = [int(s["claim_id"]) for s in support]
    claims = {c.id: c for c in db.query(Claim).filter(Claim.case_id == case_id, Claim.id.in_(ids))}
    missing = [i for i in ids if i not in claims]
    if missing:
        raise FindingError(f"claims not in this case: {missing}")
    out = []
    for s in support:
        role = s.get("role", "supports")
        if role not in ROLES:
            raise FindingError(f"role must be one of {', '.join(ROLES)}")
        out.append((claims[int(s["claim_id"])], role))
    return out


def _current(db: Session, case_id: int, finding_id: int) -> Finding:
    f = db.query(Finding).filter(Finding.case_id == case_id, Finding.id == finding_id).first()
    if f is None:
        raise FindingError("finding not found")
    if f.superseded_at is not None:
        raise FindingError("this version was superseded; act on the current version")
    return f


def _new_version(db: Session, prev: Optional[Finding], now: datetime, **fields) -> Finding:
    if prev is not None:
        prev.superseded_at = now
        db.flush()  # close before inserting the successor (one current version per key)
    f = Finding(**fields)
    db.add(f)
    db.flush()
    return f


def create(db: Session, tenant_id: int, case_id: int, user_id: int, title: str, statement: str,
           support: list[dict]) -> Finding:
    claims = _support_claims(db, case_id, support)
    now = datetime.utcnow()
    f = _new_version(db, None, now, tenant_id=tenant_id, case_id=case_id, finding_key=uuid.uuid4().hex, version=1,
                     title=title.strip(), statement=statement.strip(), status="draft", method="analyst",
                     evidence_snapshot_at=now, change_note="created", created_by=user_id, created_at=now)
    for c, role in claims:
        db.add(FindingSupport(tenant_id=tenant_id, finding_id=f.id, claim_id=c.id, role=role))
    db.flush()
    return f


def revise(db: Session, tenant_id: int, case_id: int, user_id: int, finding_id: int, *, title: Optional[str] = None,
           statement: Optional[str] = None, status: Optional[str] = None, support: Optional[list[dict]] = None,
           note: str = "") -> Finding:
    cur = _current(db, case_id, finding_id)
    content_change = (title is not None and title.strip() != cur.title) or \
        (statement is not None and statement.strip() != cur.statement) or support is not None
    new_status = status or cur.status
    if status is not None and status != cur.status:
        if status not in STATUSES or status not in TRANSITIONS[cur.status]:
            raise FindingError(f"cannot move a {cur.status} finding to {status}")
    if content_change and new_status in ("approved", "proposed") and status is None:
        new_status = "draft"  # changed wording or evidence needs approval again
    if not content_change and new_status == cur.status:
        raise FindingError("nothing to change")
    claims = _support_claims(db, case_id, support) if support is not None else \
        [(db.get(Claim, s.claim_id), s.role) for s in db.query(FindingSupport).filter(FindingSupport.finding_id == cur.id)]
    now = datetime.utcnow()
    what = []
    if content_change:
        what.append("content changed")
    if new_status != cur.status:
        what.append(f"{cur.status} → {new_status}")
    f = _new_version(db, cur, now, tenant_id=tenant_id, case_id=case_id, finding_key=cur.finding_key,
                     version=cur.version + 1, title=(title or cur.title).strip(),
                     statement=(statement or cur.statement).strip(), status=new_status, method=cur.method,
                     evidence_snapshot_at=now if support is not None else cur.evidence_snapshot_at,
                     supersedes_id=cur.id, change_note=("; ".join(what) + (f": {note}" if note else ""))[:255],
                     created_by=user_id, created_at=now)
    for c, role in claims:
        db.add(FindingSupport(tenant_id=tenant_id, finding_id=f.id, claim_id=c.id, role=role))
    db.flush()
    return f


def _claim_successor(db: Session, case_id: int, claim: Claim) -> Optional[Claim]:
    if claim.superseded_at is None:
        return claim
    return db.query(Claim).filter(Claim.case_id == case_id, Claim.claim_key == claim.claim_key,
                                  Claim.superseded_at.is_(None)).first()


def refresh(db: Session, tenant_id: int, case_id: int, user_id: int, finding_id: int) -> Finding:
    """Point the finding at the current version of each supporting claim; retracted claims are dropped."""
    cur = _current(db, case_id, finding_id)
    rows = db.query(FindingSupport).filter(FindingSupport.finding_id == cur.id).all()
    changed, dropped, support = [], [], []
    for s in rows:
        c = db.get(Claim, s.claim_id)
        nxt = _claim_successor(db, case_id, c)
        if nxt is None:
            dropped.append(c.claim_key)
            continue
        if nxt.id != c.id:
            changed.append(c.claim_key)
        support.append({"claim_id": nxt.id, "role": s.role})
    if not changed and not dropped:
        raise FindingError("the supporting evidence has not changed")
    if not support:
        raise FindingError("every supporting claim was retracted; revise the finding or reject it")
    note = f"evidence refreshed: {len(changed)} claim(s) updated, {len(dropped)} retracted"
    return revise(db, tenant_id, case_id, user_id, finding_id, support=support, note=note,
                  status=None if cur.status == "draft" else "draft")


def view(db: Session, case_id: int, f: Finding, live: bool = True) -> dict:
    """Finding version → claim versions → evidence → region (page, row, box) → source document and SHA-256.
    `live` adds what changed since (stale claims and their current versions); frozen snapshots omit it."""
    sup = db.query(FindingSupport).filter(FindingSupport.finding_id == f.id).order_by(FindingSupport.id).all()
    claims = {c.id: c for c in db.query(Claim).filter(Claim.id.in_([s.claim_id for s in sup]))} if sup else {}
    evidence: dict[int, list] = {}
    for e in db.query(ClaimEvidence).filter(ClaimEvidence.claim_id.in_(list(claims))).order_by(ClaimEvidence.id) \
            if claims else []:
        evidence.setdefault(e.claim_id, []).append(e)
    docs = {d.id: d for d in db.query(Document).filter(Document.id.in_(
        {e.document_id for es in evidence.values() for e in es if e.document_id}))} if evidence else {}
    parties = {p.id: p.name for p in db.query(Party.id, Party.name).filter(Party.id.in_(
        {c.object_party_id for c in claims.values() if c.object_party_id}))} if claims else {}
    out_support = []
    for s in sup:
        c = claims[s.claim_id]
        item = {
            "role": s.role,
            "claim": {"id": c.id, "claim_key": c.claim_key, "kind": c.kind, "subject": c.subject_label,
                      "party": parties.get(c.object_party_id), "amount_minor": c.amount_minor, "currency": c.currency,
                      "date": c.valid_date.isoformat() if c.valid_date else None, "status": c.status,
                      "method": c.method, "recorded_at": c.recorded_at.isoformat()},
            "evidence": [{"document_id": e.document_id, "filename": docs[e.document_id].filename if e.document_id in docs else None,
                          "source_sha256": docs[e.document_id].content_hash if e.document_id in docs else None,
                          "page": e.page, "seq": e.seq,
                          "box": [e.box_x0, e.box_top, e.box_x1, e.box_bottom] if e.box_x0 is not None else None,
                          "quote": e.quote, "external_id": e.external_id} for e in evidence.get(c.id, [])]}
        if live:
            nxt = _claim_successor(db, case_id, c)
            item["changed_since"] = None if c.superseded_at is None else {
                "superseded_at": c.superseded_at.isoformat(), "reason": c.supersede_reason,
                "current_claim_id": nxt.id if nxt else None}
        out_support.append(item)
    out = {"id": f.id, "finding_key": f.finding_key, "version": f.version, "title": f.title, "statement": f.statement,
           "status": f.status, "method": f.method, "evidence_snapshot_at": f.evidence_snapshot_at.isoformat(),
           "created_at": f.created_at.isoformat(), "created_by": f.created_by, "change_note": f.change_note,
           "supersedes_id": f.supersedes_id, "support": out_support}
    if live:
        out["superseded_at"] = f.superseded_at.isoformat() if f.superseded_at else None
        out["stale"] = any(s.get("changed_since") for s in out_support)
    return out


def list_current(db: Session, case_id: int) -> list[dict]:
    rows = db.query(Finding).filter(Finding.case_id == case_id, Finding.superseded_at.is_(None)) \
        .order_by(Finding.created_at.desc(), Finding.id.desc()).all()
    out = []
    for f in rows:
        v = view(db, case_id, f)
        out.append({k: v[k] for k in ("id", "finding_key", "version", "title", "status", "stale", "created_at")}
                   | {"claims": len(v["support"])})
    return out


def history(db: Session, case_id: int, finding_key: str) -> list[dict]:
    rows = db.query(Finding).filter(Finding.case_id == case_id, Finding.finding_key == finding_key) \
        .order_by(Finding.version).all()
    return [{"id": f.id, "version": f.version, "status": f.status, "change_note": f.change_note,
             "created_at": f.created_at.isoformat(), "created_by": f.created_by,
             "superseded_at": f.superseded_at.isoformat() if f.superseded_at else None} for f in rows]


def get(db: Session, case_id: int, finding_id: int) -> Finding:
    f = db.query(Finding).filter(Finding.case_id == case_id, Finding.id == finding_id).first()
    if f is None:
        raise FindingError("finding not found")
    return f


# -------------------------------------------------------------------------------------------------- reports

def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def issue(db: Session, tenant_id: int, case_id: int, user_id: int, title: str, finding_ids: list[int]) -> Report:
    if not finding_ids:
        raise FindingError("a report needs at least one finding")
    found = {f.id: f for f in db.query(Finding).filter(Finding.case_id == case_id, Finding.id.in_(finding_ids))}
    for i in finding_ids:
        f = found.get(i)
        if f is None:
            raise FindingError(f"finding {i} is not in this case")
        if f.superseded_at is not None or f.status != "approved":
            raise FindingError(f"finding {i} is not a current, approved version")
    case = db.get(Case, case_id)
    issuer = db.get(User, user_id)
    now = datetime.utcnow().replace(microsecond=0)
    snapshot = {"report": {"title": title.strip(), "case": {"id": case_id, "title": case.title if case else None},
                           "frozen_at": now.isoformat(), "issued_by": issuer.email if issuer else None},
                "findings": [{**view(db, case_id, found[i], live=False),
                              "robustness": fragility.for_finding(db, case_id, i)} for i in finding_ids],
                "notice": "Findings are statements by the named analysts, each tied to the claim versions and page "
                          "regions listed. MindDoc does not determine fraud or intent."}
    body = canonical(snapshot)
    r = Report(tenant_id=tenant_id, case_id=case_id, title=title.strip(), frozen_at=now,
               content_hash=hashlib.sha256(body.encode("utf-8")).hexdigest(), snapshot=body, issued_by=user_id)
    db.add(r)
    db.flush()
    for i in finding_ids:
        db.add(ReportFinding(tenant_id=tenant_id, report_id=r.id, finding_id=i))
    db.flush()
    return r


def report_view(db: Session, case_id: int, report_id: int) -> dict:
    r = db.query(Report).filter(Report.case_id == case_id, Report.id == report_id).first()
    if r is None:
        raise FindingError("report not found")
    intact = hashlib.sha256(r.snapshot.encode("utf-8")).hexdigest() == r.content_hash
    pinned = [rf.finding_id for rf in db.query(ReportFinding).filter(ReportFinding.report_id == r.id)]
    new_evidence = []
    for f in db.query(Finding).filter(Finding.id.in_(pinned)) if pinned else []:
        v = view(db, case_id, f)
        later = db.query(Finding).filter(Finding.case_id == case_id, Finding.finding_key == f.finding_key,
                                         Finding.version > f.version).order_by(Finding.version.desc()).first()
        if v["stale"] or later is not None:
            new_evidence.append({"finding_id": f.id, "title": f.title, "claims_changed": v["stale"],
                                 "newer_version_id": later.id if later else None})
    return {"id": r.id, "title": r.title, "frozen_at": r.frozen_at.isoformat(), "content_hash": r.content_hash,
            "intact": intact, "finding_ids": pinned, "new_evidence_since_report": new_evidence,
            "snapshot": json.loads(r.snapshot)}


def list_reports(db: Session, case_id: int) -> list[dict]:
    return [{"id": r.id, "title": r.title, "frozen_at": r.frozen_at.isoformat(), "content_hash": r.content_hash,
             "findings": db.query(ReportFinding).filter(ReportFinding.report_id == r.id).count()}
            for r in db.query(Report).filter(Report.case_id == case_id).order_by(Report.frozen_at.desc())]
