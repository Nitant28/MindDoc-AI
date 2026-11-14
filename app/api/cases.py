"""Cases (engagements): list, create, settings, members with roles, and which documents belong to a case (ADR-0012)."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.cases import access
from app.core import audit
from app.database.models import Case, CaseDocument, CaseMember, Document, Party, PartyMention, User, get_db

router = APIRouter()


class CaseBody(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class CaseUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    status: Optional[str] = None


class MemberBody(BaseModel):
    email: str
    role: str


class RoleBody(BaseModel):
    role: str


class DocumentLink(BaseModel):
    document_id: int


def _summary(db: Session, user, c: Case) -> dict:
    return {"id": c.id, "title": c.title, "status": c.status or "open", "is_default": bool(c.is_default),
            "created_at": c.created_at.isoformat() if c.created_at else None, "my_role": access.case_role(db, user, c),
            "documents": db.query(func.count(CaseDocument.document_id)).filter(CaseDocument.case_id == c.id).scalar(),
            "members": None if c.is_default else
            db.query(func.count(CaseMember.user_id)).filter(CaseMember.case_id == c.id).scalar()}


def _members(db: Session, case: Case) -> list[dict]:
    rows = db.query(CaseMember, User).join(User, User.id == CaseMember.user_id) \
        .filter(CaseMember.case_id == case.id).order_by(CaseMember.added_at).all()
    return [{"user_id": u.id, "email": u.email, "role": m.role, "active": u.is_active is not False,
             "added_at": m.added_at.isoformat()} for m, u in rows]


def _role(role: str) -> str:
    if role not in access.ROLES:
        raise HTTPException(status_code=422, detail=f"role must be one of {', '.join(access.ROLES)}")
    return role


@router.get("")
def list_cases(db: Session = Depends(get_db), user=Depends(get_current_user)):
    access.default_case(db, user.tenant_id)
    visible = access.visible_case_ids(db, user)
    cases = db.query(Case).filter(Case.id.in_(visible)).order_by(Case.is_default.desc(), Case.created_at.desc()).all()
    return [_summary(db, user, c) for c in cases]


@router.post("")
def create_case(body: CaseBody, db: Session = Depends(get_db), user=Depends(get_current_user)):
    now = datetime.utcnow()
    case = Case(tenant_id=user.tenant_id, title=body.title.strip(), status="open", is_default=False,
                created_by=user.id, created_at=now)
    db.add(case)
    db.flush()
    db.add(CaseMember(case_id=case.id, user_id=user.id, tenant_id=user.tenant_id, role="lead", added_by=user.id,
                      added_at=now))
    audit.record(db, user.tenant_id, user.id, "case.create", "case", case.id, {"title": case.title})
    db.commit()
    return _summary(db, user, case)


@router.get("/{case_id}")
def get_case(case_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    case = access.require_case(db, user, case_id, "viewer")
    docs = db.query(Document).join(CaseDocument, CaseDocument.document_id == Document.id) \
        .filter(CaseDocument.case_id == case.id).order_by(Document.id.desc()).all()
    in_cases = dict(db.query(CaseDocument.document_id, func.count(CaseDocument.case_id))
                    .filter(CaseDocument.document_id.in_([d.id for d in docs] or [-1]))
                    .group_by(CaseDocument.document_id).all())
    return {**_summary(db, user, case), "members": _members(db, case),
            "open_to_organisation": bool(case.is_default),
            "document_list": [{"id": d.id, "filename": d.filename, "status": d.status or "completed",
                               "doc_type": d.doc_type, "cases": in_cases.get(d.id, 1)} for d in docs]}


@router.put("/{case_id}")
def update_case(case_id: int, body: CaseUpdate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    case = access.require_case(db, user, case_id, "lead")
    changes = {}
    if body.title is not None and body.title.strip() != case.title:
        changes["title"] = [case.title, body.title.strip()]
        case.title = body.title.strip()
    if body.status is not None and body.status != case.status:
        if body.status not in ("open", "closed"):
            raise HTTPException(status_code=422, detail="status must be open or closed")
        if case.is_default and body.status == "closed":
            raise HTTPException(status_code=409, detail="The General case cannot be closed")
        changes["status"] = [case.status, body.status]
        case.status = body.status
    if not changes:
        raise HTTPException(status_code=409, detail="Nothing to change")
    audit.record(db, user.tenant_id, user.id, "case.update", "case", case.id, changes)
    db.commit()
    return _summary(db, user, case)


# ---------------------------------------------------------------------------------------------------- members

@router.get("/{case_id}/members")
def list_members(case_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    case = access.require_case(db, user, case_id, "viewer")
    return {"case_id": case.id, "open_to_organisation": bool(case.is_default), "members": _members(db, case)}


@router.post("/{case_id}/members")
def add_member(case_id: int, body: MemberBody, db: Session = Depends(get_db), user=Depends(get_current_user)):
    case = access.require_case(db, user, case_id, "lead")
    role = _role(body.role)
    target = db.query(User).filter(User.email == body.email.strip().lower(), User.tenant_id == user.tenant_id).first()
    if target is None or target.is_active is False:
        raise HTTPException(status_code=404, detail="No active member of your organisation has that email")
    if db.get(CaseMember, (case.id, target.id)):
        raise HTTPException(status_code=409, detail="Already a member of this case; change the role instead")
    db.add(CaseMember(case_id=case.id, user_id=target.id, tenant_id=user.tenant_id, role=role, added_by=user.id,
                      added_at=datetime.utcnow()))
    audit.record(db, user.tenant_id, user.id, "case.member.add", "case", case.id, {"user_id": target.id, "role": role})
    db.commit()
    return {"case_id": case.id, "members": _members(db, case)}


def _leads_after(db: Session, case: Case, user_id: int, new_role: Optional[str]) -> int:
    leads = {m.user_id for m in db.query(CaseMember).filter(CaseMember.case_id == case.id, CaseMember.role == "lead")}
    if new_role == "lead":
        leads.add(user_id)
    else:
        leads.discard(user_id)
    return len(leads)


@router.put("/{case_id}/members/{member_id}")
def change_role(case_id: int, member_id: int, body: RoleBody, db: Session = Depends(get_db),
                user=Depends(get_current_user)):
    case = access.require_case(db, user, case_id, "lead")
    role = _role(body.role)
    m = db.get(CaseMember, (case.id, member_id))
    if m is None:
        raise HTTPException(status_code=404, detail="Not a member of this case")
    if not case.is_default and _leads_after(db, case, member_id, role) == 0:
        raise HTTPException(status_code=409, detail="A case needs at least one lead")
    old, m.role = m.role, role
    audit.record(db, user.tenant_id, user.id, "case.member.role", "case", case.id,
                 {"user_id": member_id, "from": old, "to": role})
    db.commit()
    return {"case_id": case.id, "members": _members(db, case)}


@router.delete("/{case_id}/members/{member_id}")
def remove_member(case_id: int, member_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    case = access.require_case(db, user, case_id, "lead")
    m = db.get(CaseMember, (case.id, member_id))
    if m is None:
        raise HTTPException(status_code=404, detail="Not a member of this case")
    if not case.is_default and _leads_after(db, case, member_id, None) == 0:
        raise HTTPException(status_code=409, detail="A case needs at least one lead")
    db.delete(m)
    audit.record(db, user.tenant_id, user.id, "case.member.remove", "case", case.id, {"user_id": member_id})
    db.commit()
    return {"case_id": case.id, "members": _members(db, case)}


# -------------------------------------------------------------------------------------------------- documents

@router.post("/{case_id}/documents")
def link_document(case_id: int, body: DocumentLink, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Add a document the caller can already see to another case (a statement used in two engagements)."""
    case = access.require_case(db, user, case_id, "analyst")
    doc = access.require_document(db, user, body.document_id)
    if db.get(CaseDocument, (case.id, doc.id)):
        raise HTTPException(status_code=409, detail="The document is already in this case")
    db.add(CaseDocument(case_id=case.id, document_id=doc.id, tenant_id=user.tenant_id))
    audit.record(db, user.tenant_id, user.id, "case.document.add", "case", case.id, {"document_id": doc.id})
    db.commit()
    return {"case_id": case.id, "document_id": doc.id, "linked": True}


@router.delete("/{case_id}/documents/{doc_id}")
def unlink_document(case_id: int, doc_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Remove a document from one case. Its claims in this case are closed with a reason (nothing is deleted) and
    its party mentions leave the case. A document must stay in at least one case: delete it instead."""
    from app.identity.claims import build_claims
    case = access.require_case(db, user, case_id, "analyst")
    link = db.get(CaseDocument, (case.id, doc_id))
    if link is None:
        raise HTTPException(status_code=404, detail="The document is not in this case")
    if db.query(CaseDocument).filter(CaseDocument.document_id == doc_id).count() <= 1:
        raise HTTPException(status_code=409, detail="This is the document's only case; delete the document instead")
    db.delete(link)
    party_ids = [p for (p,) in db.query(Party.id).filter(Party.case_id == case.id)]
    if party_ids:
        db.query(PartyMention).filter(PartyMention.document_id == doc_id, PartyMention.party_id.in_(party_ids)) \
            .delete(synchronize_session=False)
    db.flush()
    closed = build_claims(db, user.tenant_id, case.id)
    audit.record(db, user.tenant_id, user.id, "case.document.remove", "case", case.id, {"document_id": doc_id})
    db.commit()
    return {"case_id": case.id, "document_id": doc_id, "linked": False, "claims": closed}
