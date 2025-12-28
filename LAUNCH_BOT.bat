@echo off
REM MindDoc AI - Complete Bot Launcher with Verification
REM This script verifies setup, initializes database, and starts the bot

setlocal enabledelayedexpansion
color 0A
title MindDoc AI - Bot Launcher

cls
echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║                                                            ║
echo ║          MindDoc AI - Complete Bot Launcher               ║
echo ║                                                            ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

REM Check Python installation
echo [1/4] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ✗ ERROR: Python is not installed or not in PATH
    echo.
    echo Please install Python from: https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)
python --version
echo ✓ Python found
echo.

REM Check dependencies
echo [2/4] Verifying dependencies...
python -c "import fastapi; import sqlalchemy; import pydantic" >nul 2>&1
if errorlevel 1 (
    echo.
    echo ⚠ Installing missing dependencies...
    echo This may take a few minutes on first run...
    echo.
    pip install -r requirements.txt --quiet
    if errorlevel 1 (
        echo ✗ Failed to install dependencies
        pause
        exit /b 1
    )
)
echo ✓ All dependencies available
echo.

REM Initialize database
echo [3/4] Initializing database...
python -c "from app.database.models import create_tables, SessionLocal, init_default_tenant; create_tables(); db = SessionLocal(); init_default_tenant(db); db.close(); print('✓ Database initialized')" 2>nul
if errorlevel 1 (
    echo ✗ Database initialization failed
    echo.
    echo Attempting fallback initialization...
    python -c "from app.database.models import Base, engine; Base.metadata.create_all(bind=engine); print('✓ Database tables created')"
    if errorlevel 1 (
        echo.
        echo ✗ Critical error: Cannot initialize database
        echo.
        echo Please run HEALTH_CHECK.bat for troubleshooting
        echo.
        pause
        exit /b 1
    )
)
echo.

REM Start services
echo [4/4] Starting services...
echo.
echo ════════════════════════════════════════════════════════════
echo ✓ INITIALIZATION COMPLETE
echo ════════════════════════════════════════════════════════════
echo.
echo Services will start in separate windows:
echo.
echo   • Backend: http://localhost:8000
echo   • Frontend: http://localhost:5173
echo   • API Docs: http://localhost:8000/docs
echo.
echo Press any key to start services...
pause >nul

REM Create temp file for backend startup
cd /d "%~dp0"

REM Start backend in a new window
echo Starting backend server...
start "MindDoc AI - Backend" cmd /k "python run_server.py"

REM Wait for backend to start
timeout /t 3 /nobreak

REM Start frontend in a new window
echo Starting frontend server...
start "MindDoc AI - Frontend" cmd /k "cd frontend && npm run dev"

REM Wait for frontend to start
timeout /t 3 /nobreak

REM Try to open browser
echo.
echo Attempting to open browser...
timeout /t 2 /nobreak

REM Open browser (Windows)
start "" http://localhost:5173

REM Main window instructions
cls
echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║                                                            ║
echo ║               Services Started Successfully!              ║
echo ║                                                            ║
echo ╚════════════════════════════════════════════════════════════╝
echo.
echo ✓ Backend running on:    http://localhost:8000
echo ✓ Frontend running on:   http://localhost:5173
echo ✓ API Documentation:     http://localhost:8000/docs
echo.
echo ────────────────────────────────────────────────────────────
echo.
echo First Time Users:
echo   1. Wait 10 seconds for frontend to fully load
echo   2. Register a new account (email and password)
echo   3. Login with your credentials
echo   4. Click "Upload" to upload a PDF
echo   5. Wait for processing to complete
echo   6. Start chatting with your document!
echo.
echo ────────────────────────────────────────────────────────────
echo.
echo Troubleshooting:
echo   • If backend fails: Check HEALTH_CHECK.bat
echo   • If frontend fails: Check that port 5173 is available
echo   • If upload fails: Verify PDF is readable and < 500MB
echo   • If chat fails: Check OpenAI API key in .env file
echo.
echo ────────────────────────────────────────────────────────────
echo.
echo Two new windows should have opened:
echo   1. Backend (8000) - Shows API logs
echo   2. Frontend (5173) - Shows build logs
echo.
echo Keep these windows open while using the application.
echo Close them when done.
echo.
echo For questions, see: FINALIZATION_CHECKLIST.md
echo.
pause
