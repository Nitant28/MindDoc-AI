"""Bank accounts, findings and frozen reports for a case (R5; design F §2.3, §4)."""
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
    return {**service.view(db, case.id, f), "history": service.history(db, case.id, f.finding_key)}


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

