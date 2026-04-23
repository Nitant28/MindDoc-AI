#!/usr/bin/env python3
"""
MindDoc AI Backend Server
Starts the FastAPI application with automatic database initialization
"""

import uvicorn
import sys
import logging
from pathlib import Path

# Ensure app is importable
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from app.main import app
from app.database.models import create_tables, SessionLocal, init_default_tenant

def startup():
    """Initialize database before starting server"""
    try:
        print("\n" + "=" * 60)
        print("MindDoc AI Backend - Initialization")
        print("=" * 60)
        print("\n[*] Initializing database...")
        create_tables()
        print("[OK] Database tables verified")
        
        db = SessionLocal()
        try:
            init_default_tenant(db)
            print("[OK] Default tenant initialized")
        finally:
            db.close()
        
        print("[OK] All systems ready")
        print("=" * 60)
        print("\nStarting FastAPI server...")
        print("  Backend: http://localhost:8080")
        print("  API Docs: http://localhost:8080/docs")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\n[ERROR] Initialization failed: {str(e)}")
        print("Cannot start backend without database")
        sys.exit(1)

if __name__ == "__main__":
    # Run startup
    startup()
    
    # Start server
    import os
    port = int(os.getenv("PORT", 8080))
    host = os.getenv("HOST", "0.0.0.0")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True
    )