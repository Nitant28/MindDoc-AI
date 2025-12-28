#!/usr/bin/env python3
"""
MindDoc AI - Project Finalization & Verification Script
Ensures all components are properly initialized and functional
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ProjectVerifier:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.passed = 0
        self.failed = 0
        
    def check(self, condition, message):
        """Check a condition and log result"""
        if condition:
            logger.info(f"✓ {message}")
            self.passed += 1
        else:
            logger.error(f"✗ {message}")
            self.failed += 1
        return condition
    
    def verify_structure(self):
        """Verify project structure"""
        logger.info("\n" + "=" * 60)
        logger.info("1. VERIFYING PROJECT STRUCTURE")
        logger.info("=" * 60)
        
        directories = [
            'app',
            'app/api',
            'app/database',
            'app/services',
            'app/core',
            'frontend',
            'scripts',
            'models',
        ]
        
        for dir_path in directories:
            full_path = self.project_root / dir_path
            self.check(
                full_path.exists(),
                f"Directory exists: {dir_path}"
            )
    
    def verify_files(self):
        """Verify critical files exist"""
        logger.info("\n" + "=" * 60)
        logger.info("2. VERIFYING CRITICAL FILES")
        logger.info("=" * 60)
        
        files = [
            'app/main.py',
            'app/database/models.py',
            'app/api/auth.py',
            'app/api/documents.py',
            'app/api/chat.py',
            'app/services/document_service.py',
            'app/core/config.py',
            'app/core/security.py',
            'requirements.txt',
            'frontend/package.json',
        ]
        
        for file_path in files:
            full_path = self.project_root / file_path
            self.check(
                full_path.exists(),
                f"File exists: {file_path}"
            )
    
    def verify_database(self):
        """Verify database initialization"""
        logger.info("\n" + "=" * 60)
        logger.info("3. VERIFYING DATABASE SETUP")
        logger.info("=" * 60)
        
        try:
            # Import and test database
            sys.path.insert(0, str(self.project_root))
            from app.database.models import create_tables, SessionLocal, Base
            from sqlalchemy import text
            
            logger.info("Attempting database initialization...")
            create_tables()
            self.check(True, "Database tables created/verified")
            
            # Test session (fixed SQL syntax)
            db = SessionLocal()
            try:
                db.execute(text("SELECT 1"))
                self.check(True, "Database connection verified")
            finally:
                db.close()
                
        except Exception as e:
            self.check(False, f"Database initialization: {str(e)}")
    
    def verify_dependencies(self):
        """Verify critical dependencies"""
        logger.info("\n" + "=" * 60)
        logger.info("4. VERIFYING DEPENDENCIES")
        logger.info("=" * 60)
        
        critical_deps = [
            'fastapi',
            'sqlalchemy',
            'pydantic',
            'pymupdf',
            'pdfplumber',
            'easyocr',
        ]
        
        for dep in critical_deps:
            try:
                __import__(dep.replace('-', '_'))
                self.check(True, f"Dependency available: {dep}")
            except ImportError:
                self.check(False, f"Dependency missing: {dep}")
    
    def verify_config(self):
        """Verify configuration files"""
        logger.info("\n" + "=" * 60)
        logger.info("5. VERIFYING CONFIGURATION")
        logger.info("=" * 60)
        
        try:
            sys.path.insert(0, str(self.project_root))
            from app.core.config import settings
            
            self.check(True, "Settings loaded successfully")
            logger.info(f"  - Database URL: {settings.database_url}")
            logger.info(f"  - Secret Key: {'*' * 20}")
            
        except Exception as e:
            self.check(False, f"Configuration error: {str(e)}")
    
    def verify_api(self):
        """Verify API can be imported"""
        logger.info("\n" + "=" * 60)
        logger.info("6. VERIFYING API ENDPOINTS")
        logger.info("=" * 60)
        
        try:
            sys.path.insert(0, str(self.project_root))
            from app.main import app
            
            self.check(True, "FastAPI app imported successfully")
            
            # Check routes
            routes = [r.path for r in app.routes]
            self.check(len(routes) > 0, f"API routes registered: {len(routes)}")
            
            expected_prefixes = ['/api/auth', '/api/documents', '/api/chat']
            for prefix in expected_prefixes:
                found = any(prefix in route for route in routes)
                self.check(found, f"Router registered: {prefix}")
                
        except Exception as e:
            self.check(False, f"API verification error: {str(e)}")
    
    def verify_services(self):
        """Verify services can be imported"""
        logger.info("\n" + "=" * 60)
        logger.info("7. VERIFYING SERVICES")
        logger.info("=" * 60)
        
        services = [
            ('app.services.document_service', 'Document Service'),
            ('app.services.auth_service', 'Auth Service'),
            ('app.services.rag_service', 'RAG Service'),
        ]
        
        sys.path.insert(0, str(self.project_root))
        for service_path, service_name in services:
            try:
                __import__(service_path)
                self.check(True, f"Service available: {service_name}")
            except ImportError as e:
                self.check(False, f"Service import error: {service_name} - {str(e)}")
    
    def verify_frontend(self):
        """Verify frontend setup"""
        logger.info("\n" + "=" * 60)
        logger.info("8. VERIFYING FRONTEND")
        logger.info("=" * 60)
        
        frontend_dir = self.project_root / 'frontend'
        
        frontend_files = [
            'package.json',
            'tsconfig.json',
            'vite.config.ts',
            'tailwind.config.js',
            'src/main.tsx',
            'src/App.tsx',
        ]
        
        for file_path in frontend_files:
            full_path = frontend_dir / file_path
            self.check(
                full_path.exists(),
                f"Frontend file exists: {file_path}"
            )
    
    def generate_report(self):
        """Generate final report"""
        logger.info("\n" + "=" * 60)
        logger.info("FINAL VERIFICATION REPORT")
        logger.info("=" * 60)
        
        total = self.passed + self.failed
        success_rate = (self.passed / total * 100) if total > 0 else 0
        
        logger.info(f"\nTotal Checks: {total}")
        logger.info(f"Passed: {self.passed} ✓")
        logger.info(f"Failed: {self.failed} ✗")
        logger.info(f"Success Rate: {success_rate:.1f}%")
        
        if self.failed == 0:
            logger.info("\n" + "=" * 60)
            logger.info("✓ ALL CHECKS PASSED - PROJECT READY!")
            logger.info("=" * 60)
            logger.info("\nNext Steps:")
            logger.info("  1. Run: RUN_BOT.bat (or python run_server.py)")
            logger.info("  2. Open: http://localhost:5173")
            logger.info("  3. Register and login")
            logger.info("  4. Upload a PDF to test")
            logger.info("\nDocumentation: See FINALIZATION_CHECKLIST.md")
            return True
        else:
            logger.error("\n" + "=" * 60)
            logger.error("✗ SOME CHECKS FAILED")
            logger.error("=" * 60)
            logger.error("\nPlease fix the issues above before running the application.")
            logger.error("Run: HEALTH_CHECK.bat for troubleshooting")
            return False
    
    def run_all_checks(self):
        """Run all verification checks"""
        logger.info("\n")
        logger.info("╔" + "=" * 58 + "╗")
        logger.info("║" + " " * 58 + "║")
        logger.info("║" + "  MindDoc AI - Project Finalization Verification".center(58) + "║")
        logger.info("║" + " " * 58 + "║")
        logger.info("╚" + "=" * 58 + "╝")
        
        self.verify_structure()
        self.verify_files()
        self.verify_config()
        self.verify_dependencies()
        self.verify_database()
        self.verify_api()
        self.verify_services()
        self.verify_frontend()
        
        success = self.generate_report()
        return 0 if success else 1


if __name__ == "__main__":
    verifier = ProjectVerifier()
    sys.exit(verifier.run_all_checks())
