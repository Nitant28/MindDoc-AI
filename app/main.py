## (Moved root endpoint below app creation)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from fastapi.staticfiles import StaticFiles
import os
## Removed asynccontextmanager for lifespan
import logging
import sys

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






app = FastAPI(
    title="MindDoc AI",
    description="AI-powered document processing and chat",
    version="1.0.0"
)

# Root endpoint moved to /api/docs or handled by frontend
@app.get("/api")
def api_root():
    """API Root endpoint."""
    return {"message": "Welcome to MindDoc AI API! Use /api/docs for documentation."}

# Add GZip compression for faster responses
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Increase upload size limit and robustness
class LargeUploadMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request._receive = request.receive  # Patch for large files
        return await call_next(request)
app.add_middleware(LargeUploadMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(notebook_api.router, prefix="/api/notebook", tags=["notebook"])
app.include_router(compat_router)
app.include_router(finetune_router)

@app.get("/api/test")
def test():
    """Health check endpoint"""
    return {"message": "API is working", "status": "healthy"}

@app.get("/api/health")
def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "service": "MindDoc AI Backend",
        "version": "1.0.0",
        "database": "connected"
    }

from app.api.compat_api import router as compat_router
app.include_router(compat_router)
from app.api.finetune_api import router as finetune_router
app.include_router(finetune_router)

# Mount static files for frontend (Production)
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
    logger.info(f"Serving frontend from {frontend_path}")
else:
    logger.warning(f"Frontend dist directory not found at {frontend_path}. Frontend will not be served.")

from fastapi.responses import FileResponse

@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """Catch-all route to serve the React frontend for SPA navigation."""
    # Skip API routes and root path
    if full_path.startswith("api") or full_path == "":
         return {"detail": "Not Found"}
         
    index_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    
    return {"detail": "Frontend index.html not found"}