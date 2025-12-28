from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
import logging
from sqlalchemy.orm import Session
from app.database.models import get_db, Document, DocumentChunk, User, SavedItem
from app.services.document_service import extract_text_from_file, save_document as save_document_service
from app.core.security import verify_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter()

logger = logging.getLogger(__name__)

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    token = credentials.credentials
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    user_id = int(payload["sub"])
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

@router.post("/upload")
def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db), user = Depends(get_current_user)):
    # Accept PDFs, DOCX, common images, and text files (.txt)
    allowed = ('.pdf', '.docx', '.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.txt', '.gif')
    filename = (file.filename or '').lower()
    
    # Validate file extension
    if not filename or not any(filename.endswith(ext) for ext in allowed):
        raise HTTPException(status_code=400, detail=f"Only PDF, DOCX, image files (.pdf, .docx, .png, .jpg, .jpeg, .tiff, .bmp, .gif), and .txt allowed. Got: {filename}")

    try:
        # If it's a .txt file, read text directly
        if filename.endswith('.txt'):
            try:
                file.file.seek(0)
            except Exception:
                pass
            raw = file.file.read()
            if isinstance(raw, bytes):
                try:
                    content = raw.decode('utf-8')
                except Exception:
                    content = raw.decode('latin-1', errors='ignore')
            else:
                content = str(raw)
        else:
            content = extract_text_from_file(file.file, file.filename)
    except Exception as e:
        logger.exception("OCR/text extraction failed for %s: %s", file.filename, e)
        content = ""

    if not content or len(content.strip()) < 10:
        raise HTTPException(status_code=400, detail="Could not extract text from document. Try a higher quality file.")

    try:
        saved = save_document_service(db, file.filename or 'uploaded', content, user.tenant_id)
        logger.info("User %s uploaded document %s (%d chars)", getattr(user, 'email', user.id), file.filename, len(content))
        return {
            "message": "Document uploaded successfully",
            "document_id": getattr(saved, 'id', None),
            "filename": file.filename,
            "characters_extracted": len(content),
            "preview": content[:200]
        }
    except Exception as e:
        logger.exception("Failed to save document %s for user %s: %s", file.filename, getattr(user, 'email', user.id), e)
        raise HTTPException(status_code=500, detail="Failed to save document")

@router.get("/list")
def list_documents(db: Session = Depends(get_db), user = Depends(get_current_user)):
    docs = db.query(Document).filter(Document.tenant_id == user.tenant_id).all()
    return [{"id": d.id, "filename": d.filename} for d in docs]


@router.delete('/delete/{doc_id}')
def delete_document(doc_id: int, db: Session = Depends(get_db), user = Depends(get_current_user)):
    doc = db.query(Document).filter(Document.id == doc_id, Document.tenant_id == user.tenant_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    # delete chunks
    db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).delete()
    db.delete(doc)
    db.commit()
    return {"message": "Document deleted"}


@router.put('/edit/{doc_id}')
def edit_document(doc_id: int, filename: str, db: Session = Depends(get_db), user = Depends(get_current_user)):
    doc = db.query(Document).filter(Document.id == doc_id, Document.tenant_id == user.tenant_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    doc.filename = filename
    db.commit()
    db.refresh(doc)
    return {"id": doc.id, "filename": doc.filename}

@router.post('/save/{doc_id}')
def save_document(doc_id: int, db: Session = Depends(get_db), user = Depends(get_current_user)):
    doc = db.query(Document).filter(Document.id == doc_id, Document.tenant_id == user.tenant_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    saved_item = SavedItem(user_id=user.id, item_type="document", title=doc.filename, content=doc.content[:500])  # save snippet
    db.add(saved_item)
    db.commit()
    return {"message": "Document saved"}