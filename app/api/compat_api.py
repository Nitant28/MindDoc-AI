from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.core.config import settings
from app.database.models import User, Document, DocumentChunk
from app.database.models import get_db
from passlib.context import CryptContext
import jwt
import os
import shutil
from app.services.rag_service import query_rag, load_vector_store

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict):
    # Use jwt_secret from settings
    return jwt.encode(data, settings.jwt_secret, algorithm=settings.jwt_algorithm)

@router.post("/auth/register")
def register(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(email=email, hashed_password=get_password_hash(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}

@router.post("/auth/login")
def login(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}

UPLOAD_DIR = os.path.join(os.getcwd(), "data", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.get("/documents/list")
def list_documents(db: Session = Depends(get_db)):
    docs = db.query(Document).all()
    return [{"id": d.id, "filename": d.filename} for d in docs]

@router.post("/chat/query")
def chat_query(query: str = Form(...), document_id: int = Form(None), db: Session = Depends(get_db)):
    # For demo, use tenant_id=1
    vector_store = load_vector_store(db, tenant_id=1, document_id=document_id)
    answer = query_rag(vector_store, query, db=db, tenant_id=1, document_id=document_id)
    return {"answer": answer}
