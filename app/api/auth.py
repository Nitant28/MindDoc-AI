import re
import secrets

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
    # Every user gets a private workspace: documents, graph and index are isolated per tenant.
    tenant = create_tenant(db, f"ws-{secrets.token_hex(6)}")
    user = create_user(db, email, request.password, tenant.id)
    return {"access_token": create_access_token({"sub": str(user.id)}), "token_type": "bearer"}


@router.post("/login")
def login(request: LoginRequest, http: Request, db: Session = Depends(get_db)):
    _limit(http)
    user = get_user_by_email(db, request.email.strip().lower()) or get_user_by_email(db, request.email)
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"access_token": create_access_token({"sub": str(user.id)}), "token_type": "bearer"}


@router.get("/me")
def me(user=Depends(get_current_user), db: Session = Depends(get_db)):
    tenant = db.get(Tenant, user.tenant_id)
    return {"id": user.id, "email": user.email, "workspace": tenant.name if tenant else None}


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
