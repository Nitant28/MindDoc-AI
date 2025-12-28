from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import sys

from app.api import auth, documents, chat
from app.database.models import create_tables, SessionLocal, init_default_tenant

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database
    logger.info("=" * 60)
    logger.info("MindDoc AI Backend Starting...")
    logger.info("=" * 60)
    
    try:
        # Step 1: Create all tables
        create_tables()
        
        # Step 2: Initialize default tenant
        db = SessionLocal()
        try:
            init_default_tenant(db)
        finally:
            db.close()
        
        logger.info("=" * 60)
        logger.info("✓ Database initialization complete")
        logger.info("✓ Backend ready to accept requests")
        logger.info("=" * 60)
    except Exception as e:
        logger.critical(f"✗ Failed to initialize database: {str(e)}")
        logger.critical("Cannot start backend without database")
        raise
    
    yield
    
    # Shutdown
    logger.info("MindDoc AI Backend shutting down...")


app = FastAPI(
    title="MindDoc AI",
    description="AI-powered document processing and chat",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])


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