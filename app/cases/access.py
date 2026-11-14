"""Case authorisation (ADR-0012). Tenant isolation is row-level security; this module decides, inside a tenant, which
cases and documents a user may read or change.

* The default "General" case is open to every active member of the organisation: admins act as its lead, members
  as analysts. An explicit `case_members` row can raise that role.
* Every other case is visible only to its explicit members. A non-member gets 404, as if the case did not exist.
* A document is visible when at least one case it belongs to is visible (a document in no case counts as General).
  Changing or deleting a document needs analyst rights in every case that holds it, because the change affects them.
* Roles, lowest first: viewer (read) < analyst (analysis, findings up to "proposed") < reviewer (approve or reject
  findings, issue reports and disclosures) < lead (members and case settings).
"""
from __future__ import annotations

from typing import Iterable, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.database.models import Case, CaseDocument, CaseMember, Document

ROLES = ("viewer", "analyst", "reviewer", "lead")
RANK = {r: i for i, r in enumerate(ROLES)}


def is_admin(user) -> bool:
    return (getattr(user, "tenant_role", None) or "admin") == "admin"


def _best(*roles: Optional[str]) -> Optional[str]:
    have = [r for r in roles if r]
    return max(have, key=RANK.__getitem__) if have else None


def case_role(db: Session, user, case: Case) -> Optional[str]:
    """The user's role in a case, or None when they may not see it."""
    if case is None or case.tenant_id != user.tenant_id:
        return None
    m = db.get(CaseMember, (case.id, user.id))
    explicit = m.role if m else None
    if case.is_default:
        return _best("lead" if is_admin(user) else "analyst", explicit)
    return explicit


def default_case(db: Session, tenant_id: int) -> Case:
    from app.services.ingestion import ensure_default_case
    case = ensure_default_case(db, tenant_id)
    db.commit()
    return case


def require_case(db: Session, user, case_id: Optional[int], need: str = "viewer") -> Case:
    """The case (default when `case_id` is None) if the user holds at least `need`; 404 for non-members."""
    case = default_case(db, user.tenant_id) if case_id is None else \
        db.query(Case).filter(Case.id == case_id, Case.tenant_id == user.tenant_id).first()
    role = case_role(db, user, case) if case is not None else None
    if role is None:
        raise HTTPException(status_code=404, detail="Case not found")
    if RANK[role] < RANK[need]:
        raise HTTPException(status_code=403, detail=f"This needs the {need} role in this case (you are {role})")
    return case


def visible_case_ids(db: Session, user) -> set[int]:
    cases = db.query(Case).filter(Case.tenant_id == user.tenant_id).all()
    member = {m.case_id for m in db.query(CaseMember.case_id).filter(CaseMember.user_id == user.id)}
    return {c.id for c in cases if c.is_default or c.id in member}


def hidden_document_ids(db: Session, user) -> set[int]:
    """Documents of the tenant this user may not see (empty in the common case: everything is visible)."""
    visible_cases = visible_case_ids(db, user)
    links: dict[int, set[int]] = {}
    for doc_id, case_id in db.query(CaseDocument.document_id, CaseDocument.case_id) \
            .join(Case, Case.id == CaseDocument.case_id).filter(Case.tenant_id == user.tenant_id):
        links.setdefault(doc_id, set()).add(case_id)
    return {d for d, cs in links.items() if not cs & visible_cases}


def visible_document_ids(db: Session, user) -> Optional[list[int]]:
    """None when every document is visible; otherwise the explicit allow-list (possibly empty)."""
    hidden = hidden_document_ids(db, user)
    if not hidden:
        return None
    return [d for (d,) in db.query(Document.id).filter(Document.tenant_id == user.tenant_id) if d not in hidden]


def case_document_ids(db: Session, case_id: int) -> list[int]:
    return [d for (d,) in db.query(CaseDocument.document_id).filter(CaseDocument.case_id == case_id)]


def scoped_document_ids(db: Session, user, case_id: Optional[int] = None,
                        requested: Optional[Iterable[int]] = None) -> Optional[list[int]]:
    """Allow-list for search and chat: the case's documents (when a case is given), the caller's explicit choice,
    minus anything hidden. None means "no restriction"; an empty list means "nothing may be searched"."""
    allowed: Optional[set[int]] = None
    if case_id is not None:
        require_case(db, user, case_id, "viewer")
        allowed = set(case_document_ids(db, case_id))
    hidden = hidden_document_ids(db, user)
    requested = [d for d in (requested or []) if d]
    if requested:
        allowed = set(requested) if allowed is None else allowed & set(requested)
    if allowed is None:
        return visible_document_ids(db, user) if hidden else None
    return sorted(d for d in allowed if d not in hidden)


def document_cases(db: Session, document_id: int) -> list[Case]:
    return db.query(Case).join(CaseDocument, CaseDocument.case_id == Case.id) \
        .filter(CaseDocument.document_id == document_id).all()


def require_document(db: Session, user, doc_id: int, write: bool = False) -> Document:
    """The document if the user may see it (404 otherwise); with `write`, analyst rights in every case holding it."""
    doc = db.query(Document).filter(Document.id == doc_id, Document.tenant_id == user.tenant_id).first()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    cases = document_cases(db, doc.id)
    roles = [case_role(db, user, c) for c in cases]
    if cases and not any(roles):
        raise HTTPException(status_code=404, detail="Document not found")
    if write:
        if not cases:
            roles = [case_role(db, user, default_case(db, user.tenant_id))]
        if any(r is None or RANK[r] < RANK["analyst"] for r in roles):
            raise HTTPException(status_code=403, detail="Changing this document needs the analyst role in every "
                                                        "case that holds it")
    return doc
