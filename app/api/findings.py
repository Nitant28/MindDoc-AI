"""Bank accounts, findings and frozen reports for a case (R5; design F §2.3, §4); disclosure copies and evidence
bundles (R8)."""
import hashlib
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.parties import _case
from app.cases import access
from app.database.models import BankAccount, CaseDocument, Statement, get_db
from app.findings import service

accounts_router = APIRouter()
findings_router = APIRouter()
reports_router = APIRouter()


def _err(e: service.FindingError) -> HTTPException:
    msg = str(e)
    return HTTPException(status_code=404 if "not found" in msg else 409 if "superseded" in msg else 422, detail=msg)


# --------------------------------------------------------------------------------------------- accounts

@accounts_router.get("")
def list_accounts(case_id: Optional[int] = None, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Bank accounts behind the case's statements: masked number, IFSC, holder and where the holder came from."""
    case = _case(db, user, case_id)
    rows = (db.query(BankAccount, Statement.document_id)
            .join(Statement, Statement.bank_account_id == BankAccount.id)
            .join(CaseDocument, CaseDocument.document_id == Statement.document_id)
            .filter(CaseDocument.case_id == case.id).all())
    out: dict[int, dict] = {}
    for a, doc_id in rows:
        item = out.setdefault(a.id, {"id": a.id, "account_masked": a.account_masked, "ifsc": a.ifsc,
                                     "account_type": a.account_type, "hash_basis": a.hash_basis,
                                     "holder": a.holder_name, "holder_source": a.holder_source,
                                     "holder_set_at": a.holder_set_at, "documents": []})
        item["documents"].append(doc_id)
    return {"case_id": case.id, "accounts": list(out.values())}


class HolderBody(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    reason: str = Field(min_length=3, max_length=2000)


@accounts_router.put("/{account_id}/holder")
def set_holder(account_id: int, body: HolderBody, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Set the account holder by hand (e.g. for Account Aggregator data, whose profile is not read). Recorded as the
    analyst's; statement headers never overwrite it. Re-run party resolution to update the holder party."""
    a = db.query(BankAccount).filter(BankAccount.id == account_id, BankAccount.tenant_id == user.tenant_id).first()
    if a is None:
        raise HTTPException(status_code=404, detail="Account not found")
    # the holder applies wherever the account's statements are used: analyst rights in all of those cases
    for (doc_id,) in db.query(Statement.document_id).filter(Statement.bank_account_id == a.id):
        access.require_document(db, user, doc_id, write=True)
    a.holder_name, a.holder_source = " ".join(body.name.split()), "analyst"
    a.holder_set_by, a.holder_set_at = user.id, datetime.utcnow()
    db.commit()
    return {"id": a.id, "holder": a.holder_name, "holder_source": a.holder_source}


# --------------------------------------------------------------------------------------------- findings

class SupportItem(BaseModel):
    claim_id: int
    role: str = Field(default="supports", pattern="^(supports|contradicts|context)$")


class FindingBody(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    statement: str = Field(min_length=10, max_length=5000)
    support: list[SupportItem] = Field(min_length=1, max_length=200)


@findings_router.get("")
def list_findings(case_id: Optional[int] = None, db: Session = Depends(get_db), user=Depends(get_current_user)):
    case = _case(db, user, case_id)
    return {"case_id": case.id, "findings": service.list_current(db, case.id)}


@findings_router.post("")
def create_finding(body: FindingBody, case_id: Optional[int] = None, db: Session = Depends(get_db),
                   user=Depends(get_current_user)):
    case = _case(db, user, case_id, "analyst")
    try:
        f = service.create(db, user.tenant_id, case.id, user.id, body.title, body.statement,
                           [s.model_dump() for s in body.support])
    except service.FindingError as e:
        db.rollback()
        raise _err(e)
    db.commit()
    return service.view(db, case.id, f)


@findings_router.get("/{finding_id}")
def get_finding(finding_id: int, case_id: Optional[int] = None, db: Session = Depends(get_db),
                user=Depends(get_current_user)):
    """One finding version with its full lineage: claim versions → evidence → page region → source SHA-256."""
    case = _case(db, user, case_id)
    try:
        f = service.get(db, case.id, finding_id)
    except service.FindingError as e:
        raise _err(e)
    from app.findings import fragility
    return {**service.view(db, case.id, f), "history": service.history(db, case.id, f.finding_key),
            "robustness": fragility.for_finding(db, case.id, f.id)}


class ReviseBody(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=200)
    statement: Optional[str] = Field(default=None, min_length=10, max_length=5000)
    status: Optional[str] = Field(default=None, pattern="^(draft|proposed|approved|rejected)$")
    support: Optional[list[SupportItem]] = None
    note: str = Field(default="", max_length=500)


@findings_router.post("/{finding_id}/revise")
def revise_finding(finding_id: int, body: ReviseBody, case_id: Optional[int] = None, db: Session = Depends(get_db),
                   user=Depends(get_current_user)):
    # approving or rejecting is a reviewer's decision; drafting and proposing are an analyst's
    case = _case(db, user, case_id, "reviewer" if body.status in ("approved", "rejected") else "analyst")
    try:
        f = service.revise(db, user.tenant_id, case.id, user.id, finding_id, title=body.title,
                           statement=body.statement, status=body.status,
                           support=[s.model_dump() for s in body.support] if body.support is not None else None,
                           note=body.note)
    except service.FindingError as e:
        db.rollback()
        raise _err(e)
    db.commit()
    return service.view(db, case.id, f)


@findings_router.post("/{finding_id}/refresh")
def refresh_finding(finding_id: int, case_id: Optional[int] = None, db: Session = Depends(get_db),
                    user=Depends(get_current_user)):
    case = _case(db, user, case_id, "analyst")
    try:
        f = service.refresh(db, user.tenant_id, case.id, user.id, finding_id)
    except service.FindingError as e:
        db.rollback()
        raise _err(e)
    db.commit()
    return service.view(db, case.id, f)


# ---------------------------------------------------------------------------------------------- reports

class ReportBody(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    finding_ids: list[int] = Field(min_length=1, max_length=200)


@reports_router.get("")
def list_reports(case_id: Optional[int] = None, db: Session = Depends(get_db), user=Depends(get_current_user)):
    case = _case(db, user, case_id)
    return {"case_id": case.id, "reports": service.list_reports(db, case.id)}


@reports_router.post("")
def issue_report(body: ReportBody, case_id: Optional[int] = None, db: Session = Depends(get_db),
                 user=Depends(get_current_user)):
    """Freeze approved finding versions into a report (immutable; content hash over the full snapshot)."""
    case = _case(db, user, case_id, "reviewer")
    try:
        r = service.issue(db, user.tenant_id, case.id, user.id, body.title, body.finding_ids)
    except service.FindingError as e:
        db.rollback()
        raise _err(e)
    db.commit()
    return service.report_view(db, case.id, r.id)


@reports_router.get("/{report_id}")
def get_report(report_id: int, case_id: Optional[int] = None, db: Session = Depends(get_db),
               user=Depends(get_current_user)):
    case = _case(db, user, case_id)
    try:
        return service.report_view(db, case.id, report_id)
    except service.FindingError as e:
        raise _err(e)


@reports_router.get("/{report_id}/export")
def export_report(report_id: int, case_id: Optional[int] = None, db: Session = Depends(get_db),
                  user=Depends(get_current_user)):
    """The frozen snapshot exactly as hashed (download); its SHA-256 is in the X-Content-SHA256 header."""
    case = _case(db, user, case_id)
    from app.database.models import Report
    r = db.query(Report).filter(Report.case_id == case.id, Report.id == report_id).first()
    if r is None:
        raise HTTPException(status_code=404, detail="report not found")
    return Response(content=r.snapshot.encode("utf-8"), media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="minddoc-report-{r.id}.json"',
                             "X-Content-SHA256": r.content_hash})


# -------------------------------------------------------------------------------- disclosures and bundles (R8)

class DisclosureBody(BaseModel):
    recipient: str = Field(min_length=3, max_length=300)
    subject_party_ids: Optional[list[int]] = Field(default=None, max_length=500)


def _report(db: Session, case_id: int, report_id: int):
    from app.database.models import Report
    r = db.query(Report).filter(Report.case_id == case_id, Report.id == report_id).first()
    if r is None:
        raise HTTPException(status_code=404, detail="report not found")
    return r


def _disclosure_view(d, internal: bool = True) -> dict:
    out = {"id": d.id, "report_id": d.report_id, "recipient": d.recipient, "created_at": d.created_at.isoformat(),
           "created_by": d.created_by, "content_hash": d.content_hash, "base_hash": d.base_hash,
           "subjects": json.loads(d.subjects),
           "intact": hashlib.sha256(d.content.encode("utf-8")).hexdigest() == d.content_hash}
    if internal:
        out["withheld"] = json.loads(d.withheld_internal)
    return out


@reports_router.get("/{report_id}/disclosure-parties")
def disclosure_parties(report_id: int, case_id: Optional[int] = None, db: Session = Depends(get_db),
                       user=Depends(get_current_user)):
    """Parties of the case for choosing the report's subjects; account holders are the default subjects."""
    from app.findings import disclosure
    case = _case(db, user, case_id, "reviewer")
    _report(db, case.id, report_id)
    parties, holders = disclosure.case_parties(db, case.id)
    return {"parties": [{"id": p["id"], "name": p["display"], "kind": p["kind"], "default_subject": p["id"] in holders}
                        for p in parties]}


@reports_router.post("/{report_id}/disclosures")
def create_disclosure(report_id: int, body: DisclosureBody, case_id: Optional[int] = None,
                      db: Session = Depends(get_db), user=Depends(get_current_user)):
    """A copy of the frozen report for a recipient, with third-party personal data withheld and every withheld item
    listed with its reason (SBI v. Amit Iron, 2026, para 126(e)). The frozen report itself is not changed."""
    from app.core import audit
    from app.database.models import ReportDisclosure
    from app.findings import disclosure
    case = _case(db, user, case_id, "reviewer")
    r = _report(db, case.id, report_id)
    if hashlib.sha256(r.snapshot.encode("utf-8")).hexdigest() != r.content_hash:
        raise HTTPException(status_code=409, detail="The frozen report failed its integrity check")
    parties, holders = disclosure.case_parties(db, case.id)
    known = {p["id"] for p in parties}
    subjects = set(body.subject_party_ids) & known if body.subject_party_ids is not None else holders
    now = datetime.utcnow().replace(microsecond=0)
    content, digest, internal = disclosure.make(json.loads(r.snapshot), r.content_hash, parties, subjects,
                                                body.recipient.strip(), now.isoformat())
    d = ReportDisclosure(tenant_id=user.tenant_id, report_id=r.id, recipient=body.recipient.strip(),
                         subjects=json.dumps([{"id": p["id"], "name": p["display"]} for p in parties
                                              if p["id"] in subjects], ensure_ascii=False),
                         withheld_internal=json.dumps(internal, ensure_ascii=False),
                         content=service.canonical(content), content_hash=digest, base_hash=r.content_hash,
                         created_by=user.id, created_at=now)
    db.add(d)
    db.flush()
    audit.record(db, user.tenant_id, user.id, "report.disclosure.create", "report", r.id,
                 {"disclosure_id": d.id, "recipient": d.recipient, "content_hash": digest,
                  "withheld": [{k: w[k] for k in ("label", "kind", "occurrences")} for w in internal]})
    db.commit()
    return _disclosure_view(d)


@reports_router.get("/{report_id}/disclosures")
def list_disclosures(report_id: int, case_id: Optional[int] = None, db: Session = Depends(get_db),
                     user=Depends(get_current_user)):
    from app.database.models import ReportDisclosure
    case = _case(db, user, case_id, "reviewer")
    r = _report(db, case.id, report_id)
    rows = db.query(ReportDisclosure).filter(ReportDisclosure.report_id == r.id) \
        .order_by(ReportDisclosure.created_at.desc()).all()
    return {"report_id": r.id, "disclosures": [_disclosure_view(d) for d in rows]}


@reports_router.get("/{report_id}/disclosures/{disclosure_id}/export")
def export_disclosure(report_id: int, disclosure_id: int, case_id: Optional[int] = None,
                      db: Session = Depends(get_db), user=Depends(get_current_user)):
    """The disclosed copy exactly as hashed (X-Content-SHA256)."""
    from app.database.models import ReportDisclosure
    case = _case(db, user, case_id, "reviewer")
    r = _report(db, case.id, report_id)
    d = db.query(ReportDisclosure).filter(ReportDisclosure.report_id == r.id,
                                          ReportDisclosure.id == disclosure_id).first()
    if d is None:
        raise HTTPException(status_code=404, detail="disclosure not found")
    name = f"minddoc-report-{r.id}-disclosure-{d.id}.json"
    return Response(content=d.content.encode("utf-8"), media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="{name}"',
                             "X-Content-SHA256": d.content_hash, "Access-Control-Expose-Headers": "X-Content-SHA256"})


@reports_router.get("/{report_id}/bundle")
def evidence_bundle(report_id: int, disclosure_id: Optional[int] = None, case_id: Optional[int] = None,
                    db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Evidence bundle (zip): the report or disclosure as hashed, page regions of every cited row, sources and a
    SHA-256 manifest. Disclosure bundles black out withheld text and never include whole pages."""
    from app.database.models import ReportDisclosure
    from app.findings import bundle
    case = _case(db, user, case_id, "reviewer" if disclosure_id is not None else "viewer")
    r = _report(db, case.id, report_id)
    d = None
    if disclosure_id is not None:
        d = db.query(ReportDisclosure).filter(ReportDisclosure.report_id == r.id,
                                              ReportDisclosure.id == disclosure_id).first()
        if d is None:
            raise HTTPException(status_code=404, detail="disclosure not found")
    data, name = bundle.build(db, r, d)
    return Response(content=data, media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{name}"',
                             "X-Content-SHA256": hashlib.sha256(data).hexdigest(),
                             "Access-Control-Expose-Headers": "X-Content-SHA256"})
