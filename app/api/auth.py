import re
import secrets
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import auth_limiter, create_access_token, verify_password
from app.database.models import Tenant, get_db
from app.services.auth_service import create_tenant, create_user, get_user_by_email, update_user

router = APIRouter()

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RegisterRequest(BaseModel):
    email: str
    password: str
    invite_token: Optional[str] = None  # join an existing organisation instead of creating a new workspace


class LoginRequest(BaseModel):
    email: str
    password: str


class UpdateEmailRequest(BaseModel):
    new_email: str
    password: str


def _limit(request: Request):
    key = request.client.host if request.client else "anon"
    if not auth_limiter.allow(key):
        raise HTTPException(status_code=429, detail="Too many attempts. Try again in a minute.")


@router.post("/register")
def register(request: RegisterRequest, http: Request, db: Session = Depends(get_db)):
    _limit(http)
    email = request.email.strip().lower()
    if not _EMAIL.match(email):
        raise HTTPException(status_code=400, detail="Enter a valid email address")
    if len(request.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if get_user_by_email(db, email):
        raise HTTPException(status_code=400, detail="Email already registered")
    if request.invite_token:
        # Join the inviting organisation (ADR-0012); the invitation is single-use.
        from app.api.team import redeem
        from app.core import audit
        from app.database.tenancy import set_tenant
        from app.core.security import hash_password
        from app.database.models import TenantInvite, User
        inv = redeem(db, request.invite_token, email)
        now = datetime.utcnow()
        claimed = db.query(TenantInvite).filter(TenantInvite.id == inv.id, TenantInvite.used_at.is_(None))             .update({"used_at": now}, synchronize_session=False)  # single use, also under concurrent requests
        if claimed != 1:
            db.rollback()
            raise HTTPException(status_code=400, detail="This invitation is not valid (used, revoked, expired or "
                                                        "for another email)")
        user = User(email=email, hashed_password=hash_password(request.password), tenant_id=inv.tenant_id,
                    tenant_role=inv.tenant_role, is_active=True)
        db.add(user)
        db.flush()
        db.query(TenantInvite).filter(TenantInvite.id == inv.id).update({"used_by": user.id},
                                                                         synchronize_session=False)
        set_tenant(db, inv.tenant_id)
        audit.record(db, inv.tenant_id, user.id, "team.invite.used", "invite", inv.id, {"user_id": user.id})
        db.commit()
    else:
        # Without an invitation every user gets a private workspace (an organisation of one).
        tenant = create_tenant(db, f"ws-{secrets.token_hex(6)}")
        user = create_user(db, email, request.password, tenant.id)
    return {"access_token": create_access_token({"sub": str(user.id)}), "token_type": "bearer"}


@router.post("/login")
def login(request: LoginRequest, http: Request, db: Session = Depends(get_db)):
    _limit(http)
    user = get_user_by_email(db, request.email.strip().lower()) or get_user_by_email(db, request.email)
    if not user or not verify_password(request.password, user.hashed_password) or user.is_active is False:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"access_token": create_access_token({"sub": str(user.id)}), "token_type": "bearer"}


@router.get("/me")
def me(user=Depends(get_current_user), db: Session = Depends(get_db)):
    tenant = db.get(Tenant, user.tenant_id)
    return {"id": user.id, "email": user.email, "workspace": tenant.name if tenant else None,
            "tenant_role": user.tenant_role or "admin"}


@router.put("/update_email")
def update_email(request: UpdateEmailRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid password")
    new_email = request.new_email.strip().lower()
    if not _EMAIL.match(new_email):
        raise HTTPException(status_code=400, detail="Enter a valid email address")
    if get_user_by_email(db, new_email) and new_email != user.email:
        raise HTTPException(status_code=400, detail="Email already in use")
    update_user(db, user.id, email=new_email)
    return {"message": "Email updated"}
