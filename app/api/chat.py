from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.models import get_db, ChatSession, ChatMessage, SavedItem
from app.services.rag_service import load_vector_store, query_rag
from app.api.documents import get_current_user
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class QueryRequest(BaseModel):
    query: str
    session_id: Optional[int] = None
    document_id: Optional[int] = None

@router.post("/query")
def query_documents(request: QueryRequest, db: Session = Depends(get_db), user = Depends(get_current_user)):
    tenant_id = user.tenant_id
    vector_store = load_vector_store(db, tenant_id, request.document_id)
    # Enable tools for stronger responses
    answer = query_rag(vector_store, request.query, use_tools=True)
    if request.session_id:
        session = db.query(ChatSession).filter(ChatSession.id == request.session_id, ChatSession.user_id == user.id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        session = ChatSession(user_id=user.id, title=request.query[:50])
        db.add(session)
        db.commit()
        db.refresh(session)
    user_msg = ChatMessage(session_id=session.id, role="user", content=request.query)
    db.add(user_msg)
    assistant_msg = ChatMessage(session_id=session.id, role="assistant", content=answer)
    db.add(assistant_msg)
    db.commit()
    return {"answer": answer, "session_id": session.id}

@router.get("/sessions")
def get_sessions(db: Session = Depends(get_db), user = Depends(get_current_user)):
    sessions = db.query(ChatSession).filter(ChatSession.user_id == user.id).all()
    return [{"id": s.id, "title": s.title, "created_at": s.created_at} for s in sessions]

@router.get("/messages/{session_id}")
def get_messages(session_id: int, db: Session = Depends(get_db), user = Depends(get_current_user)):
    session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    messages = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at).all()
    return [{"role": m.role, "content": m.content} for m in messages]

@router.post("/save_response")
def save_response(request: dict, db: Session = Depends(get_db), user = Depends(get_current_user)):
    saved_item = SavedItem(user_id=user.id, item_type="response", title=request.get("title", "Saved Response"), content=request["content"])
    db.add(saved_item)
    db.commit()
    return {"message": "Response saved"}

@router.delete("/sessions/{session_id}")
def delete_session(session_id: int, db: Session = Depends(get_db), user = Depends(get_current_user)):
    session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete()
    db.delete(session)
    db.commit()
    return {"message": "Session deleted"}

@router.put("/sessions/{session_id}")
def edit_session(session_id: int, title: str, db: Session = Depends(get_db), user = Depends(get_current_user)):
    session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.title = title
    db.commit()
    db.refresh(session)
    return {"id": session.id, "title": session.title}

@router.get("/saved_items")
def get_saved_items(db: Session = Depends(get_db), user = Depends(get_current_user)):
    items = db.query(SavedItem).filter(SavedItem.user_id == user.id).all()
    return [{"id": i.id, "type": i.item_type, "title": i.title, "content": i.content, "created_at": i.created_at} for i in items]

@router.delete("/saved_items/{item_id}")
def delete_saved_item(item_id: int, db: Session = Depends(get_db), user = Depends(get_current_user)):
    item = db.query(SavedItem).filter(SavedItem.id == item_id, SavedItem.user_id == user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()
    return {"message": "Item deleted"}

@router.put("/saved_items/{item_id}")
def edit_saved_item(item_id: int, title: str, content: str, db: Session = Depends(get_db), user = Depends(get_current_user)):
    item = db.query(SavedItem).filter(SavedItem.id == item_id, SavedItem.user_id == user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    item.title = title
    item.content = content
    db.commit()
    db.refresh(item)
    return {"id": item.id, "title": item.title, "content": item.content}