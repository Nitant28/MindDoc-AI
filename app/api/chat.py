import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.ai import rag
from app.api.deps import enforce_rate, get_current_user
from app.cases import access
from app.core.security import query_limiter
from app.database.models import ChatMessage, ChatSession, SavedItem, SessionLocal, get_db
from app.database.tenancy import set_tenant

router = APIRouter()
logger = logging.getLogger(__name__)


class QueryRequest(BaseModel):
    query: str
    session_id: Optional[int] = None
    document_id: Optional[int] = None
    document_ids: Optional[list[int]] = None
    case_id: Optional[int] = None  # search only this case's documents
    mode: str = "fast"


def _doc_ids(req: QueryRequest) -> list[int]:
    ids = list(req.document_ids or [])
    if req.document_id:
        ids.append(req.document_id)
    return list(dict.fromkeys(ids))


def _scope(db: Session, user, req: QueryRequest) -> list[int]:
    """Documents this question may search: the chosen case or documents, minus any the caller may not see
    (ADR-0012). An empty result means "no restriction"; nothing searchable is a 404."""
    ids = access.scoped_document_ids(db, user, req.case_id, _doc_ids(req))
    if ids is None:
        return []
    if not ids:
        raise HTTPException(status_code=404, detail="No documents you can search in this scope")
    return ids


def _session(db: Session, user, req: QueryRequest) -> ChatSession:
    if req.session_id:
        s = db.query(ChatSession).filter(ChatSession.id == req.session_id, ChatSession.user_id == user.id).first()
        if not s:
            raise HTTPException(status_code=404, detail="Session not found")
        return s
    s = ChatSession(user_id=user.id, title=req.query.strip()[:60])
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def _history(db: Session, session_id: int) -> list[dict]:
    msgs = (db.query(ChatMessage).filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.id.desc()).limit(8).all())
    return [{"role": m.role, "content": m.content} for m in reversed(msgs)]


def _persist(db: Session, session_id: int, query: str, final: dict):
    db.add(ChatMessage(session_id=session_id, role="user", content=query))
    db.add(ChatMessage(session_id=session_id, role="assistant", content=final.get("answer", ""),
                       meta_json=rag.meta_from_final(final)))
    db.commit()


def _validate(req: QueryRequest):
    if not req.query or not req.query.strip():
        raise HTTPException(status_code=400, detail="Query is empty")
    if len(req.query) > 8000:
        raise HTTPException(status_code=400, detail="Query too long (max 8000 chars)")
    if req.mode not in ("fast", "deep"):
        req.mode = "fast"


@router.post("/query")
def query_documents(req: QueryRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    enforce_rate(query_limiter, user)
    _validate(req)
    scope = _scope(db, user, req)
    session = _session(db, user, req)
    final = rag.answer(db, tenant_id=user.tenant_id, user_id=user.id, query=req.query, document_ids=scope,
                       mode=req.mode, history=_history(db, session.id), session_id=session.id)
    if final.get("type") == "error":
        raise HTTPException(status_code=404, detail=final.get("detail"))
    _persist(db, session.id, req.query, final)
    final.pop("type", None)
    final["session_id"] = session.id
    return final


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj, default=str)}\n\n"


@router.post("/stream")
def stream(req: QueryRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    enforce_rate(query_limiter, user)
    _validate(req)
    tenant_id, user_id = user.tenant_id, user.id
    scope = _scope(db, user, req)

    def gen():
        db = SessionLocal()  # own session: lives as long as the stream
        set_tenant(db, tenant_id)
        try:
            class _U:  # minimal user stand-in bound to this session
                id = user_id
            session = _session(db, _U, req)
            yield _sse({"type": "session", "session_id": session.id})
            for ev in rag.run(db, tenant_id=tenant_id, user_id=user_id, query=req.query,
                              document_ids=scope, mode=req.mode, history=_history(db, session.id),
                              session_id=session.id, stream=True):
                if ev["type"] == "final":
                    ev["session_id"] = session.id
                    _persist(db, session.id, req.query, ev)
                yield _sse(ev)
        except HTTPException as e:
            yield _sse({"type": "error", "detail": e.detail})
        except Exception as e:
            logger.exception("stream failed: %s", e)
            yield _sse({"type": "error", "detail": f"Internal error: {type(e).__name__}"})
        finally:
            db.close()

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/sessions")
def get_sessions(db: Session = Depends(get_db), user=Depends(get_current_user)):
    sessions = db.query(ChatSession).filter(ChatSession.user_id == user.id).order_by(ChatSession.id.desc()).all()
    return [{"id": s.id, "title": s.title, "created_at": s.created_at} for s in sessions]


@router.get("/messages/{session_id}")
def get_messages(session_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    out = []
    for m in db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.id).all():
        item = {"role": m.role, "content": m.content}
        if m.meta_json:
            try:
                item["meta"] = json.loads(m.meta_json)
            except ValueError:
                pass
        out.append(item)
    return out


@router.post("/save_response")
def save_response(request: dict, db: Session = Depends(get_db), user=Depends(get_current_user)):
    if not request.get("content"):
        raise HTTPException(status_code=400, detail="content is required")
    db.add(SavedItem(user_id=user.id, item_type="response", title=str(request.get("title", "Saved Response"))[:200],
                     content=str(request["content"])))
    db.commit()
    return {"message": "Response saved"}


@router.delete("/sessions/{session_id}")
def delete_session(session_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete()
    db.delete(session)
    db.commit()
    return {"message": "Session deleted"}


@router.put("/sessions/{session_id}")
def edit_session(session_id: int, title: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.title = title[:200]
    db.commit()
    return {"id": session.id, "title": session.title}


@router.get("/saved_items")
def get_saved_items(db: Session = Depends(get_db), user=Depends(get_current_user)):
    items = db.query(SavedItem).filter(SavedItem.user_id == user.id).order_by(SavedItem.id.desc()).all()
    return [{"id": i.id, "type": i.item_type, "title": i.title, "content": i.content, "created_at": i.created_at}
            for i in items]


@router.delete("/saved_items/{item_id}")
def delete_saved_item(item_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    item = db.query(SavedItem).filter(SavedItem.id == item_id, SavedItem.user_id == user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()
    return {"message": "Item deleted"}


@router.put("/saved_items/{item_id}")
def edit_saved_item(item_id: int, title: str, content: str, db: Session = Depends(get_db),
                    user=Depends(get_current_user)):
    item = db.query(SavedItem).filter(SavedItem.id == item_id, SavedItem.user_id == user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    item.title, item.content = title, content
    db.commit()
    return {"id": item.id, "title": item.title, "content": item.content}
