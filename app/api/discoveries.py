"""Discovery ledger API (R7): run the detectors on a case, list and open leads, record dispositions.
A discovery is a lead for review with its transactions and evidence; MindDoc never decides fraud or intent."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import enforce_rate, get_current_user
from app.cases import access
from app.core.security import query_limiter
from app.database.models import Discovery, get_db
from app.discovery import detectors, service

router = APIRouter()


class Disposition(BaseModel):
    status: str = Field(pattern="^(open|confirmed|dismissed)$")
    reason: str = Field(default="", max_length=2000)


@router.get("/detectors")
def list_detectors(user=Depends(get_current_user)):
    return {"version": detectors.VERSION,
            "detectors": [{"id": k, "title": detectors._TITLES[k], "description": detectors.DESCRIPTIONS[k],
                           "defaults": detectors.DEFAULTS[k], "rule_out": detectors.RULE_OUT[k]}
                          for k in detectors.DETECTORS]}


@router.post("/run")
def run_detectors(case_id: Optional[int] = None, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Resolve parties, then run every detector on the case's analysed statements. Dispositions are kept."""
    enforce_rate(query_limiter, user)
    case = access.require_case(db, user, case_id, "analyst")
    out = service.run(db, user.tenant_id, case.id, user.id)
    db.commit()
    return {"case_id": case.id, **out}


@router.get("")
def list_discoveries(case_id: Optional[int] = None, status: Optional[str] = None, detector: Optional[str] = None,
                     include_gone: bool = False, db: Session = Depends(get_db), user=Depends(get_current_user)):
    case = access.require_case(db, user, case_id, "viewer")
    return {"case_id": case.id, **service.list_view(db, case.id, status, detector, include_gone)}


@router.get("/{discovery_id}")
def get_discovery(discovery_id: int, case_id: Optional[int] = None, db: Session = Depends(get_db),
                  user=Depends(get_current_user)):
    case = access.require_case(db, user, case_id, "viewer")
    d = db.query(Discovery).filter(Discovery.case_id == case.id, Discovery.id == discovery_id).first()
    if d is None:
        raise HTTPException(status_code=404, detail="discovery not found")
    return service.view(d)


@router.post("/{discovery_id}/disposition")
def dispose(discovery_id: int, body: Disposition, case_id: Optional[int] = None, db: Session = Depends(get_db),
            user=Depends(get_current_user)):
    """open → confirmed (worth pursuing) or dismissed (explained), with a reason; back to open clears it."""
    from app.core import audit
    case = access.require_case(db, user, case_id, "analyst")
    try:
        d = service.dispose(db, case.id, discovery_id, body.status, body.reason, user.id)
    except service.DiscoveryError as e:
        db.rollback()
        raise HTTPException(status_code=404 if "not found" in str(e) else 422, detail=str(e))
    audit.record(db, user.tenant_id, user.id, "discovery.disposition", "discovery", d.id,
                 {"status": d.status, "reason": d.disposition_reason})
    db.commit()
    return service.view(d)
