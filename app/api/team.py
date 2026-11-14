"""Organisation members and invitations (ADR-0012: tenant = organisation).

MindDoc sends no email: an admin creates an invitation and passes the one-time link to the colleague through their
own channel. Only the token's SHA-256 is stored; the token is shown once. An invitation can be limited to one email
address, expires (default 7 days) and can be revoked.
"""
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.cases import access
from app.core import audit
from app.database.models import TenantInvite, User, get_db

router = APIRouter()
TENANT_ROLES = ("admin", "member")


class InviteBody(BaseModel):
    email: Optional[str] = None
    tenant_role: str = "member"
    days: int = Field(default=7, ge=1, le=30)


class MemberUpdate(BaseModel):
    tenant_role: Optional[str] = None
    is_active: Optional[bool] = None


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _admin(user) -> None:
    if not access.is_admin(user):
        raise HTTPException(status_code=403, detail="Only an organisation admin can do this")


def _member_view(u: User) -> dict:
    return {"id": u.id, "email": u.email, "tenant_role": u.tenant_role or "admin", "active": u.is_active is not False,
            "created_at": u.created_at.isoformat() if u.created_at else None}


def _invite_view(i: TenantInvite) -> dict:
    now = datetime.utcnow()
    state = "used" if i.used_at else "revoked" if i.revoked_at else "expired" if i.expires_at < now else "open"
    return {"id": i.id, "email": i.email, "tenant_role": i.tenant_role, "state": state,
            "created_at": i.created_at.isoformat(), "expires_at": i.expires_at.isoformat(),
            "used_by": i.used_by, "used_at": i.used_at.isoformat() if i.used_at else None}


@router.get("/members")
def list_members(db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = db.query(User).filter(User.tenant_id == user.tenant_id).order_by(User.id).all()
    return {"me": user.id, "is_admin": access.is_admin(user), "members": [_member_view(u) for u in rows]}


@router.put("/members/{member_id}")
def update_member(member_id: int, body: MemberUpdate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    _admin(user)
    target = db.query(User).filter(User.id == member_id, User.tenant_id == user.tenant_id).first()
    if target is None:
        raise HTTPException(status_code=404, detail="Member not found")
    changes = {}
    if body.tenant_role is not None and body.tenant_role != (target.tenant_role or "admin"):
        if body.tenant_role not in TENANT_ROLES:
            raise HTTPException(status_code=422, detail="tenant_role must be admin or member")
        changes["tenant_role"] = [target.tenant_role, body.tenant_role]
        target.tenant_role = body.tenant_role
    if body.is_active is not None and body.is_active != (target.is_active is not False):
        changes["is_active"] = [target.is_active, body.is_active]
        target.is_active = body.is_active
    if not changes:
        raise HTTPException(status_code=409, detail="Nothing to change")
    admins = db.query(User).filter(User.tenant_id == user.tenant_id).all()
    if not any((u.tenant_role or "admin") == "admin" and u.is_active is not False for u in admins):
        db.rollback()
        raise HTTPException(status_code=409, detail="The organisation needs at least one active admin")
    audit.record(db, user.tenant_id, user.id, "team.member.update", "user", target.id, changes)
    db.commit()
    return _member_view(target)


@router.get("/invites")
def list_invites(db: Session = Depends(get_db), user=Depends(get_current_user)):
    _admin(user)
    rows = db.query(TenantInvite).filter(TenantInvite.tenant_id == user.tenant_id) \
        .order_by(TenantInvite.created_at.desc()).all()
    return [_invite_view(i) for i in rows]


@router.post("/invites")
def create_invite(body: InviteBody, db: Session = Depends(get_db), user=Depends(get_current_user)):
    _admin(user)
    if body.tenant_role not in TENANT_ROLES:
        raise HTTPException(status_code=422, detail="tenant_role must be admin or member")
    email = body.email.strip().lower() if body.email and body.email.strip() else None
    if email and db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="That email already has an account")
    token = secrets.token_urlsafe(24)
    now = datetime.utcnow()
    inv = TenantInvite(tenant_id=user.tenant_id, token_hash=token_hash(token), email=email,
                       tenant_role=body.tenant_role, created_by=user.id, created_at=now,
                       expires_at=now + timedelta(days=body.days))
    db.add(inv)
    db.flush()
    audit.record(db, user.tenant_id, user.id, "team.invite.create", "invite", inv.id,
                 {"email": email, "tenant_role": body.tenant_role, "expires_at": inv.expires_at})
    db.commit()
    return {**_invite_view(inv), "token": token}


@router.delete("/invites/{invite_id}")
def revoke_invite(invite_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    _admin(user)
    inv = db.query(TenantInvite).filter(TenantInvite.id == invite_id, TenantInvite.tenant_id == user.tenant_id).first()
    if inv is None:
        raise HTTPException(status_code=404, detail="Invitation not found")
    if inv.used_at or inv.revoked_at:
        raise HTTPException(status_code=409, detail="This invitation is no longer open")
    inv.revoked_at = datetime.utcnow()
    audit.record(db, user.tenant_id, user.id, "team.invite.revoke", "invite", inv.id, {})
    db.commit()
    return _invite_view(inv)


def redeem(db: Session, token: str, email: str) -> TenantInvite:
    """The open invitation for this token (and email, if it is limited to one), or a 400 that does not say which
    check failed."""
    inv = db.query(TenantInvite).filter(TenantInvite.token_hash == token_hash(token.strip())).first()
    now = datetime.utcnow()
    if inv is None or inv.used_at or inv.revoked_at or inv.expires_at < now or (inv.email and inv.email != email):
        raise HTTPException(status_code=400, detail="This invitation is not valid (used, revoked, expired or for "
                                                    "another email)")
    return inv
