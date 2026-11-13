import logging
import os
import sys
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from app.api import auth, chat, documents, findings, intel, parties, vision
from app.core.config import settings
from app.database.models import Document, SessionLocal, Tenant, create_tables, init_default_tenant
from app.database.tenancy import set_tenant

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s", stream=sys.stdout)
logger = logging.getLogger("minddoc")

VERSION = "2.1.0"


def _background_warmup():
    """Load models and backfill v2 analytics for legacy documents without blocking startup."""
    try:
        from app.ai import verifier
        from app.ml import embeddings
        from app.services.ingestion import backfill_insights
        embeddings.active_model_name()
        embeddings.load_reranker_blocking()
        verifier.download_nli_model_in_background()
        n = 0
        tenant_ids = []
        db = SessionLocal()
        try:
            tenant_ids = [t for (t,) in db.query(Tenant.id).all()]
        finally:
            db.close()
        for tid in tenant_ids:  # row-level security: work tenant by tenant, never across tenants
            db = SessionLocal()
            try:
                set_tenant(db, tid)
                n += sum(backfill_insights(db, d) for d in db.query(Document).filter(
                    Document.tenant_id == tid, Document.doc_type.is_(None), Document.status == "completed").all())
            finally:
                db.close()
        if n:
            logger.info("Backfilled v2 insights for %d legacy documents", n)
    except Exception as e:
        logger.warning("warm-up failed: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("MindDoc AI %s starting", VERSION)
    create_tables()
    db = SessionLocal()
    try:
        init_default_tenant(db)
    finally:
        db.close()
    if os.getenv("MINDDOC_SKIP_WARMUP") != "1":
        threading.Thread(target=_background_warmup, daemon=True).start()
    worker = None
    if settings.embedded_worker:  # demo hosts (ADR-0013); production runs `python -m app.worker` instead
        from app.jobs.worker import Worker
        worker = Worker(threads=settings.worker_threads,
                        poll_seconds=float(os.getenv("MINDDOC_WORKER_POLL", "2"))).start()
    app.state.worker = worker
    yield
    if worker is not None:
        worker.stop(timeout=10)
    logger.info("MindDoc AI shutting down")


app = FastAPI(title="MindDoc AI", description="Glass-box document intelligence: multimodal RAG, CV, knowledge graph",
              version=VERSION, lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"], expose_headers=["X-Highlight-Boxes"])


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s: %s", request.url.path, exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(intel.router, prefix="/api/intel", tags=["intelligence"])
app.include_router(vision.router, prefix="/api/vision", tags=["vision"])
app.include_router(parties.router, prefix="/api/parties", tags=["parties"])
app.include_router(findings.accounts_router, prefix="/api/accounts", tags=["accounts"])
app.include_router(findings.findings_router, prefix="/api/findings", tags=["findings"])
app.include_router(findings.reports_router, prefix="/api/reports", tags=["reports"])


@app.get("/api/health")
def health():
    return {"status": "healthy", "service": "MindDoc AI Backend", "version": VERSION}


# Serve the built frontend (frontend/dist) from the same origin when present: one deployable unit.
_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _DIST.is_dir():
    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse(status_code=404, content={"detail": "Not Found"})
        target = (_DIST / full_path).resolve()
        if full_path and target.is_file() and _DIST in target.parents:
            return FileResponse(target)
        return FileResponse(_DIST / "index.html")
