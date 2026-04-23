import os
import logging
import sys

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from app.api import auth, documents, chat
from app.api import notebook_api
from app.api.compat_api import router as compat_router
from app.api.finetune_api import router as finetune_router
from app.database.models import create_tables, SessionLocal, init_default_tenant

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

# Initialize DB on startup
try:
    create_tables()
    db = SessionLocal()
    init_default_tenant(db)
    db.close()
    logger.info("Database initialized successfully")
except Exception as e:
    logger.error(f"DB init error: {e}")

app = FastAPI(
    title="MindDoc AI",
    description="AI-powered document processing and chat",
    version="1.0.0"
)

# CORS - allow all origins for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# API Routes
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(notebook_api.router, prefix="/api/notebook", tags=["notebook"])
app.include_router(compat_router)
app.include_router(finetune_router)


@app.get("/api")
def api_root():
    return {"message": "MindDoc AI API is running. Use /api/docs for documentation."}


@app.get("/api/health")
def health():
    return {
        "status": "healthy",
        "service": "MindDoc AI Backend",
        "version": "1.0.0",
        "database": "connected"
    }


@app.get("/api/test")
def test():
    return {"message": "API is working", "status": "healthy"}


# Frontend SPA setup
FRONTEND_DIST = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
INDEX_HTML = os.path.join(FRONTEND_DIST, "index.html")

if os.path.exists(FRONTEND_DIST):
    assets_path = os.path.join(FRONTEND_DIST, "assets")
    if os.path.exists(assets_path):
        app.mount("/assets", StaticFiles(directory=assets_path), name="assets")
    logger.info(f"Frontend dist found at {FRONTEND_DIST}")
else:
    logger.warning(f"Frontend dist NOT found at {FRONTEND_DIST}")


@app.get("/{full_path:path}")
async def serve_spa(request: Request, full_path: str):
    """Catch-all: serve index.html for all non-API routes (React SPA)."""
    # Serve actual static files (vite.svg, etc.)
    if full_path and os.path.exists(FRONTEND_DIST):
        static_file = os.path.join(FRONTEND_DIST, full_path)
        if os.path.isfile(static_file):
            return FileResponse(static_file)
    # For all React routes (/login, /register, /chat, etc.) serve index.html
    if os.path.exists(INDEX_HTML):
        return FileResponse(INDEX_HTML)
    return JSONResponse({"detail": "Application not found"}, status_code=404)
