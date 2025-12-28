from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.models import get_db, Tenant, User
from app.services.auth_service import create_user, get_user_by_email, create_tenant, update_user
from app.core.security import verify_password, create_access_token
from app.api.documents import get_current_user
from pydantic import BaseModel

router = APIRouter()

class RegisterRequest(BaseModel):
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class UpdateEmailRequest(BaseModel):
    new_email: str
    password: str

@router.post("/register")
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    if get_user_by_email(db, request.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    tenant = db.query(Tenant).filter(Tenant.name == "default").first()
    if not tenant:
        tenant = create_tenant(db, "default")
    user = create_user(db, request.email, request.password, tenant.id)
    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}

@router.post("/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = get_user_by_email(db, request.email)
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}

@router.put("/update_email")
def update_email(request: UpdateEmailRequest, db: Session = Depends(get_db), user = Depends(get_current_user)):
    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid password")
    if get_user_by_email(db, request.new_email) and request.new_email != user.email:
        raise HTTPException(status_code=400, detail="Email already in use")
    update_user(db, user.id, email=request.new_email)
    return {"message": "Email updated"}