"""Parties: entity resolution, review queue, reversible merges and the case flow graph (R5, ADR-0009)."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import enforce_rate, get_current_user
from app.core.security import query_limiter
from app.database.models import Case, get_db
from app.cases import access
from app.identity import service

router = APIRouter()


def _case(db: Session, user, case_id: Optional[int], need: str = "viewer") -> Case:
    """The case if the caller holds `need` in it (ADR-0012: non-members get 404, too low a role 403)."""
    return access.require_case(db, user, case_id, need)


@router.post("/resolve")
def resolve_parties(case_id: Optional[int] = None, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Build party records from the case's statement transactions and run resolution. Automatic merges are recorded
    as identity events with their evidence; uncertain pairs go to the review queue. Human decisions are respected."""
    enforce_rate(query_limiter, user)
    case = _case(db, user, case_id, "analyst")
    return {"case_id": case.id, **service.run_resolution(db, user.tenant_id, case.id, user.id)}


@router.get("")
def list_parties(case_id: Optional[int] = None, as_of: Optional[datetime] = None, db: Session = Depends(get_db),
                 user=Depends(get_current_user)):
    """Canonical parties (optionally as they stood at system time `as_of`)."""
    from app.discovery.service import tags_for
    case = _case(db, user, case_id)
    tags = tags_for(db, case.id)
    parties = [{**p, "tags": tags.get(p["party_id"], {})} for p in service.parties_overview(db, case.id, as_of)]
    return {"case_id": case.id, "as_of": as_of, "parties": parties}


@router.get("/reviews")
def list_reviews(case_id: Optional[int] = None, state: str = "open", db: Session = Depends(get_db),
                 user=Depends(get_current_user)):
    if state not in ("open", "merged", "kept_separate"):
        raise HTTPException(status_code=422, detail="state must be open, merged or kept_separate")
    case = _case(db, user, case_id)
    return {"case_id": case.id, "reviews": service.review_queue(db, case.id, state)}


class Decision(BaseModel):
    decision: str = Field(pattern="^(merge|keep_separate)$")
    reason: str = Field(min_length=3, max_length=2000)
    override_conflict: bool = False


@router.post("/reviews/{review_id}")
def decide(review_id: int, body: Decision, case_id: Optional[int] = None, db: Session = Depends(get_db),
           user=Depends(get_current_user)):
    case = _case(db, user, case_id, "analyst")
    try:
        r = service.decide_review(db, user.tenant_id, case.id, review_id, body.decision, body.reason, user.id,
                                  body.override_conflict)
    except service.IdentityError as e:
        db.rollback()
        raise HTTPException(status_code=409 if "PAN" in str(e) or "already" in str(e) else 422, detail=str(e))
    db.commit()
    return {"id": r.id, "state": r.state}


class MergeBody(BaseModel):
    a_party_id: int
    b_party_id: int
    reason: str = Field(min_length=3, max_length=2000)
    override_conflict: bool = False


@router.post("/merge")
def merge(body: MergeBody, case_id: Optional[int] = None, db: Session = Depends(get_db),
          user=Depends(get_current_user)):
    case = _case(db, user, case_id, "analyst")
    try:
        ev = service.merge(db, user.tenant_id, case.id, body.a_party_id, body.b_party_id, body.reason, user.id,
                           body.override_conflict)
    except service.IdentityError as e:
        db.rollback()
        raise HTTPException(status_code=409 if "PAN" in str(e) or "already" in str(e) else 422, detail=str(e))
    db.commit()
    return {"event_id": ev.id}


class UnmergeBody(BaseModel):
    event_id: int
    reason: str = Field(min_length=3, max_length=2000)


@router.post("/unmerge")
def unmerge(body: UnmergeBody, case_id: Optional[int] = None, db: Session = Depends(get_db),
            user=Depends(get_current_user)):
    case = _case(db, user, case_id, "analyst")
    try:
        out = service.unmerge(db, user.tenant_id, case.id, body.event_id, body.reason, user.id)
    except service.IdentityError as e:
        db.rollback()
        raise HTTPException(status_code=409 if "already" in str(e) else 404, detail=str(e))
    db.commit()
    return out


@router.get("/graph")
def graph(case_id: Optional[int] = None, as_of: Optional[datetime] = None, db: Session = Depends(get_db),
          user=Depends(get_current_user)):
    """Money flows between statement accounts and canonical parties, built from transfer claims (current, or as
    known at system time `as_of`). Every edge carries its claims and each claim its evidence row."""
    case = _case(db, user, case_id)
    return {"case_id": case.id, **service.flow_graph(db, case.id, as_of)}


@router.get("/claims")
def claims(case_id: Optional[int] = None, party_id: Optional[int] = None, as_of: Optional[datetime] = None,
           db: Session = Depends(get_db), user=Depends(get_current_user)):
    """TRANSFERRED_TO / RECEIVED_FROM claims with evidence (statement row, page, region)."""
    from app.identity.claims import claims_view
    case = _case(db, user, case_id)
    return {"case_id": case.id, "as_of": as_of, "claims": claims_view(db, case.id, as_of=as_of, party_id=party_id)}


@router.get("/claims/history")
def claim_versions(key: str, case_id: Optional[int] = None, db: Session = Depends(get_db),
                   user=Depends(get_current_user)):
    """All versions of one logical claim, oldest first, with why each was superseded."""
    from app.identity.claims import claim_history
    case = _case(db, user, case_id)
    return {"case_id": case.id, "claim_key": key, "versions": claim_history(db, case.id, key)}


@router.get("/{party_id}")
def detail(party_id: int, case_id: Optional[int] = None, db: Session = Depends(get_db),
           user=Depends(get_current_user)):
    from app.discovery.service import tags_for
    case = _case(db, user, case_id)
    try:
        out = service.party_detail(db, case.id, party_id)
    except service.IdentityError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {**out, "tags": tags_for(db, case.id).get(out.get("party_id", party_id), {})}


class TagBody(BaseModel):
    related: bool
    reason: str = Field(default="", max_length=2000)


@router.put("/{party_id}/tags")
def set_related(party_id: int, body: TagBody, case_id: Optional[int] = None, db: Session = Depends(get_db),
                user=Depends(get_current_user)):
    """Mark (or unmark) a party as related to the subject, with the reason. The end-use detector treats payments
    to related parties after a loan disbursement as leads."""
    from app.core import audit
    from app.discovery.service import DiscoveryError, set_tag
    case = _case(db, user, case_id, "analyst")
    try:
        out = set_tag(db, user.tenant_id, case.id, party_id, "related", body.related, body.reason, user.id)
    except DiscoveryError as e:
        db.rollback()
        raise HTTPException(status_code=404 if "not found" in str(e) else 422, detail=str(e))
    audit.record(db, user.tenant_id, user.id, "party.tag", "party", party_id,
                 {"tag": "related", "on": body.related, "reason": body.reason})
    db.commit()
    return out
